## 角色系统开发 — 配套代码

对应文章：三-04-RPG 游戏角色系统怎么设计？属性／技能／装备／背包

### 文章章节 ↔ 示例

| 文章章节 | 本目录 | 说明 |
|----------|--------|------|
| 属性系统 / 修改器链 | `character_system.py` | 基础→装备→Buff 优先级链 |
| 技能系统 | 正文 UseSkill 骨架 | 冷却/施法/效果链 |
| 装备系统 | `character_system.py` | equip() 固定/百分比加成 |
| 背包系统 | 正文 AddItem 骨架 | 堆叠与空位逻辑 |
| Buff 系统 | `character_system.py` | buff() 临时修改器 |

### 示例

| 示例 | 文件 | 说明 |
|------|------|------|
| 属性修改器链 | `character_system.py` | 基础属性→装备加成→Buff 修改器链→最终值 |

### 设计要点

- **修改器优先级**: BASE(0) → 装备固定(10) → 装备%(20) → Buff%(30) → Buff固定(40)
- **修改器链**: 每个 `Attribute` 维护有序 `Modifier` 列表，`get_final()` 逐一应用
- **装备系统**: `equip()` 添加固定/百分比加成
- **Buff 系统**: `buff()` 添加临时修改器（可移除）
- **计算明细**: `get_breakdown()` 输出每一步中间值

### 运行

```bash
python3 character_system.py
```

### 延伸阅读

- 开源合集：https://github.com/gonglei007/GameDevMind
