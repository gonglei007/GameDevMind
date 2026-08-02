## 登录与支付 — 配套代码

对应文章：六-06-游戏登录和支付怎么接入？方案设计要点

### 文章章节 ↔ 示例

| 文章章节 | 本目录 | 说明 |
|----------|--------|------|
| 订单创建 / 支付回调 | `payment_verify.py` | 下单、签名验证、幂等发货 |
| 对账系统 | `payment_verify.py` | 渠道账单与本地订单对比 |
| 登录 / Token | 正文为接口骨架 | JWT 与第三方登录见 GameDevMind |

### 示例

| 示例 | 文件 | 说明 |
|------|------|------|
| 支付验证流程 | `payment_verify.py` | 下单→回调→验签→发货→对账 |

### 运行

```bash
python3 payment_verify.py
```

纯标准库，无需安装依赖。

### 延伸阅读

- 开源合集：https://github.com/gonglei007/GameDevMind
