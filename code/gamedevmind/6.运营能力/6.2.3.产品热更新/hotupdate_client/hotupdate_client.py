#!/usr/bin/env python3
"""
hotupdate_client.py — 热更新最小流程演示

流程：拉取远程 manifest → 对比本地版本 → 下载差异文件 → MD5 校验 → 原子替换
对应文档：mds/6.运营能力/6.2.3.产品热更新.md
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

# 演示用：本地「CDN」目录，生产环境替换为真实 CDN URL
DEMO_CDN = Path(__file__).resolve().parent / "demo_cdn"
LOCAL_ROOT = Path(__file__).resolve().parent / "local_assets"
MANIFEST_NAME = "manifest.json"


@dataclass
class FileEntry:
    path: str
    md5: str
    size: int


def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest(source: Path | str) -> Dict[str, FileEntry]:
    if isinstance(source, Path):
        data = json.loads(source.read_text(encoding="utf-8"))
    else:
        with urllib.request.urlopen(source, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

    files = {
        item["path"]: FileEntry(item["path"], item["md5"], item["size"])
        for item in data["files"]
    }
    return {"version": data["version"], "files": files}


def diff_manifests(
    local: Dict, remote: Dict
) -> tuple[str, str, List[FileEntry]]:
    """返回 (local_ver, remote_ver, 需下载列表)"""
    to_download: List[FileEntry] = []
    remote_files: Dict[str, FileEntry] = remote["files"]

    for path, entry in remote_files.items():
        local_path = LOCAL_ROOT / path
        if not local_path.exists():
            to_download.append(entry)
            continue
        if md5_file(local_path) != entry.md5:
            to_download.append(entry)

    return local["version"], remote["version"], to_download


def download_file(entry: FileEntry, cdn_base: Path) -> Path:
    src = cdn_base / entry.path
    tmp = LOCAL_ROOT / f"{entry.path}.download"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, tmp)

    actual = md5_file(tmp)
    if actual != entry.md5:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"MD5 mismatch: {entry.path} expected {entry.md5}, got {actual}")
    return tmp


def apply_updates(entries: List[FileEntry], cdn_base: Path) -> None:
    for entry in entries:
        tmp = download_file(entry, cdn_base)
        target = LOCAL_ROOT / entry.path
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp.replace(target)
        print(f"  ✓ {entry.path} ({entry.size} bytes)")


def write_local_manifest(remote: Dict) -> None:
    manifest_path = LOCAL_ROOT / MANIFEST_NAME
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": remote["version"],
        "files": [
            {"path": e.path, "md5": e.md5, "size": e.size}
            for e in remote["files"].values()
        ],
    }
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def run_update(cdn_base: Path = DEMO_CDN) -> int:
    local_manifest_path = LOCAL_ROOT / MANIFEST_NAME
    if local_manifest_path.exists():
        local = load_manifest(local_manifest_path)
    else:
        local = {"version": "0.0.0", "files": {}}

    remote_manifest_path = cdn_base / MANIFEST_NAME
    remote = load_manifest(remote_manifest_path)

    local_ver, remote_ver, todo = diff_manifests(local, remote)
    print(f"本地版本: {local_ver}  →  远程版本: {remote_ver}")

    if not todo:
        print("已是最新，无需更新。")
        return 0

    print(f"需更新 {len(todo)} 个文件：")
    apply_updates(todo, cdn_base)
    write_local_manifest(remote)
    print("热更新完成。")
    return 0


if __name__ == "__main__":
    sys.exit(run_update())
