"""Build the shared content inventory from mds/ and its document metadata."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import os
import re

from lib_config import ROOT
from lib_links import links_in, local_target

# Logical ownership may differ from the historical file numbering. Keep the
# original paths stable, as required by docs/知识结构分层规范.md.
PARENT_OVERRIDES = {"4.1.3": "2.1", "4.1.4": "2.1", "6.3.1": "6.4", "6.3.4": "6.4"}
LEVELS = {"入门": 1, "初级": 1, "中级": 2, "高级": 3}
PATH_INFO = [
    ("a", "🎓 路径 A：新人入门", "在校生、转行者 · 建立全景认知"),
    ("b", "💻 路径 B：研发实战", "1～5 年程序员 · 补盲区、做架构决策"),
    ("c", "🚀 路径 C：上线运营", "主程/CTO · 从能跑到能运营"),
]


def doc_id(path: Path) -> str:
    m = re.match(r"^(\d+(?:\.\d+)*)\.", path.stem)
    return m.group(1) if m else ""


def title_of(path: Path) -> str:
    headings = re.findall(r"^#{1,6}\s+(.+)$", path.read_text(encoding="utf-8-sig"), re.M)
    return next((title.strip() for title in headings if title.strip() not in {"目录", "Table of Contents"}), path.stem)


def md_link(title: str, path: str) -> str:
    # Unicode itself is valid in Markdown links; # and spaces must be escaped.
    target = path.replace("%", "%25").replace("#", "%23").replace(" ", "%20").replace("(", "%28").replace(")", "%29")
    return f"[{title}]({target})"


def relative(path: str, source: Path, root: Path = ROOT) -> str:
    return Path(os.path.relpath(root / path, source.parent)).as_posix()


def build_catalog(root: Path = ROOT) -> dict:
    all_paths = sorted((root / "mds").rglob("*.md"))
    core = [p for p in all_paths if re.fullmatch(r"[1-6]\..+", p.parent.name)]
    ids: dict[str, Path] = {}
    for p in core:
        ident = doc_id(p)
        if not ident or ident in ids:
            raise ValueError(f"Missing or duplicate document ID: {p}")
        ids[ident] = p

    by_id: dict[str, dict] = {}
    for ident, p in ids.items():
        parent_id = PARENT_OVERRIDES.get(ident, ident.rpartition(".")[0])
        if parent_id and parent_id not in ids:
            raise ValueError(f"Missing parent {parent_id} for {p}")
        text = p.read_text(encoding="utf-8-sig")
        depth = len(ident.split(".")) - 1
        level_match = re.search(r"等级[:：]\s*([^,，*\n]+)", text)
        levels = [LEVELS[v.strip()] for v in level_match.group(1).split("|") if v.strip() in LEVELS] if level_match else []
        roles = re.search(r"角色[:：]\s*([^*\n]+)", text)
        role = roles.group(1) if roles else ""
        doc = {"t": title_of(p), "p": p.relative_to(root).as_posix(), "c": int(ident.split(".")[0]),
               "l": min(levels) if depth >= 2 and levels else 0,
               "r": ",".join(v for v in ("客户端", "服务端") if v in role),
               "parent": ids[parent_id].relative_to(root).as_posix() if parent_id else ""}
        code = root / "code" / "gamedevmind" / p.parent.name / p.stem
        if code.is_dir():
            doc["code"] = code.relative_to(root).as_posix() + "/"
        by_id[ident] = doc

    children: dict[str, list[str]] = defaultdict(list)
    for ident in by_id:
        children[PARENT_OVERRIDES.get(ident, ident.rpartition(".")[0])].append(ident)
    ordered: list[dict] = []
    def walk(ident: str, category: int) -> None:
        doc = by_id[ident]
        doc["c"] = category
        ordered.append(doc)
        for child in sorted(children[ident], key=lambda v: tuple(map(int, v.split(".")))):
            walk(child, category)
    for ident in sorted(children[""], key=int):
        walk(ident, int(ident))
    if len(ordered) != len(core):
        raise ValueError("Catalog contains an unreachable document or parent cycle")

    core_paths = {d["p"] for d in ordered}
    source = root / "mds/topics/推荐阅读路径.md"
    reading = source.read_text(encoding="utf-8-sig")
    learning_paths = []
    for ident, title, desc in PATH_INFO:
        m = re.search(rf"^## 路径 {ident.upper()}[：:].*?\n(.*?)(?=^## |\Z)", reading, re.M | re.S)
        if not m:
            raise ValueError(f"Missing reading path {ident}")
        paths = []
        for link in links_in(m.group(1)):
            target = local_target(source, link.target, root)
            if target and target[0].is_relative_to(root):
                path = target[0].relative_to(root).as_posix()
                if path in core_paths and path not in paths:
                    paths.append(path)
        learning_paths.append({"id": ident, "title": title, "desc": desc, "paths": paths})

    stats = {"documents": len(all_paths), "core": len(ordered), "supplementary": len(all_paths) - len(ordered),
             "cases": len([p for p in (root / "cases").glob("*.md") if p.name != "README.md"]),
             "aiCases": len([p for p in (root / "ai-cases").glob("*.md") if p.name != "README.md"]),
             "codeCollections": len(list((root / "code").glob("*/README.md")))}
    return {"docs": ordered, "stats": stats, "paths": learning_paths,
            "supplementary": [p.relative_to(root).as_posix() for p in all_paths if p.relative_to(root).as_posix() not in core_paths]}
