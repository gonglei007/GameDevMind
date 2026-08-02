#!/usr/bin/env python3
"""生成 sample/hero_config.xlsx 演示文件"""
from pathlib import Path
from openpyxl import Workbook

base = Path(__file__).resolve().parent / "sample"
base.mkdir(parents=True, exist_ok=True)
path = base / "hero_config.xlsx"

wb = Workbook()
ws = wb.active
ws.title = "hero"
ws.append(["id", "name", "hp", "attack", "is_rare"])
ws.append(["int", "string", "int", "int", "bool"])
ws.append(["英雄ID", "名称", "生命", "攻击", "是否稀有"])
ws.append([1001, "剑士", 1200, 85, True])
ws.append([1002, "法师", 800, 120, False])
ws.append([1003, "弓手", 950, 95, True])
wb.save(path)
print(f"created {path}")
