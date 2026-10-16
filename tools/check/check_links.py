#!/usr/bin/env python3
"""Offline gate for published Markdown/HTML file targets and heading anchors."""
from lib_links import check_links, content_files


def main() -> int:
    files = content_files()
    errors, checked = check_links(files)
    for error in errors:
        print(f"ERROR: {error}")
    print(f"Checked {checked} internal links in {len(files)} files; {len(errors)} errors")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
