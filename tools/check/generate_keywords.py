#!/usr/bin/env python3
"""从 mds/ 提取关键词，生成 KEYWORDS.md（供搜索参考）。"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_config import ROOT
from content_catalog import md_link, title_of

KW_BLOCK = re.compile(
    r"\*\*关键词:\*\*\s*(?:<br/?>\s*)?\n\*([^*]+)\*",
    re.IGNORECASE,
)
LINK_IN_MDS = re.compile(r"\]\((mds/[^)]+)\)")


def render_keywords(root: Path = ROOT) -> str:
    mds_dir = root / "mds"
    keyword_to_docs: dict[str, list[str]] = defaultdict(list)

    for md in sorted(mds_dir.rglob("*.md")):
        text = md.read_text(encoding="utf-8", errors="ignore")
        m = KW_BLOCK.search(text)
        if not m:
            continue
        rel = md.relative_to(root).as_posix()
        title = title_of(md)
        for kw in re.split(r"[,，、]", m.group(1)):
            kw = kw.strip()
            if kw and len(kw) >= 2:
                keyword_to_docs[kw.lower()].append(md_link(title, rel))

    lines = [
        "# GameDevMind 关键词索引",
        "",
        "> 由 `tools/check/generate_keywords.py` 自动生成，请勿手动编辑",
        "",
        "配合 [GitHub 搜索技巧](mds/topics/常见问题.md#如何在-github-上搜索) 使用。",
        "",
        "---",
        "",
    ]

    for kw in sorted(keyword_to_docs.keys(), key=lambda k: (-len(keyword_to_docs[k]), k)):
        docs = sorted(set(keyword_to_docs[kw]))[:8]
        extra = len(keyword_to_docs[kw]) - len(docs)
        suffix = f" 等 {len(keyword_to_docs[kw])} 篇" if extra > 0 else ""
        lines.append(f"### {kw}{suffix}")
        lines.append("")
        lines.append(" · ".join(docs))
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    out = ROOT / "KEYWORDS.md"
    out.write_text(render_keywords(), encoding="utf-8", newline="\n")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
