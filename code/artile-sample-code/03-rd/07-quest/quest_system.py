"""
游戏任务系统 — 状态机驱动

对应文章：三-07-任务系统开发
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Callable, Dict, Any


class QuestState(Enum):
    LOCKED = "locked"
    AVAILABLE = "available"
    ACTIVE = "active"
    COMPLETED = "completed"
    CLAIMED = "claimed"


@dataclass
class Quest:
    id: str
    name: str
    desc: str
    state: QuestState = QuestState.LOCKED
    prerequisites: List[str] = field(default_factory=list)
    objectives: List[Dict] = field(default_factory=list)
    rewards: Dict[str, int] = field(default_factory=dict)
    progress: Dict[int, int] = field(default_factory=dict)

    def can_accept(self) -> bool:
        return self.state == QuestState.AVAILABLE

    def update_progress(self, obj_idx: int, amount: int = 1):
        if self.state != QuestState.ACTIVE:
            return
        obj = self.objectives[obj_idx]
        key = obj_idx
        self.progress[key] = min(
            self.progress.get(key, 0) + amount,
            obj.get("target", 1)
        )
        if all(
            self.progress.get(i, 0) >= o.get("target", 1)
            for i, o in enumerate(self.objectives)
        ):
            self.state = QuestState.COMPLETED

    def claim(self) -> dict:
        if self.state == QuestState.COMPLETED:
            self.state = QuestState.CLAIMED
            return self.rewards
        return {}


class QuestManager:
    def __init__(self):
        self._quests: Dict[str, Quest] = {}

    def add(self, quest: Quest):
        self._quests[quest.id] = quest

    def get(self, qid: str) -> Quest:
        return self._quests.get(qid)

    def accept(self, qid: str) -> bool:
        q = self._quests.get(qid)
        if q and q.can_accept():
            q.state = QuestState.ACTIVE
            return True
        return False

    def unlock(self, qid: str):
        q = self._quests.get(qid)
        if q and q.state == QuestState.LOCKED:
            prereqs_met = all(
                self._quests[p].state == QuestState.CLAIMED
                for p in q.prerequisites
            )
            if prereqs_met:
                q.state = QuestState.AVAILABLE

    def list_by_state(self, state: QuestState) -> List[Quest]:
        return [q for q in self._quests.values() if q.state == state]


def main():
    print("=== 游戏任务系统演示 ===\n")

    mgr = QuestManager()

    # 添加任务链：新手引导 → 初次战斗 → 加入公会
    mgr.add(Quest("Q1", "新手引导", "完成新手教程", QuestState.AVAILABLE,
                  objectives=[{"type": "talk", "target": 3, "desc": "与NPC对话"}],
                  rewards={"gold": 100, "exp": 50}))

    mgr.add(Quest("Q2", "初次战斗", "击败史莱姆", QuestState.LOCKED,
                  prerequisites=["Q1"],
                  objectives=[{"type": "kill", "target": 5, "desc": "击败史莱姆"}],
                  rewards={"gold": 200, "sword_lv1": 1}))

    mgr.add(Quest("Q3", "加入公会", "找到公会大厅", QuestState.LOCKED,
                  prerequisites=["Q2"],
                  objectives=[{"type": "talk", "target": 1, "desc": "与公会管理员对话"}],
                  rewards={"gold": 500, "title": "新人"}))

    # 演示任务链
    print("[接取 Q1: 新手引导]")
    mgr.accept("Q1")
    q1 = mgr.get("Q1")
    q1.update_progress(0, 2)
    print(f"  进度: {q1.progress}")
    q1.update_progress(0, 1)
    print(f"  完成! 奖励: {q1.claim()}"  )

    print("\n[解锁并接取 Q2]")
    mgr.unlock("Q2")
    mgr.accept("Q2")
    q2 = mgr.get("Q2")
    for i in range(5):
        q2.update_progress(0)
    print(f"  完成! 奖励: {q2.claim()}")

    print("\n[解锁并接取 Q3]")
    mgr.unlock("Q3")
    mgr.accept("Q3")
    q3 = mgr.get("Q3")
    q3.update_progress(0)
    print(f"  完成! 奖励: {q3.claim()}")

    print("\n✅ 任务链全部完成！")


if __name__ == "__main__":
    main()
