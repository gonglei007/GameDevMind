#!/usr/bin/env python3
"""
支付验证流程 - 下单→回调→发货→对账
文章: 06-operations/06-payment (游戏支付系统)
纯标准库，python3 直接运行
"""

import time
import json
import hashlib
import hmac
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum


# ============================================================
# 数据模型
# ============================================================
class OrderStatus(Enum):
    CREATED = "created"           # 已创建
    PAYING = "paying"             # 支付中
    PAID = "paid"                 # 已支付（等待回调验证）
    VERIFIED = "verified"         # 已验证
    DELIVERED = "delivered"       # 已发货
    RECONCILED = "reconciled"     # 已对账
    REFUNDED = "refunded"         # 已退款
    FAILED = "failed"             # 失败


@dataclass
class Order:
    """订单"""
    order_id: str
    player_id: int
    product_id: str
    product_name: str
    amount_cents: int             # 金额（分）
    currency: str = "CNY"
    status: OrderStatus = OrderStatus.CREATED
    created_at: float = field(default_factory=time.time)
    paid_at: Optional[float] = None
    delivered_at: Optional[float] = None
    channel_order_id: Optional[str] = None  # 渠道订单号
    callback_raw: Optional[Dict] = None      # 回调原始数据
    signature_verified: bool = False


@dataclass
class Product:
    """商品"""
    product_id: str
    name: str
    price_cents: int
    items: List[Dict] = field(default_factory=list)  # 发货物品列表


@dataclass
class ReconciliationResult:
    """对账结果"""
    date: str
    total_orders: int
    total_amount_cents: int
    matched: int
    unmatched_local: int        # 本地有、渠道无
    unmatched_channel: int      # 渠道有、本地无
    amount_diff_cents: int      # 金额差异
    details: List[Dict] = field(default_factory=list)


# ============================================================
# 签名/验证工具
# ============================================================
class PaymentCrypto:
    """支付签名工具（模拟支付渠道的签名机制）"""

    SECRET_KEY = "zhihu-game-secret-key-2025"

    @staticmethod
    def sign(data: Dict, secret: str = None) -> str:
        """生成签名"""
        key = secret or PaymentCrypto.SECRET_KEY
        # 排序后拼接
        raw = "&".join(f"{k}={v}" for k, v in sorted(data.items()) if v is not None)
        raw += f"&key={key}"
        return hashlib.md5(raw.encode()).hexdigest().upper()

    @staticmethod
    def verify(data: Dict, signature: str, secret: str = None) -> bool:
        """验证签名"""
        expected = PaymentCrypto.sign(data, secret)
        return hmac.compare_digest(expected, signature)


# ============================================================
# 支付系统
# ============================================================
class PaymentSystem:
    """游戏支付系统"""

    def __init__(self):
        self.orders: Dict[str, Order] = {}
        self.products: Dict[str, Product] = {}
        self.delivery_log: List[Dict] = []
        self._register_default_products()

    def _register_default_products(self):
        """注册默认商品"""
        products = [
            Product("zhihu_monthly", "月卡", 3000,
                    [{"type": "diamond", "amount": 300, "desc": "立得300钻石"},
                     {"type": "daily_diamond", "amount": 30, "days": 30, "desc": "每日30钻石x30天"}]),
            Product("zhihu_gift_60", "60钻石", 600,
                    [{"type": "diamond", "amount": 60, "desc": "60钻石"}]),
            Product("zhihu_gift_300", "300钻石", 3000,
                    [{"type": "diamond", "amount": 300, "desc": "300钻石"},
                     {"type": "diamond_bonus", "amount": 30, "desc": "赠30钻石"}]),
            Product("zhihu_gift_648", "6480钻石", 64800,
                    [{"type": "diamond", "amount": 6480, "desc": "6480钻石"},
                     {"type": "diamond_bonus", "amount": 1300, "desc": "赠1300钻石"}]),
            Product("zhihu_battle_pass", "战斗通行证", 6800,
                    [{"type": "battle_pass", "amount": 1, "desc": "本期战斗通行证"}]),
        ]
        for p in products:
            self.products[p.product_id] = p

    def create_order(self, player_id: int, product_id: str) -> Optional[Order]:
        """
        创建订单（下单）
        返回 Order，失败返回 None
        """
        # 验证商品
        if product_id not in self.products:
            print(f"  ❌ 商品 {product_id} 不存在")
            return None

        product = self.products[product_id]

        # 生成订单号
        order_id = f"ZIHU{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"

        order = Order(
            order_id=order_id,
            player_id=player_id,
            product_id=product.product_id,
            product_name=product.name,
            amount_cents=product.price_cents,
            status=OrderStatus.CREATED,
        )
        self.orders[order_id] = order
        print(f"  📝 订单创建: {order_id} | 玩家:{player_id} | {product.name} | ¥{product.price_cents/100:.2f}")
        return order

    def start_pay(self, order_id: str) -> Dict:
        """
        发起支付（模拟向支付渠道发起请求）
        返回支付参数
        """
        order = self.orders.get(order_id)
        if not order:
            return {"error": "订单不存在"}

        if order.status != OrderStatus.CREATED:
            return {"error": f"订单状态异常: {order.status.value}"}

        # 构建支付请求参数
        pay_params = {
            "app_id": "zhihu-game-001",
            "order_id": order.order_id,
            "amount": order.amount_cents,
            "currency": order.currency,
            "product_name": order.product_name,
            "player_id": str(order.player_id),
            "timestamp": str(int(time.time())),
            "nonce": uuid.uuid4().hex[:16],
        }
        pay_params["sign"] = PaymentCrypto.sign(pay_params)

        order.status = OrderStatus.PAYING
        order.channel_order_id = f"CH{pay_params['timestamp']}{pay_params['nonce'][:8].upper()}"

        print(f"  💳 发起支付: {order_id} -> 渠道订单: {order.channel_order_id}")

        return {
            "success": True,
            "order_id": order_id,
            "channel_order_id": order.channel_order_id,
            "pay_params": pay_params,
            "message": "请在支付渠道完成付款",
        }

    def handle_callback(self, callback_data: Dict) -> Dict:
        """
        处理支付回调（支付渠道异步通知）
        这是最重要的环节！必须：
        1. 验证签名
        2. 验证订单信息
        3. 防止重复回调
        4. 发货
        """
        order_id = callback_data.get("order_id")

        # === 步骤1: 查找订单 ===
        order = self.orders.get(order_id)
        if not order:
            return {"success": False, "error": "订单不存在", "order_id": order_id}

        # === 步骤2: 防重检查 ===
        if order.status in (OrderStatus.DELIVERED, OrderStatus.VERIFIED,
                            OrderStatus.RECONCILED):
            print(f"  ⚠️  订单 {order_id} 已处理，跳过重复回调")
            return {"success": True, "message": "already_processed", "order_id": order_id}

        # === 步骤3: 签名验证 ===
        sign = callback_data.pop("sign", "")
        if not PaymentCrypto.verify(callback_data, sign):
            order.status = OrderStatus.FAILED
            print(f"  ❌ 签名验证失败: {order_id}")
            return {"success": False, "error": "签名验证失败", "order_id": order_id}

        # === 步骤4: 金额验证 ===
        channel_amount = int(callback_data.get("amount", 0))
        if channel_amount != order.amount_cents:
            print(f"  ❌ 金额不匹配: 订单{order.amount_cents} vs 回调{channel_amount}")
            return {"success": False, "error": "金额不匹配", "order_id": order_id}

        # === 步骤5: 更新订单状态 ===
        order.status = OrderStatus.VERIFIED
        order.paid_at = time.time()
        order.callback_raw = callback_data
        order.signature_verified = True

        print(f"  ✅ 回调验证通过: {order_id} | ¥{order.amount_cents/100:.2f}")

        # === 步骤6: 发货 ===
        delivery_result = self._deliver(order)
        return delivery_result

    def _deliver(self, order: Order) -> Dict:
        """发货"""
        product = self.products.get(order.product_id)
        if not product:
            return {"success": False, "error": "商品不存在", "order_id": order.order_id}

        delivery_items = []
        for item in product.items:
            delivery_items.append({
                "player_id": order.player_id,
                "type": item["type"],
                "amount": item["amount"],
                "desc": item["desc"],
            })

        # 添加到发货日志
        self.delivery_log.append({
            "order_id": order.order_id,
            "player_id": order.player_id,
            "product_id": order.product_id,
            "items": product.items,
            "delivered_at": time.time(),
        })

        order.status = OrderStatus.DELIVERED
        order.delivered_at = time.time()

        # 打印发货明细
        print(f"  📦 发货完成: {order.order_id}")
        for di in delivery_items:
            print(f"     -> 玩家{di['player_id']}: {di['desc']}")

        return {
            "success": True,
            "order_id": order.order_id,
            "player_id": order.player_id,
            "items": delivery_items,
            "message": "发货成功",
        }

    def reconcile(self, date: str, channel_orders: List[Dict]) -> ReconciliationResult:
        """
        对账：对比本地订单和渠道订单
        channel_orders: 渠道提供的订单列表
        """
        # 本地订单（已支付/已发货的）
        local_paid = {
            o.order_id: o
            for o in self.orders.values()
            if o.status in (OrderStatus.VERIFIED, OrderStatus.DELIVERED,
                            OrderStatus.RECONCILED)
            and datetime.fromtimestamp(o.created_at).strftime("%Y-%m-%d") == date
        }

        # 渠道订单
        channel_map = {co["order_id"]: co for co in channel_orders}

        local_ids = set(local_paid.keys())
        channel_ids = set(channel_map.keys())

        matched = local_ids & channel_ids
        unmatched_local = local_ids - channel_ids
        unmatched_channel = channel_ids - local_ids

        # 金额差异
        amount_diff = 0
        details = []
        for oid in matched:
            local_amt = local_paid[oid].amount_cents
            channel_amt = channel_map[oid]["amount"]
            diff = local_amt - channel_amt
            if diff != 0:
                amount_diff += diff
                details.append({
                    "order_id": oid,
                    "local_amount": local_amt,
                    "channel_amount": channel_amt,
                    "diff": diff,
                })
            # 标记已对账
            local_paid[oid].status = OrderStatus.RECONCILED

        # 记录差异订单
        for oid in unmatched_local:
            details.append({
                "order_id": oid,
                "issue": "本地有，渠道无",
                "local_amount": local_paid[oid].amount_cents,
            })
        for oid in unmatched_channel:
            details.append({
                "order_id": oid,
                "issue": "渠道有，本地无",
                "channel_amount": channel_map[oid]["amount"],
            })

        result = ReconciliationResult(
            date=date,
            total_orders=len(local_paid),
            total_amount_cents=sum(o.amount_cents for o in local_paid.values()),
            matched=len(matched),
            unmatched_local=len(unmatched_local),
            unmatched_channel=len(unmatched_channel),
            amount_diff_cents=amount_diff,
            details=details,
        )

        print(f"\n📊 对账结果 [{date}]:")
        print(f"  总订单: {result.total_orders} | 匹配: {result.matched} | "
              f"本地多余: {result.unmatched_local} | 渠道多余: {result.unmatched_channel}")
        print(f"  总金额: ¥{result.total_amount_cents/100:.2f} | "
              f"金额差异: ¥{result.amount_diff_cents/100:.2f}")

        if result.unmatched_local or result.unmatched_channel or amount_diff != 0:
            print(f"  ⚠️  存在差异，需人工处理!")
            for d in details:
                print(f"     - {d}")

        return result

    def get_order(self, order_id: str) -> Optional[Order]:
        """查询订单"""
        return self.orders.get(order_id)

    def get_statistics(self) -> Dict:
        """统计信息"""
        total = len(self.orders)
        delivered = sum(1 for o in self.orders.values()
                        if o.status == OrderStatus.DELIVERED)
        total_revenue = sum(o.amount_cents for o in self.orders.values()
                            if o.status in (OrderStatus.VERIFIED,
                                            OrderStatus.DELIVERED,
                                            OrderStatus.RECONCILED))
        return {
            "total_orders": total,
            "delivered": delivered,
            "total_revenue_cents": total_revenue,
            "total_revenue_yuan": total_revenue / 100,
        }


def run_demo():
    """运行演示"""
    print("=" * 60)
    print("  游戏支付验证系统 - 演示")
    print("=" * 60)

    ps = PaymentSystem()

    # ====== 1. 下单 ======
    print("\n📝 步骤1: 创建订单")
    print("-" * 40)
    order1 = ps.create_order(1001, "zhihu_monthly")
    order2 = ps.create_order(1002, "zhihu_gift_648")
    order3 = ps.create_order(1003, "zhihu_gift_60")

    # ====== 2. 发起支付 ======
    print("\n💳 步骤2: 发起支付")
    print("-" * 40)
    pay1 = ps.start_pay(order1.order_id)
    pay2 = ps.start_pay(order2.order_id)
    pay3 = ps.start_pay(order3.order_id)

    # ====== 3. 模拟支付回调 ======
    print("\n📲 步骤3: 处理支付回调")
    print("-" * 40)

    # 正常回调
    callback1 = {
        "order_id": order1.order_id,
        "amount": 3000,
        "channel_order_id": order1.channel_order_id,
        "timestamp": str(int(time.time())),
    }
    callback1["sign"] = PaymentCrypto.sign(callback1)
    print("\n  回调1 (正常):")
    ps.handle_callback(callback1)

    # 篡改金额的回调（模拟攻击）
    callback2_fake = {
        "order_id": order2.order_id,
        "amount": 1,  # 攻击者尝试1分钱买648礼包!
        "channel_order_id": order2.channel_order_id,
        "timestamp": str(int(time.time())),
    }
    callback2_fake["sign"] = "INVALID_SIGN"  # 签名无法通过
    print("\n  回调2 (金额被篡改):")
    result2 = ps.handle_callback(callback2_fake)
    print(f"     -> {result2.get('error', result2.get('message'))}")

    # 正常回调2
    callback2_real = {
        "order_id": order2.order_id,
        "amount": 64800,
        "channel_order_id": order2.channel_order_id,
        "timestamp": str(int(time.time())),
    }
    callback2_real["sign"] = PaymentCrypto.sign(callback2_real)
    print("\n  回调2 (正常):")
    ps.handle_callback(callback2_real)

    # 正常回调3
    callback3 = {
        "order_id": order3.order_id,
        "amount": 600,
        "channel_order_id": order3.channel_order_id,
        "timestamp": str(int(time.time())),
    }
    callback3["sign"] = PaymentCrypto.sign(callback3)
    print("\n  回调3 (正常):")
    ps.handle_callback(callback3)

    # ====== 4. 统计 ======
    print("\n📊 步骤4: 交易统计")
    print("-" * 40)
    stats = ps.get_statistics()
    print(f"  总订单: {stats['total_orders']}")
    print(f"  已发货: {stats['delivered']}")
    print(f"  总收入: ¥{stats['total_revenue_yuan']:.2f}")

    # ====== 5. 对账 ======
    print("\n🔍 步骤5: 日终对账")
    print("-" * 40)
    today = datetime.now().strftime("%Y-%m-%d")
    channel_orders = [
        {"order_id": order1.order_id, "amount": 3000},
        {"order_id": order2.order_id, "amount": 64800},
        {"order_id": order3.order_id, "amount": 600},
        {"order_id": "ZIHU_UNKNOWN_01", "amount": 9800},  # 渠道有、本地无
    ]
    ps.reconcile(today, channel_orders)

    # ====== 6. 订单生命周期 ======
    print("\n📋 订单生命周期示例 (订单1):")
    o = ps.get_order(order1.order_id)
    print(f"  {o.order_id}: {o.product_name}")
    print(f"  创建 -> 支付中 -> 已验证 -> 已发货")
    print(f"  金额: ¥{o.amount_cents/100:.2f}")
    print(f"  签名验证: {'✅' if o.signature_verified else '❌'}")

    print("\n✅ 支付验证系统演示完成!")


if __name__ == "__main__":
    run_demo()
