#!/usr/bin/env python3
"""
多平台构建脚本：iOS/Android/Web 构建流程模拟
纯标准库，直接运行。

构建流程：
  1. 平台配置加载
  2. 代码编译/转译（模拟）
  3. 资源打包（Texture/Model/Audio → 平台格式）
  4. 签名 & 归档
  5. 构建报告生成
"""
import os
import sys
import json
import time
import shutil
import hashlib
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


# ─── 平台定义 ──────────────────────────────────────────────────────
class BuildPlatform(Enum):
    IOS = auto()
    ANDROID = auto()
    WEB = auto()
    PC_WINDOWS = auto()
    PC_MAC = auto()
    PC_LINUX = auto()


@dataclass
class PlatformConfig:
    """平台构建配置"""
    platform: BuildPlatform
    output_extension: str = ""
    texture_format: str = ""
    script_backend: str = ""     # il2cpp / mono / wasm
    compression: str = ""        # lz4 / lzma / brotli
    sdk_version: str = ""
    defines: list = field(default_factory=list)


PLATFORM_CONFIGS = {
    BuildPlatform.IOS: PlatformConfig(
        BuildPlatform.IOS, ".ipa", "ASTC", "il2cpp", "lz4",
        sdk_version="17.0",
        defines=["IOS", "MOBILE", "METAL"],
    ),
    BuildPlatform.ANDROID: PlatformConfig(
        BuildPlatform.ANDROID, ".apk", "ETC2", "il2cpp", "lz4",
        sdk_version="34",
        defines=["ANDROID", "MOBILE", "VULKAN", "GLES3"],
    ),
    BuildPlatform.WEB: PlatformConfig(
        BuildPlatform.WEB, ".html", "Basis", "wasm", "brotli",
        sdk_version="3.0",
        defines=["WEB", "WEBGL", "OPENGL"],
    ),
    BuildPlatform.PC_WINDOWS: PlatformConfig(
        BuildPlatform.PC_WINDOWS, ".exe", "DXT5", "mono", "lzma",
        sdk_version="10.0",
        defines=["WINDOWS", "PC", "DIRECTX"],
    ),
    BuildPlatform.PC_MAC: PlatformConfig(
        BuildPlatform.PC_MAC, ".app", "ASTC", "mono", "lzma",
        sdk_version="14.0",
        defines=["MAC", "PC", "METAL"],
    ),
}


@dataclass
class BuildStep:
    """构建步骤"""
    name: str
    status: str = "pending"     # pending / running / success / failed / skipped
    elapsed_ms: float = 0.0
    output: str = ""
    warnings: list = field(default_factory=list)
    errors: list = field(default_factory=list)


@dataclass
class BuildResult:
    """构建结果"""
    platform: BuildPlatform
    success: bool = False
    output_path: Path = None
    total_time_ms: float = 0.0
    steps: list = field(default_factory=list)
    artifact_size: int = 0
    warnings_count: int = 0
    errors_count: int = 0


# ─── 构建引擎核心 ──────────────────────────────────────────────────

class BuildEngine:
    """多平台构建引擎"""

    def __init__(self, project_root: Path, output_dir: Path):
        self.project_root = Path(project_root)
        self.output_dir = Path(output_dir)

    def build(self, platform: BuildPlatform,
              clean: bool = False,
              version: str = "1.0.0") -> BuildResult:
        """执行完整构建流程"""
        config = PLATFORM_CONFIGS[platform]
        result = BuildResult(platform=platform)
        start_time = time.time()

        if clean:
            self._clean(platform)

        # 构建阶段流水线
        stages = [
            ("📋 配置验证",   lambda: self._validate_config(config, version)),
            ("🔨 代码编译",   lambda: self._compile_code(config)),
            ("📦 资源打包",   lambda: self._bundle_assets(config)),
            ("🔗 链接/IL2CPP", lambda: self._link_binary(config)),
            ("✍️ 签名",       lambda: self._sign_package(config)),
            ("📐 归档",       lambda: self._archive(config, version)),
        ]

        for stage_name, stage_fn in stages:
            step = BuildStep(name=stage_name)
            step_start = time.time()
            try:
                step.output = stage_fn()
                step.status = "success"
            except BuildError as e:
                step.status = "failed"
                step.errors.append(str(e))
                result.errors_count += 1
            except Exception as e:
                step.status = "failed"
                step.errors.append(f"未预期错误: {e}")
                result.errors_count += 1
            step.elapsed_ms = (time.time() - step_start) * 1000
            result.steps.append(step)

        result.total_time_ms = (time.time() - start_time) * 1000
        result.success = result.errors_count == 0

        if result.success:
            artifact_name = f"game_{platform.name.lower()}_{version}{config.output_extension}"
            result.output_path = self.output_dir / artifact_name
            # 模拟产出大小
            base_sizes = {
                BuildPlatform.IOS: 180_000_000,
                BuildPlatform.ANDROID: 160_000_000,
                BuildPlatform.WEB: 30_000_000,
                BuildPlatform.PC_WINDOWS: 500_000_000,
                BuildPlatform.PC_MAC: 480_000_000,
            }
            result.artifact_size = base_sizes.get(platform, 100_000_000)
            # 写入模拟产出
            result.output_path.parent.mkdir(parents=True, exist_ok=True)
            result.output_path.write_bytes(b"BUILD_ARTIFACT" * 100)

        for s in result.steps:
            result.warnings_count += len(s.warnings)
        return result

    def _validate_config(self, config: PlatformConfig, version: str) -> str:
        """验证构建配置"""
        if not config.output_extension:
            raise BuildError("缺少 output_extension")
        if not config.texture_format:
            raise BuildError("缺少 texture_format")
        return f"版本 {version} | SDK {config.sdk_version} | 定义: {config.defines}"

    def _compile_code(self, config: PlatformConfig) -> str:
        """编译代码（模拟）"""
        src_count = len(list(self.project_root.rglob("*.py"))) + \
                    len(list(self.project_root.rglob("*.cpp")))
        if src_count == 0:
            src_count = 42  # 模拟
        time.sleep(0.05)
        return f"编译 {src_count} 个源文件 → {config.script_backend}"

    def _bundle_assets(self, config: PlatformConfig) -> str:
        """资源打包（模拟）"""
        texture_count = random.randint(30, 200)
        model_count = random.randint(5, 50)
        audio_count = random.randint(10, 80)
        time.sleep(0.03)
        return (f"纹理({texture_count})→{config.texture_format} | "
                f"模型({model_count}) | 音频({audio_count}) | "
                f"压缩:{config.compression}")

    def _link_binary(self, config: PlatformConfig) -> str:
        """链接/IL2CPP 转换"""
        if config.script_backend == "il2cpp":
            time.sleep(0.08)
            return "IL2CPP 转换完成 (C# → C++ → 本机代码)"
        elif config.script_backend == "wasm":
            time.sleep(0.05)
            return "WebAssembly 编译完成 (.wasm)"
        else:
            time.sleep(0.02)
            return "Mono 链接完成"

    def _sign_package(self, config: PlatformConfig) -> str:
        """签名"""
        if config.platform == BuildPlatform.IOS:
            return "iOS 签名: 开发者证书 + 描述文件"
        elif config.platform == BuildPlatform.ANDROID:
            return "Android 签名: keystore (SHA-256)"
        elif config.platform == BuildPlatform.WEB:
            return "Web: 跳过签名（HTTPS 传输安全）"
        else:
            return "PC: 可选代码签名"

    def _archive(self, config: PlatformConfig, version: str) -> str:
        """归档"""
        archive_name = f"game_{config.platform.name}_{version}_build_{int(time.time())}"
        return f"归档至: {self.output_dir / archive_name}{config.output_extension}"

    def _clean(self, platform: BuildPlatform):
        """清理旧构建产物"""
        for f in self.output_dir.glob(f"*{platform.name.lower()}*"):
            if f.is_file():
                f.unlink()


class BuildError(Exception):
    """构建错误"""
    pass


# ─── 批量构建 ──────────────────────────────────────────────────────

def build_all(engine: BuildEngine,
              platforms: list[BuildPlatform] = None,
              version: str = "1.0.0",
              parallel: bool = False) -> list[BuildResult]:
    """批量构建多个平台"""
    if platforms is None:
        platforms = list(PLATFORM_CONFIGS.keys())

    results = []
    for plat in platforms:
        result = engine.build(plat, clean=True, version=version)
        results.append(result)
    return results


def print_build_report(results: list[BuildResult]):
    """打印构建报告"""
    print(f"\n{'='*70}")
    print(f"{'📊 构建报告':^70}")
    print(f"{'='*70}")

    total_time = 0
    for r in results:
        status_icon = "✅" if r.success else "❌"
        plat_name = r.platform.name
        t = r.total_time_ms
        total_time += t
        artifact = r.output_path.name if r.output_path else "N/A"
        print(f"  {status_icon} {plat_name:12s} | {t:8.1f}ms | "
              f"{r.artifact_size / 1_000_000:6.1f}MB | {artifact}")
        for s in r.steps:
            s_icon = {"success": "✓", "failed": "✗", "skipped": "-"}.get(s.status, "?")
            print(f"     {s_icon} {s.name}: {s.output[:60]}")
            for err in s.errors[:2]:
                print(f"       ⚠ {err}")

    print(f"{'─'*70}")
    print(f"  ⏱ 总耗时: {total_time:.0f}ms | "
          f"成功: {sum(1 for r in results if r.success)}/{len(results)}")


# ─── 入口 ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import random
    # 使用随机种子确保输出一致但可演示
    random.seed(42)

    print("=" * 60)
    print("🏗 多平台构建工具")
    print("=" * 60)

    project_root = Path("./_build_demo_project")
    output_dir = Path("./_build_demo_output")
    project_root.mkdir(parents=True, exist_ok=True)

    # 创建一些模拟源文件
    for src in ["main.py", "game_engine.py", "renderer.py", "network.py"]:
        (project_root / src).write_text("# source file\n" * 10)

    engine = BuildEngine(project_root, output_dir)

    # 单平台构建演示
    print("\n── 单平台构建 (iOS) ──")
    result = engine.build(BuildPlatform.IOS, clean=True)
    for s in result.steps:
        icon = {"success": "✓", "failed": "✗"}.get(s.status, "?")
        print(f"  {icon} {s.name} ({s.elapsed_ms:.0f}ms): {s.output}")

    # 全平台批量构建
    print("\n── 全平台批量构建 ──")
    all_platforms = [BuildPlatform.IOS, BuildPlatform.ANDROID,
                     BuildPlatform.WEB, BuildPlatform.PC_WINDOWS, BuildPlatform.PC_MAC]
    all_results = build_all(engine, all_platforms)
    print_build_report(all_results)

    # 清理
    shutil.rmtree(project_root)
    shutil.rmtree(output_dir)
    print(f"\n🧹 已清理临时文件")
