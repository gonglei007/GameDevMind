## GM 后台 — 配套代码

对应文章：六-02-游戏 GM 后台怎么设计？用户管理／数据查询

### 文章章节 ↔ 示例

| 文章章节 | 本目录 | 说明 |
|----------|--------|------|
| 用户管理 / 封禁发奖 | `gm_commands.py` | `ban` / `unban` / `send_item` 命令 |
| 权限管理 | `gm_commands.py` | RBAC 权限级别与命令注册 |
| 操作审计 | `gm_commands.py` | 命令执行日志与追溯 |
| 数据查询 / 运营工具 | 正文为接口骨架 | 完整 Web API 见 GameDevMind |

### 示例

| 示例 | 文件 | 说明 |
|------|------|------|
| GM 命令系统 | `gm_commands.py` | 命令注册、权限校验、冷却、审计日志 |

### 运行

```bash
python3 gm_commands.py
```

纯标准库，无需安装依赖。

### 延伸阅读

- 开源合集：https://github.com/gonglei007/GameDevMind
