# 热更新客户端最小流程

演示网游热更新的核心链路：**manifest 对比 → 差异下载 → MD5 校验 → 原子替换**。

对应文档：[产品热更新](../../../../mds/6.运营能力/6.2.3.产品热更新.md)

## 快速运行

```bash
cd hotupdate_client
python hotupdate_client.py
```

预期输出：检测到远程 `1.2.0` 比本地 `1.1.0` 新，下载 `lua/main.lua` 并更新本地 manifest。

## 演示数据说明

| 目录 | 含义 |
|------|------|
| `demo_cdn/` | 模拟 CDN 上的最新资源与 manifest |
| `local_assets/` | 模拟玩家本地已安装资源（缺 `lua/main.lua`） |

## 核心知识点

1. **manifest 驱动**：只传版本号不够，需文件级 MD5 列表做增量更新
2. **先下后换**：下载到 `.download` 临时文件，校验通过再 `replace`，避免半包损坏
3. **差异化更新**：生产环境 manifest 可按渠道/平台/分支拆分（见图谱文档）

## 延伸

- 案例：[热更后旧资源残留](../../../../cases/hotupdate-stale-assets.md)
- 案例：[大版本强更与兼容](../../../../cases/major-version-force-update.md)
