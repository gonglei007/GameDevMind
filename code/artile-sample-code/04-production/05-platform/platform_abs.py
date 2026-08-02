"""
平台抽象层 — 跨平台接口统一

对应文章：四-05-技术中台
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

# 文件系统抽象
class FileSystem(ABC):
    @abstractmethod
    def read(self, path: str) -> str: ...
    @abstractmethod
    def write(self, path: str, data: str): ...
    @abstractmethod
    def exists(self, path: str) -> bool: ...

class LocalFS(FileSystem):
    def __init__(self, root="/tmp/game"):
        self.root = root
    def read(self, path): return f"[local] data from {path}"
    def write(self, path, data): print(f"  💾 写入 {self.root}/{path}")
    def exists(self, path): return True

class CloudFS(FileSystem):
    def read(self, path): return f"[cloud] data from {path}"
    def write(self, path, data): print(f"  ☁️ 上传到云存储: {path}")
    def exists(self, path): return False

# 输入抽象
class Input(ABC):
    @abstractmethod
    def get_touch(self) -> Optional[tuple]: ...

class TouchInput(Input):
    def get_touch(self): return (100, 200)

class MouseInput(Input):
    def get_touch(self): return (500, 300)

class Platform:
    def __init__(self, name: str, fs: FileSystem, inp: Input):
        self.name = name
        self.fs = fs
        self.input = inp

    def save_game(self, slot: int, data: str):
        self.fs.write(f"save_{slot}.sav", data)

    def load_game(self, slot: int) -> str:
        return self.fs.read(f"save_{slot}.sav")


def main():
    print("=== 平台抽象层演示 ===\n")
    mobile = Platform("iOS", LocalFS(), TouchInput())
    pc = Platform("PC", CloudFS(), MouseInput())

    for p in [mobile, pc]:
        print(f"[{p.name}]")
        p.save_game(1, "player_data")
        touch = p.input.get_touch()
        print(f"  输入坐标: {touch}")
        print()

    print("✅ 平台抽象层演示完成")

if __name__ == "__main__":
    main()
