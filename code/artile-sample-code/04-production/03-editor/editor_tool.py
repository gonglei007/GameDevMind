#!/usr/bin/env python3
"""
编辑器工具集：批量重命名、依赖图生成、资源使用统计
纯标准库，直接运行。

功能：
  1. 批量重命名（前缀/后缀/正则替换/编号）
  2. 资源依赖图生成（扫描引用关系 → JSON/PlantUML）
  3. 资源使用统计（类型分布、大小top-N、重复检测）
"""
import os
import re
import json
import hashlib
from pathlib import Path
from collections import defaultdict, Counter
from typing import Optional
from dataclasses import dataclass, field


# ══════════════════════════════════════════════════════════════════════
# 1. 批量重命名工具
# ══════════════════════════════════════════════════════════════════════

@dataclass
class RenameRule:
    """重命名规则"""
    add_prefix: str = ""
    add_suffix: str = ""
    replace_pattern: str = ""   # 正则
    replace_with: str = ""
    to_lower: bool = False
    to_upper: bool = False
    number_pad: int = 0         # 编号补齐位数 (0=不编号)
    dry_run: bool = True


def batch_rename(directory: Path, rule: RenameRule,
                 glob_pattern: str = "*") -> list[tuple[str, str]]:
    """批量重命名文件，返回 [(旧名, 新名), ...]"""
    changes = []
    files = sorted(directory.glob(glob_pattern))
    files = [f for f in files if f.is_file()]

    for idx, fp in enumerate(files):
        stem, ext = fp.stem, fp.suffix

        # 正则替换
        if rule.replace_pattern:
            try:
                stem = re.sub(rule.replace_pattern, rule.replace_with, stem)
            except re.error as e:
                print(f"  ⚠ 正则错误: {e}")
                continue

        # 编号
        num_str = ""
        if rule.number_pad > 0:
            num_str = f"_{idx + 1:0{rule.number_pad}d}"

        # 大小写
        if rule.to_lower:
            stem = stem.lower()
        elif rule.to_upper:
            stem = stem.upper()

        new_name = f"{rule.add_prefix}{stem}{rule.add_suffix}{num_str}{ext}"
        new_path = fp.parent / new_name

        if new_name != fp.name:
            changes.append((fp.name, new_name))
            if not rule.dry_run:
                fp.rename(new_path)
            elif new_path.exists():
                changes[-1] = (fp.name, f"{new_name} ⚠(已存在)")

    return changes


# ══════════════════════════════════════════════════════════════════════
# 2. 资源依赖图生成
# ══════════════════════════════════════════════════════════════════════

# 模拟的文件引用关系（实际项目通过 AST/配置解析）
REFERENCE_PATTERNS = {
    ".py":   [r'import\s+(\w+)', r'from\s+(\w+)'],
    ".json": [r'"asset":\s*"([^"]+)"', r'"prefab":\s*"([^"]+)"'],
    ".yaml": [r'ref:\s*(\S+)', r'asset:\s*(\S+)'],
    ".prefab": [r'ref="([^"]+)"'],
}


@dataclass
class DependencyNode:
    """依赖节点"""
    name: str
    path: Path
    file_type: str = ""
    size: int = 0
    dependencies: set = field(default_factory=set)
    dependents: set = field(default_factory=set)


def build_dependency_graph(root_dir: Path) -> dict[str, DependencyNode]:
    """扫描目录构建依赖图"""
    nodes: dict[str, DependencyNode] = {}

    # 第一遍：创建所有节点
    for fp in root_dir.rglob("*"):
        if not fp.is_file():
            continue
        rel = str(fp.relative_to(root_dir))
        ft = fp.suffix.lower()
        nodes[rel] = DependencyNode(
            name=rel, path=fp,
            file_type=ft,
            size=fp.stat().st_size,
        )

    # 第二遍：扫描引用关系
    for rel, node in nodes.items():
        patterns = REFERENCE_PATTERNS.get(node.file_type, [])
        if not patterns:
            continue

        try:
            content = node.path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for pattern in patterns:
            for match in re.finditer(pattern, content):
                dep_name = match.group(1)
                # 尝试匹配已知文件（模糊匹配）
                for other_rel in nodes:
                    if dep_name in other_rel:
                        node.dependencies.add(other_rel)
                        nodes[other_rel].dependents.add(rel)

    return nodes


def export_dependency_graph(nodes: dict[str, DependencyNode],
                            fmt: str = "json") -> str:
    """导出依赖图为 JSON 或 PlantUML"""
    if fmt == "json":
        graph = {}
        for name, node in nodes.items():
            graph[name] = {
                "type": node.file_type,
                "size": node.size,
                "deps": sorted(node.dependencies),
                "used_by": sorted(node.dependents),
            }
        return json.dumps(graph, indent=2, ensure_ascii=False)

    elif fmt == "plantuml":
        lines = ["@startuml", "skinparam packageStyle rectangle"]
        for name, node in nodes.items():
            for dep in sorted(node.dependencies):
                lines.append(f'"{name}" --> "{dep}"')
        lines.append("@enduml")
        return "\n".join(lines)

    elif fmt == "mermaid":
        lines = ["```mermaid", "graph LR"]
        for name, node in nodes.items():
            for dep in sorted(node.dependencies):
                lines.append(f'    "{name}" --> "{dep}"')
        lines.append("```")
        return "\n".join(lines)

    return ""


# ══════════════════════════════════════════════════════════════════════
# 3. 资源使用统计
# ══════════════════════════════════════════════════════════════════════

@dataclass
class AssetStats:
    """资源统计报告"""
    total_files: int = 0
    total_size: int = 0
    by_type: Counter = field(default_factory=Counter)
    by_extension: Counter = field(default_factory=Counter)
    top_largest: list = field(default_factory=list)
    duplicates: list = field(default_factory=list)
    unused: list = field(default_factory=list)


def analyze_assets(root_dir: Path, dependency_graph: dict = None) -> AssetStats:
    """分析资源使用情况"""
    stats = AssetStats()
    size_map: dict[int, list[str]] = defaultdict(list)
    hash_map: dict[str, list[str]] = defaultdict(list)

    for fp in root_dir.rglob("*"):
        if not fp.is_file():
            continue
        rel_path = str(fp.relative_to(root_dir))
        file_size = fp.stat().st_size
        ext = fp.suffix.lower()

        stats.total_files += 1
        stats.total_size += file_size
        stats.by_type[_classify_asset(ext)] += 1
        stats.by_extension[ext] += 1
        size_map[file_size].append(rel_path)

        # 计算 MD5（仅对 <1MB 的文件）
        if file_size < 1024 * 1024:
            try:
                h = hashlib.md5(fp.read_bytes()).hexdigest()
                hash_map[h].append(rel_path)
            except Exception:
                pass

    # Top-N 最大文件
    all_sizes = sorted(size_map.items(), key=lambda x: x[0], reverse=True)
    stats.top_largest = [(path, sz) for sz, paths in all_sizes[:10] for path in paths[:2]]

    # 重复文件检测（相同 hash）
    for h, paths in hash_map.items():
        if len(paths) > 1:
            stats.duplicates.append(paths)

    # 未使用资源检测（如果提供了依赖图）
    if dependency_graph:
        used = set()
        for node in dependency_graph.values():
            used.update(node.dependencies)
            used.update(node.dependents)
        all_files = {str(fp.relative_to(root_dir))
                     for fp in root_dir.rglob("*") if fp.is_file()}
        stats.unused = sorted(all_files - used)

    return stats


def _classify_asset(ext: str) -> str:
    """按扩展名分类资源类型"""
    ext = ext.lower().lstrip(".")
    type_map = {
        "png": "Texture", "jpg": "Texture", "jpeg": "Texture",
        "tga": "Texture", "psd": "Texture", "dds": "Texture",
        "fbx": "Model", "obj": "Model", "gltf": "Model", "glb": "Model",
        "wav": "Audio", "mp3": "Audio", "ogg": "Audio", "flac": "Audio",
        "anim": "Animation",
        "py": "Script", "cpp": "Script", "h": "Script", "cs": "Script",
        "json": "Data", "yaml": "Data", "xml": "Data", "csv": "Data",
        "prefab": "Prefab", "scene": "Scene", "mat": "Material",
        "vert": "Shader", "frag": "Shader", "glsl": "Shader",
    }
    return type_map.get(ext, f"Other(.{ext})")


# ══════════════════════════════════════════════════════════════════════
# 入口
# ══════════════════════════════════════════════════════════════════════

def _create_demo_workspace(base: Path):
    """创建演示用项目目录结构"""
    dirs = ["Assets/Textures", "Assets/Models", "Assets/Audio",
            "Assets/Scripts", "Assets/Prefabs", "Assets/Data",
            "Assets/Animations"]
    files = {
        "Assets/Textures/hero_diffuse.png": b"PNG_DATA" * 200,
        "Assets/Textures/hero_normal.png": b"PNG_DATA" * 180,
        "Assets/Textures/enemy_boss.jpg": b"JPEG_DATA" * 400,
        "Assets/Textures/tile_grass.tga": b"TGA_DATA" * 50,
        "Assets/Textures/tile_grass_OLD.tga": b"TGA_DATA" * 50,  # 重复!
        "Assets/Models/warrior.fbx": b"FBX_MODEL" * 1000,
        "Assets/Models/dragon.gltf": b'{"ref": "dragon_tex.png"}\n' + b"\x00" * 300,
        "Assets/Audio/bgm_forest.ogg": b"OGG_AUDIO" * 800,
        "Assets/Audio/sfx_fireball.wav": b"WAV_AUDIO" * 100,
        "Assets/Scripts/player_controller.py": (
            b"import game_engine\n"
            b"from combat import CombatSystem\n"
            b"from ui import HealthBar\n"
            b"# Main player controller\n" * 5
        ),
        "Assets/Scripts/combat.py": (
            b"import math\n"
            b"from damage import calculate\n"
            b"# Combat system\n" * 5
        ),
        "Assets/Scripts/damage.py": b"def calculate(a, d): return a - d * 0.5\n" * 10,
        "Assets/Scripts/ui.py": b"class HealthBar: pass\n" * 10,
        "Assets/Prefabs/hero.prefab": (
            b'ref="hero_diffuse.png"\n'
            b'ref="warrior.fbx"\n'
            b'ref="player_controller.py"\n'
        ),
        "Assets/Data/items.json": b'{"asset": "sword_icon.png"}\n',
        "Assets/Data/config.yaml": b"ref: config.json\n",
        "Assets/Animations/idle.anim": b"ANIM_IDLE",
    }

    for d in dirs:
        (base / d).mkdir(parents=True, exist_ok=True)
    for fpath, content in files.items():
        (base / fpath).write_bytes(content)


if __name__ == "__main__":
    work_dir = Path("./_editor_demo")
    _create_demo_workspace(work_dir)

    print("=" * 60)
    print("🛠 编辑器工具集")
    print("=" * 60)

    # ── 1. 批量重命名 ──
    print("\n── 1. 批量重命名 ──")
    rule = RenameRule(
        add_prefix="v2_",
        number_pad=3,
        to_lower=True,
        dry_run=True,
    )
    changes = batch_rename(work_dir / "Assets/Textures", rule)
    for old, new in changes:
        print(f"  {old} → {new}")

    # ── 2. 依赖图 ──
    print("\n── 2. 资源依赖图 ──")
    nodes = build_dependency_graph(work_dir)
    print(f"  节点数: {len(nodes)}")
    for name, node in sorted(nodes.items()):
        if node.dependencies or node.dependents:
            print(f"  📄 {name} (type={node.file_type})")
            if node.dependencies:
                print(f"     → 依赖: {', '.join(sorted(node.dependencies)[:3])}")
            if node.dependents:
                print(f"     ← 被引用: {', '.join(sorted(node.dependents)[:3])}")

    # 导出 PlantUML
    uml = export_dependency_graph(nodes, fmt="mermaid")
    print(f"\n  [Mermaid 图]")
    for line in uml.split("\n")[2:-1]:
        print(f"  {line}")

    # ── 3. 资源统计 ──
    print(f"\n── 3. 资源使用统计 ──")
    stats = analyze_assets(work_dir, dependency_graph=nodes)
    print(f"  总文件: {stats.total_files} | 总大小: {stats.total_size:,} 字节")
    print(f"  类型分布: {dict(stats.by_type.most_common())}")
    print(f"  Top-5 最大文件:")
    for path, sz in stats.top_largest[:5]:
        print(f"    {path}: {sz:,} 字节")
    if stats.duplicates:
        print(f"  ⚠ 重复文件组: {len(stats.duplicates)}")
        for dup in stats.duplicates:
            print(f"    {dup}")
    if stats.unused:
        print(f"  💡 疑似未使用文件: {len(stats.unused)}")
        for u in stats.unused[:5]:
            print(f"    {u}")

    # 清理
    import shutil
    if work_dir.exists():
        shutil.rmtree(work_dir)
    print(f"\n🧹 已清理临时文件")
