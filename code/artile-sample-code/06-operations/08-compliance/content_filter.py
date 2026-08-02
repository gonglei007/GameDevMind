"""
内容审核过滤器

对应文章：六-08-产品合规
"""

import re


class ContentFilter:
    def __init__(self):
        self._keywords = {"外挂", "私服", "赌博", "代充"}
        self._patterns = [
            (re.compile(r"\b(?:\d{17}[\dXx])\b"), "身份证号"),
            (re.compile(r"1[3-9]\d{9}"), "手机号"),
            (re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+"), "邮箱"),
        ]
        self._banned_words = {"fuck", "shit", "asshole"}

    def check_name(self, name: str) -> tuple:
        """检查玩家昵称，返回 (通过, 原因)"""
        if len(name) < 2:
            return False, "昵称过短"
        if len(name) > 12:
            return False, "昵称过长"

        lower = name.lower()
        for word in self._banned_words:
            if word in lower:
                return False, f"包含敏感词: {word}"
        return True, "OK"

    def check_chat(self, msg: str) -> tuple:
        """检查聊天内容"""
        for pattern, desc in self._patterns:
            if pattern.search(msg):
                return False, f"疑似包含{desc}，已拦截"

        for kw in self._keywords:
            if kw in msg:
                return False, f"包含敏感关键词: {kw}"
        return True, "OK"

    def mask_sensitive(self, msg: str) -> str:
        """脱敏处理"""
        for pattern, _ in self._patterns:
            msg = pattern.sub("***", msg)
        return msg


def main():
    print("=== 内容审核过滤器演示 ===\n")

    cf = ContentFilter()

    print("[昵称检查]")
    tests = [("玩家123",), ("ab",), ("f***er",), ("超长昵称超过十二个字")]
    for name, *rest in tests:
        name = tests[tests.index((name, *rest))][0]
    for name in ["玩家123", "ab", "fucker123", "超长昵称超过十二个字"]:
        ok, reason = cf.check_name(name)
        print(f"  {'✅' if ok else '❌'} {name}: {reason}")

    print("\n[聊天内容检查]")
    for msg in ["你好啊", "加我微信 13800138000", "卖外挂加Q", "test@qq.com联系"]:
        ok, reason = cf.check_chat(msg)
        print(f"  {'✅' if ok else '❌'} {msg}: {reason}")

    print("\n✅ 内容审核演示完成")

if __name__ == "__main__":
    main()
