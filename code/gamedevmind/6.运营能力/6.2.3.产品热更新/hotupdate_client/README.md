# 热更新客户端最小流程

演示网游热更新的核心链路：**manifest 对比 → 差异下载 → MD5 校验 → 原子替换**。

对应文档：[产品热更新](../../../../../mds/6.运营能力/6.2.3.产品热更新.md)

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

## 与登录兼容/强更的边界

本示例使用仓库内本地目录模拟 CDN，未实现 min/max_app、协议协商、登录认证、强更门禁、清单签名或商店跳转。MD5 只作示例文件完整性对比，不能认证恶意来源；逐文件 replace 也不是整批资源和 manifest 的事务提交。运行会写入本目录 local_assets，请在独立副本中演示；不能以此运行结果宣称强更链路验收通过。

客户端收到可信升级拒绝后停止重试的独立状态机回归见 [client_network](../../../3.研发能力/3.1.4.客户端网络系统/client_network/)，不包含清单或版本能力判断。

## 延伸

- 案例：[热更后旧资源残留](../../../../../cases/hotupdate-stale-assets.md)
- 案例：[大版本强更与兼容](../../../../../cases/major-version-force-update.md)
