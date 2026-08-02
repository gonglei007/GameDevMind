#!/usr/bin/env python3
"""
音频混音器模拟 — 音量/声道平衡/淡入淡出/优先级队列

纯标准库实现，模拟游戏音频引擎核心：
1. 音量控制 — 线性/分贝音量调节
2. 声道平衡 (Pan) — 左右声道分配
3. 淡入淡出 — 线性/指数渐变
4. 优先级队列 — 高优先级声音抢占低优先级

运行：python audio_mixer.py
"""

import math
import time
import heapq
import random
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import List, Optional, Callable


# ══════════════════════════════════════════════
# 音频基础类型
# ══════════════════════════════════════════════

class AudioPriority(IntEnum):
    """音频优先级（值越小优先级越高）"""
    CRITICAL = 0    # UI 确认、菜单选择
    HIGH = 1        # 技能音效、脚步声
    MEDIUM = 2      # 环境音、NPC 对话
    LOW = 3         # 背景音乐、氛围


class FadeType(Enum):
    NONE = "none"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"


@dataclass
class AudioClip:
    """音频片段描述"""
    name: str
    priority: AudioPriority = AudioPriority.MEDIUM
    volume: float = 1.0          # 音量 0.0 ~ 1.0
    pan: float = 0.0             # 声道平衡 -1.0(左) ~ +1.0(右)
    duration: float = 1.0        # 时长(秒)
    fade_in: float = 0.0         # 淡入时长
    fade_out: float = 0.0        # 淡出时长
    fade_type: FadeType = FadeType.LINEAR
    is_loop: bool = False
    play_id: int = 0             # 播放实例 ID

    def __lt__(self, other: "AudioClip"):
        """优先级队列排序：优先级值小的先播放"""
        return self.priority.value < other.priority.value


# ══════════════════════════════════════════════
# 混音器核心
# ══════════════════════════════════════════════

@dataclass
class ActiveVoice:
    """活跃的播放声道"""
    clip: AudioClip
    elapsed: float = 0.0         # 已播放时长
    current_volume: float = 1.0  # 当前实际音量（受淡入淡出影响）
    is_playing: bool = True


class AudioMixer:
    """音频混音器

    模拟真实音频引擎的混音管线：
    1. 优先级队列 → 高优先级先播放
    2. 音量 + Pan → 左右声道分配
    3. 淡入淡出 → 随时间渐变音量
    4. 声道限制 → 同优先级最多 N 个声道
    """

    def __init__(self, max_voices: int = 8):
        self.max_voices = max_voices
        self.active_voices: List[ActiveVoice] = []
        self.event_log: List[str] = []
        self.master_volume: float = 1.0       # 主音量

    # ── 音量/增益 ──

    @staticmethod
    def linear_to_db(linear: float) -> float:
        """线性音量 → 分贝 (0.0~1.0 → -inf~0dB)"""
        if linear <= 0:
            return float("-inf")
        return 20.0 * math.log10(linear)

    @staticmethod
    def db_to_linear(db: float) -> float:
        """分贝 → 线性音量"""
        if db <= -96:
            return 0.0
        return 10.0 ** (db / 20.0)

    # ── 声道平衡 ──

    @staticmethod
    def pan_gains(pan: float) -> tuple:
        """Pan (-1~1) → (左声道增益, 右声道增益)

        使用等功率定律 (equal power law):
        - pan=-1: 完全左声道
        - pan= 0: 居中
        - pan=+1: 完全右声道
        """
        pan = max(-1.0, min(1.0, pan))
        # 等功率：左+右声能恒定
        angle = (pan + 1.0) * math.pi / 4.0  # 映射到 0~π/2
        left_gain = math.cos(angle)
        right_gain = math.sin(angle)
        return left_gain, right_gain

    # ── 淡入淡出 ──

    def _apply_fade(self, voice: ActiveVoice) -> float:
        """根据淡入淡出计算当前音量倍率"""
        clip = voice.clip
        t = voice.elapsed
        gain = 1.0

        # 淡入阶段
        if clip.fade_in > 0 and t < clip.fade_in:
            progress = t / clip.fade_in
            if clip.fade_type == FadeType.LINEAR:
                gain *= progress
            elif clip.fade_type == FadeType.EXPONENTIAL:
                gain *= progress ** 2

        # 淡出阶段
        remain = clip.duration - t
        if clip.fade_out > 0 and remain < clip.fade_out and remain > 0:
            progress = remain / clip.fade_out
            if clip.fade_type == FadeType.LINEAR:
                gain *= progress
            elif clip.fade_type == FadeType.EXPONENTIAL:
                gain *= progress ** 2

        return gain

    # ── 播放控制 ──

    def play(self, clip: AudioClip) -> bool:
        """请求播放音频。返回 True 表示成功加入播放队列"""
        # 检查声道是否已满
        # 统计同优先级或更高优先级的活跃声道
        active_count = sum(
            1 for v in self.active_voices
            if v.clip.priority <= clip.priority and v.is_playing
        )

        if active_count >= self.max_voices:
            # 尝试抢占最低优先级的声道
            victim = None
            for v in self.active_voices:
                if v.clip.priority > clip.priority and v.is_playing:
                    if victim is None or v.clip.priority > victim.clip.priority:
                        victim = v

            if victim:
                self._log(f"🔇 抢占: '{victim.clip.name}' (P{victim.clip.priority.value}) "
                          f"被 '{clip.name}' (P{clip.priority.value}) 抢占")
                victim.is_playing = False
                self.active_voices.remove(victim)
            else:
                self._log(f"❌ 拒绝: '{clip.name}' — 声道已满且无可抢占")
                return False

        voice = ActiveVoice(clip=clip)
        self.active_voices.append(voice)
        self._log(f"▶️  播放: '{clip.name}' "
                  f"vol={clip.volume:.2f} pan={clip.pan:+.1f} "
                  f"fade_in={clip.fade_in:.1f}s fade_out={clip.fade_out:.1f}s")
        return True

    def stop(self, clip_name: str):
        """按名称停止播放"""
        for v in self.active_voices:
            if v.clip.name == clip_name:
                v.is_playing = False
                self._log(f"⏹️  停止: '{clip_name}'")

    def stop_all(self):
        """停止所有"""
        for v in self.active_voices:
            v.is_playing = False
        self.active_voices.clear()
        self._log("⏹️  全部停止")

    # ── 每帧更新 ──

    def update(self, dt: float) -> List[dict]:
        """每帧调用，返回当前混音输出"""
        output = []

        for v in list(self.active_voices):
            if not v.is_playing:
                self.active_voices.remove(v)
                continue

            v.elapsed += dt

            # 淡入淡出
            fade_gain = self._apply_fade(v)
            v.current_volume = v.clip.volume * fade_gain * self.master_volume

            # Pan
            l_gain, r_gain = self.pan_gains(v.clip.pan)

            left = v.current_volume * l_gain
            right = v.current_volume * r_gain

            output.append({
                "name": v.clip.name,
                "left": left,
                "right": right,
                "volume": v.current_volume,
                "elapsed": v.elapsed,
                "duration": v.clip.duration,
            })

            # 结束检测
            if v.elapsed >= v.clip.duration:
                if v.clip.is_loop:
                    v.elapsed = 0.0
                    self._log(f"🔁 循环: '{v.clip.name}'")
                else:
                    v.is_playing = False
                    self._log(f"⏹️  结束: '{v.clip.name}' (duration={v.clip.duration:.1f}s)")

        return output

    # ── 可视化 ──

    def visualize(self, output: List[dict], width: int = 40) -> str:
        """ASCII 可视化当前混音状态"""
        if not output:
            return "  (静音)"

        lines = []
        for entry in output:
            name = entry["name"][:12]
            l_bar = int(entry["left"] * width)
            r_bar = int(entry["right"] * width)
            l_ch = "▓" * l_bar + "░" * (width - l_bar)
            r_ch = "▓" * r_bar + "░" * (width - r_bar)
            elapsed = entry["elapsed"]
            duration = entry["duration"]
            progress = f"{elapsed:.1f}s/{duration:.1f}s" if duration > 0 else "—"
            lines.append(f"  {name:<12} L[{l_ch}]")
            lines.append(f"  {'':12} R[{r_ch}] {progress} vol={entry['volume']:.2f}")
        return "\n".join(lines)

    def _log(self, msg: str):
        self.event_log.append(f"[{time.time():.1f}] {msg}")


# ══════════════════════════════════════════════
# 演示
# ══════════════════════════════════════════════

def demo_volume_pan():
    """演示音量和 Pan 计算"""
    print("═══ 1. 音量与声道平衡演示 ═══")

    mixer = AudioMixer()

    print("\n  dB 转换:")
    for lin in [1.0, 0.5, 0.25, 0.1, 0.01]:
        db = mixer.linear_to_db(lin)
        back = mixer.db_to_linear(db)
        print(f"    linear={lin:.2f} → {db:+.1f} dB → {back:.3f}")

    print("\n  Pan 等功率分配:")
    for pan in [-1.0, -0.5, 0.0, 0.5, 1.0]:
        l, r = mixer.pan_gains(pan)
        power = l ** 2 + r ** 2
        print(f"    pan={pan:+.1f} → L={l:.3f} R={r:.3f} | 功率和={power:.3f}")
    print()


def demo_fade():
    """演示淡入淡出"""
    print("═══ 2. 淡入淡出演示 ═══")

    mixer = AudioMixer()

    clips = [
        AudioClip("sword_swing", AudioPriority.HIGH, volume=0.8, pan=0.0,
                  duration=1.0, fade_in=0.3, fade_out=0.2, fade_type=FadeType.LINEAR),
        AudioClip("explosion", AudioPriority.CRITICAL, volume=1.0, pan=0.5,
                  duration=2.0, fade_in=0.1, fade_out=0.5, fade_type=FadeType.EXPONENTIAL),
    ]

    for c in clips:
        mixer.play(c)

    dt = 0.1
    for tick in range(25):
        output = mixer.update(dt)
        if not output:
            break
        if tick % 5 == 0 or tick < 5 or tick >= 20:
            print(f"\n  t={tick * dt:.1f}s:")
            print(mixer.visualize(output, width=30))

    print()


def demo_priority():
    """演示优先级抢占"""
    print("═══ 3. 优先级队列与抢占演示 ═══")

    mixer = AudioMixer(max_voices=3)  # 限制 3 个声道

    clips = [
        AudioClip("bgm_ambient", AudioPriority.LOW, volume=0.5, pan=0.0, duration=10.0),
        AudioClip("footstep", AudioPriority.HIGH, volume=0.6, pan=-0.3, duration=0.5),
        AudioClip("ui_click", AudioPriority.CRITICAL, volume=0.4, pan=0.0, duration=0.2),
        AudioClip("wind_loop", AudioPriority.MEDIUM, volume=0.3, pan=0.8, duration=8.0),
        AudioClip("gunshot", AudioPriority.HIGH, volume=0.9, pan=0.0, duration=0.3),
        AudioClip("menu_music", AudioPriority.LOW, volume=0.7, pan=0.0, duration=5.0, is_loop=True),
    ]

    for i, clip in enumerate(clips):
        print(f"\n  请求 #{i + 1}: '{clip.name}' (P{clip.priority.value})")
        ok = mixer.play(clip)
        print(f"  结果: {'✅ 播放' if ok else '❌ 拒绝'}")
        print(f"  活跃声道: {[(v.clip.name, v.clip.priority.name) for v in mixer.active_voices]}")

    print("\n  事件日志:")
    for log in mixer.event_log:
        print(f"    {log}")
    print()


def demo_mixer_simulation():
    """综合混音模拟"""
    print("═══ 4. 实时混音模拟 ═══")

    mixer = AudioMixer(max_voices=4)

    # 预设场景：战斗音效 + 背景音乐
    scene = [
        (0.0, AudioClip("bgm_battle", AudioPriority.LOW, 0.5, 0.0, 6.0, fade_in=1.0, fade_out=1.0)),
        (0.5, AudioClip("sword_hit", AudioPriority.HIGH, 0.8, -0.5, 0.4, fade_in=0.05, fade_out=0.1)),
        (1.0, AudioClip("shield_block", AudioPriority.HIGH, 0.7, 0.5, 0.3, fade_in=0.02, fade_out=0.1)),
        (1.5, AudioClip("sword_hit", AudioPriority.HIGH, 0.8, 0.3, 0.4, fade_in=0.05, fade_out=0.1)),
        (2.0, AudioClip("victory", AudioPriority.CRITICAL, 1.0, 0.0, 2.0, fade_in=0.2, fade_out=1.0)),
        (2.5, AudioClip("footstep", AudioPriority.MEDIUM, 0.4, -0.2, 0.8)),
    ]

    dt = 0.1
    total_time = 6.0
    steps = int(total_time / dt)

    for step in range(steps):
        t = step * dt

        # 触发场景事件
        for trigger_time, clip in scene:
            if abs(t - trigger_time) < dt * 0.6:
                mixer.play(clip)

        output = mixer.update(dt)

        if step % 8 == 0:
            print(f"\n  ═══ t={t:.1f}s ═══")
            print(mixer.visualize(output, width=35))

    print(f"\n  事件日志({len(mixer.event_log)} 条):")
    for log in mixer.event_log[-10:]:
        print(f"    {log}")
    print()


def main():
    print("=" * 60)
    print("  音频混音器模拟 — 音量/Pan/淡入淡出/优先级队列")
    print("=" * 60)
    print()

    demo_volume_pan()
    demo_fade()
    demo_priority()
    demo_mixer_simulation()

    print("=" * 60)
    print("  演示完成！")
    print("  核心：Pan等功率分配 → 线性/指数淡入淡出 → 优先级抢占")
    print("=" * 60)


if __name__ == "__main__":
    main()
