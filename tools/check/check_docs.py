#!/usr/bin/env python3
"""
GameDevMind 文档质量检查 — 本地与 CI 共用。

用法:
  python tools/check/check_docs.py
  python tools/check/check_docs.py --warn-only
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_config import ROOT, load_config
from lib_links import links_in, local_target

KW_RE = re.compile(r"\*\*关键词:\*\*", re.IGNORECASE)
TAG_RE = re.compile(r"\*\*标签:\*\*", re.IGNORECASE)
RAW_TRUE_RE = re.compile(r"\?raw=true")


def is_leaf_doc(path: Path, cfg: dict) -> bool:
    check = cfg["check"]
    if path.name in check.get("skip_filenames", []):
        return False
    if path.name.startswith("x-"):
        return False
    for part in path.parts:
        if part in check.get("skip_dir_names", []):
            return False
    pattern = re.compile(check["leaf_doc_pattern"])
    return bool(pattern.match(path.name))


def resolve_path(md_file: Path, target: str) -> Path | None:
    result = local_target(md_file, target)
    return result[0] if result else None


def iter_markdown_files(mds_dir: Path) -> list[Path]:
    return sorted(mds_dir.rglob("*.md"))


def check_file(path: Path, cfg: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    rel = path.relative_to(ROOT)
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        errors.append(f"{rel}: not UTF-8")
        return errors, warnings

    check_cfg = cfg["check"]
    if is_leaf_doc(path, cfg):
        if check_cfg.get("require_keywords") and not KW_RE.search(text):
            errors.append(f"{rel}: missing **关键词:**")
        if check_cfg.get("require_tags") and not TAG_RE.search(text):
            errors.append(f"{rel}: missing **标签:**")

    for link in links_in(text):
        if not link.image:
            continue
        resolved = resolve_path(path, link.target)
        if resolved is not None and not resolved.is_file():
            errors.append(f"{rel}:{link.line}: missing image → {link.target}")

    if check_cfg.get("warn_raw_true") and RAW_TRUE_RE.search(text):
        warnings.append(f"{rel}: contains ?raw=true (prefer plain relative paths)")

    if check_cfg.get("warn_trailing_whitespace"):
        for i, line in enumerate(text.splitlines(), 1):
            if line.endswith(" ") or line.endswith("\t"):
                warnings.append(f"{rel}:{i}: trailing whitespace")
                break

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Check GameDevMind markdown docs")
    parser.add_argument(
        "--warn-only",
        action="store_true",
        help="Only print warnings; exit 0 unless errors",
    )
    args = parser.parse_args()

    cfg = load_config()
    mds_dir = ROOT / cfg["repo"]["mds_dir"]
    if not mds_dir.is_dir():
        print(f"ERROR: {mds_dir} not found", file=sys.stderr)
        return 2

    all_errors: list[str] = []
    all_warnings: list[str] = []

    for md in iter_markdown_files(mds_dir):
        errs, warns = check_file(md, cfg)
        all_errors.extend(errs)
        all_warnings.extend(warns)

    if all_warnings:
        print(f"=== Warnings ({len(all_warnings)}) ===")
        for w in all_warnings[:50]:
            print(f"  ⚠️  {w}")
        if len(all_warnings) > 50:
            print(f"  ... and {len(all_warnings) - 50} more")

    if all_errors:
        print(f"\n=== Errors ({len(all_errors)}) ===")
        for e in all_errors[:50]:
            print(f"  ❌ {e}")
        if len(all_errors) > 50:
            print(f"  ... and {len(all_errors) - 50} more")
        return 1

    print(f"\n✅ Checked {len(list(iter_markdown_files(mds_dir)))} files under {mds_dir}")
    if all_warnings and not args.warn_only:
        print(f"   ({len(all_warnings)} warnings — see above)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
