#!/usr/bin/env python3
"""
资源导入管线模拟：原始资源→检查→转换→压缩→输出
纯标准库，直接运行。

管线阶段：
  1. 资源发现（扫描原始目录）
  2. 格式验证（检查扩展名、文件头）
  3. 格式转换（纹理→ASTC/DXT、模型→glTF）
  4. 压缩打包（LZMA压缩、依赖分析）
  5. 输出清单（生成导入报告）
"""
import os
import sys
import hashlib
import lzma
import json
import time
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Optional


# ─── 资源类型 / 平台 ──────────────────────────────────────────────
class AssetType(Enum):
    TEXTURE = auto()
    MODEL = auto()
    AUDIO = auto()
    ANIMATION = auto()
    SHADER = auto()
    CONFIG = auto()
    UNKNOWN = auto()


class Platform(Enum):
    IOS = "ios"
    ANDROID = "android"
    WEB = "web"
    PC = "pc"


# ─── 数据类 ────────────────────────────────────────────────────────
@dataclass
class AssetSource:
    """原始资源"""
    path: Path
    asset_type: AssetType = AssetType.UNKNOWN
    size_bytes: int = 0
    checksum: str = ""

    def __post_init__(self):
        if self.path.exists():
            self.size_bytes = self.path.stat().st_size
            self.checksum = hashlib.sha256(self.path.read_bytes()).hexdigest()[:16]


@dataclass
class ValidationResult:
    """验证结果"""
    asset: AssetSource
    valid: bool = True
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


@dataclass
class ConvertedAsset:
    """转换后资源"""
    source: AssetSource
    output_path: Path
    converted_size: int = 0
    platform: Platform = Platform.PC
    metadata: dict = field(default_factory=dict)


@dataclass
class PipelineReport:
    """管线报告"""
    total: int = 0
    passed: int = 0
    failed: int = 0
    total_size_before: int = 0
    total_size_after: int = 0
    elapsed_ms: float = 0.0
    details: list = field(default_factory=list)


# ─── 阶段 1：资源发现 ─────────────────────────────────────────────
EXTENSION_MAP = {
    ".png": AssetType.TEXTURE, ".jpg": AssetType.TEXTURE,
    ".tga": AssetType.TEXTURE, ".psd": AssetType.TEXTURE,
    ".fbx": AssetType.MODEL, ".obj": AssetType.MODEL,
    ".blend": AssetType.MODEL, ".gltf": AssetType.MODEL,
    ".wav": AssetType.AUDIO, ".mp3": AssetType.AUDIO,
    ".ogg": AssetType.AUDIO, ".flac": AssetType.AUDIO,
    ".anim": AssetType.ANIMATION, ".fbx_anim": AssetType.ANIMATION,
    ".vert": AssetType.SHADER, ".frag": AssetType.SHADER,
    ".glsl": AssetType.SHADER, ".hlsl": AssetType.SHADER,
    ".json": AssetType.CONFIG, ".yaml": AssetType.CONFIG,
    ".toml": AssetType.CONFIG,
}

ASSET_EXTENSIONS = set(EXTENSION_MAP.keys())
KNOWN_HEADERS = {
    b'\x89PNG\r\n\x1a\n': AssetType.TEXTURE,
    b'\xff\xd8\xff': AssetType.TEXTURE,
    b'RIFF': AssetType.AUDIO,
    b'OggS': AssetType.AUDIO,
    b'glTF': AssetType.MODEL,
}


def discover_assets(root_dir: Path, recursive: bool = True) -> list[AssetSource]:
    """扫描目录发现资源文件"""
    assets = []
    glob_method = root_dir.rglob if recursive else root_dir.glob
    for fp in glob_method("*"):
        if fp.is_file() and fp.suffix.lower() in ASSET_EXTENSIONS:
            assets.append(AssetSource(path=fp, asset_type=EXTENSION_MAP.get(fp.suffix.lower(), AssetType.UNKNOWN)))
    return sorted(assets, key=lambda a: a.path.name)


def classify_by_header(asset: AssetSource) -> AssetType:
    """通过文件头魔数二次确认类型"""
    try:
        header = asset.path.open("rb").read(8)
        for magic, atype in KNOWN_HEADERS.items():
            if header.startswith(magic):
                return atype
    except (IOError, PermissionError):
        pass
    return asset.asset_type


# ─── 阶段 2：格式验证 ──────────────────────────────────────────────
def validate_asset(asset: AssetSource, max_size_mb: float = 200.0) -> ValidationResult:
    """验证资源合法性"""
    result = ValidationResult(asset=asset)
    max_bytes = int(max_size_mb * 1024 * 1024)

    if asset.asset_type == AssetType.UNKNOWN:
        result.warnings.append(f"未知资源类型: {asset.path.suffix}")

    if asset.size_bytes == 0:
        result.errors.append("空文件")
        result.valid = False

    if asset.size_bytes > max_bytes:
        result.errors.append(f"文件过大 ({asset.size_bytes / 1024 / 1024:.1f}MB > {max_size_mb}MB)")
        result.valid = False

    if asset.asset_type == AssetType.TEXTURE:
        if asset.path.suffix.lower() not in (".png", ".jpg", ".tga"):
            result.warnings.append("纹理格式建议使用 PNG/JPEG/TGA")
    elif asset.asset_type == AssetType.MODEL:
        if asset.path.suffix.lower() not in (".fbx", ".gltf", ".obj"):
            result.warnings.append("模型格式建议使用 FBX/glTF")

    return result


# ─── 阶段 3：格式转换 ──────────────────────────────────────────────
def convert_asset(asset: AssetSource, platform: Platform,
                   output_dir: Path) -> ConvertedAsset:
    """模拟格式转换（实际项目中调用外部转换器）"""
    platform_ext = {
        Platform.IOS: ".astc.tex",
        Platform.ANDROID: ".etc2.tex",
        Platform.WEB: ".basis.tex",
        Platform.PC: ".dds.tex",
    }

    suffix_map = {
        AssetType.TEXTURE: platform_ext.get(platform, ".tex"),
        AssetType.MODEL: ".glb",
        AssetType.AUDIO: ".bank",
        AssetType.ANIMATION: ".anim.bin",
        AssetType.SHADER: ".shader.bin",
        AssetType.CONFIG: ".data",
        AssetType.UNKNOWN: ".bin",
    }

    out_name = asset.path.stem + suffix_map.get(asset.asset_type, ".bin")
    out_path = output_dir / platform.value / out_name
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 模拟转换（写入占位内容）
    simulated_data = f"CONVERTED:{asset.path.name}:{platform.value}".encode()
    out_path.write_bytes(simulated_data)

    converted = ConvertedAsset(
        source=asset,
        output_path=out_path,
        converted_size=len(simulated_data),
        platform=platform,
        metadata={"original_checksum": asset.checksum, "converter": "pipeline_v1.0"},
    )

    return converted


# ─── 阶段 4：压缩打包 ──────────────────────────────────────────────
def compress_bundle(assets: list[ConvertedAsset], bundle_path: Path) -> Path:
    """将转换后的资源打包为 LZMA 压缩包"""
    bundle = {
        "version": 1,
        "platform": assets[0].platform.value if assets else "unknown",
        "timestamp": time.time(),
        "assets": [],
    }

    for ca in assets:
        entry = {
            "name": ca.output_path.name,
            "original": str(ca.source.path),
            "size": ca.converted_size,
            "checksum": hashlib.md5(ca.output_path.read_bytes()).hexdigest(),
        }
        bundle["assets"].append(entry)

    raw = json.dumps(bundle, indent=2, ensure_ascii=False).encode()
    compressed = lzma.compress(raw)
    bundle_path.write_bytes(compressed)

    return bundle_path


# ─── 阶段 5：输出报告 ──────────────────────────────────────────────
def generate_report(results: list[ValidationResult],
                    converted: list[ConvertedAsset],
                    elapsed_ms: float) -> PipelineReport:
    """生成导入管线报告"""
    report = PipelineReport(
        total=len(results),
        passed=sum(1 for r in results if r.valid),
        failed=sum(1 for r in results if not r.valid),
        total_size_before=sum(r.asset.size_bytes for r in results),
        total_size_after=sum(c.converted_size for c in converted),
        elapsed_ms=elapsed_ms,
    )
    for r in results:
        report.details.append({
            "file": str(r.asset.path.name),
            "type": r.asset.asset_type.name,
            "valid": r.valid,
            "errors": r.errors,
            "warnings": r.warnings,
        })
    return report


# ─── 完整管线 ──────────────────────────────────────────────────────
def run_pipeline(source_dir: Path, output_dir: Path,
                 platforms: list[Platform] = None) -> list[PipelineReport]:
    """执行完整资源导入管线"""
    if platforms is None:
        platforms = [Platform.PC]

    start = time.time()
    # 1. 发现
    sources = discover_assets(source_dir)
    if not sources:
        print("⚠ 未发现任何资源文件，创建模拟资源...")
        sources = _create_demo_assets(source_dir)

    # 2. 验证
    results = [validate_asset(s) for s in sources]

    reports = []
    for plat in platforms:
        plat_start = time.time()
        # 3. 转换（每个平台）
        valid_sources = [r.asset for r in results if r.valid]
        converted = [convert_asset(a, plat, output_dir) for a in valid_sources]

        # 4. 压缩打包
        bundle_path = output_dir / f"bundle_{plat.value}.lzma"
        compress_bundle(converted, bundle_path)

        # 5. 报告
        report = generate_report(results, converted, (time.time() - plat_start) * 1000)
        reports.append(report)

    return reports


def _create_demo_assets(root: Path) -> list[AssetSource]:
    """创建演示用模拟资源文件"""
    root.mkdir(parents=True, exist_ok=True)
    demo_files = {
        "hero.png": b'\x89PNG\r\n\x1a\n' + b'\x00' * 512,
        "tilemap.jpg": b'\xff\xd8\xff' + b'\x00' * 1024,
        "warrior.fbx": b'FBX model placeholder' * 20,
        "bgm_forest.ogg": b'OggS' + b'\x00' * 2048,
        "fireball.wav": b'RIFF' + b'\x00' * 256,
        "idle.anim": b'ANIM\x01' + b'\x00' * 128,
        "standard.vert": b'#version 450\nvoid main(){}\n' * 5,
        "enemies.json": b'{"enemies":[]}\n',
        "huge_file.bin": b'\x00' * (300 * 1024 * 1024),  # 300MB 超大文件
    }

    assets = []
    for name, content in demo_files.items():
        fp = root / name
        fp.write_bytes(content)
        atype = EXTENSION_MAP.get(fp.suffix.lower(), AssetType.UNKNOWN)
        asset = AssetSource(path=fp, asset_type=atype)
        # 二次确认类型
        asset.asset_type = classify_by_header(asset)
        assets.append(asset)

    return assets


# ─── 入口 ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    work_dir = Path("./_pipeline_demo")
    src_dir = work_dir / "raw"
    out_dir = work_dir / "output"

    print("=" * 60)
    print("🎮 资源导入管线模拟")
    print("=" * 60)

    reports = run_pipeline(src_dir, out_dir, platforms=[Platform.IOS, Platform.ANDROID, Platform.PC])

    for report in reports:
        plat = "unknown"
        if report.details:
            plat = report.details[0].get("platform", "unknown")
        print(f"\n── 平台: {plat} ──")
        print(f"  总资源: {report.total}  通过: {report.passed}  失败: {report.failed}")
        print(f"  大小: {report.total_size_before:,} → {report.total_size_after:,} 字节")
        print(f"  耗时: {report.elapsed_ms:.1f}ms")
        for d in report.details:
            status = "✅" if d["valid"] else "❌"
            print(f"  {status} {d['file']} ({d['type']})")
            for err in d["errors"]:
                print(f"     ⚠ {err}")
            for warn in d["warnings"]:
                print(f"     💡 {warn}")

    # 展示打包结果
    print(f"\n📦 打包文件:")
    for bp in sorted(out_dir.glob("*.lzma")):
        print(f"  {bp.name}: {bp.stat().st_size:,} 字节")

    # 清理
    import shutil
    if work_dir.exists():
        shutil.rmtree(work_dir)
    print(f"\n🧹 已清理临时文件")
