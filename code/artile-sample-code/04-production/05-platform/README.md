## 技术中台 — 配套代码

对应文章：四-05-游戏公司技术中台怎么建？通用模块与框架

### 文章章节 ↔ 示例

| 文章章节 | 本目录 | 说明 |
|----------|--------|------|
| 网络模块 INetworkService | `platform_abs.py` | Connect/Send/事件回调 |
| UI 模块 IUIPanel | `platform_abs.py` | 面板开闭与栈管理抽象 |
| 数据持久化 IDataService | `platform_abs.py` | Load/Save 键值存储 |
| 游戏/服务端框架 | 正文 GameFramework 骨架 | 模块初始化与 Update 循环 |
| 设计模式 / EventSystem | `platform_abs.py` | 观察者模式演示 |

### 示例

| 示例 | 文件 | 说明 |
|------|------|------|
| 中台抽象层演示 | `platform_abs.py` | 网络/UI/存储接口与可替换实现 |

### 设计要点

- **接口隔离**: 业务依赖 INetworkService/IDataService，不依赖具体实现
- **可替换实现**: Memory/PlayerPrefs/File 等多种 DataService
- **模块化**: 单一职责，便于多项目复用与独立升级

### 运行

```bash
python3 platform_abs.py
```

### 延伸阅读

- 开源合集：https://github.com/gonglei007/GameDevMind
