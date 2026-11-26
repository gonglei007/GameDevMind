# Unity 暂停与恢复小场景

整理补充。这个可运行的单机示例对应[暂停功能验收](../../03.开发与迭代流程.md#示例-验收暂停功能)。它用巡逻标记、弹体、游戏计时和菜单计时展示暂停边界。

## 在编辑器中运行

1. 将本目录复制到练习目录，用 Unity Hub 添加该副本并以 Unity `6000.3.13f1` 打开。
2. 在 Project 面板打开 [PauseDemo 场景](Assets/PauseDemo.unity)，点击 Play。Game 窗口显示 `Game`、`UI` 计时与 `Shots` 计数。
3. 点击 **Fire**，在弹体到达右端前点 **Pause**，再试一次 **Fire**。
4. 点 **Resume**，观察原有弹体继续飞行，再按一次 **Fire**。重复暂停和恢复两次，按下表逐项核对。
5. 暂停时点 **Restart round**，确认界面回到 Running，计数归零，游戏计时重新开始。这个按钮模拟回合状态重置。实际项目应另验从菜单退出并重新加载关卡。

## 暂停与恢复对照表

| 观察项 | 暂停时 | 恢复后 |
|---|---|---|
| 游戏计时 `Game` 与巡逻 | 计时停止，巡逻标记留在原处 | 计时与巡逻从暂停处继续 |
| 飞行中的弹体 | 位置保持 | 从暂停的位置继续飞行 |
| 菜单计时 `UI` | 继续计时，恢复和重开按钮可以操作 | 继续计时 |
| 射击次数 `Shots` | 点击 **Fire**，射击次数与弹体位置保持 | 点击一次 **Fire**，射击次数增加一次，弹体从起点出发 |

## 看代码时关注哪些边界

- **游戏时间**由 `Time.deltaTime` 推进。暂停时停止推进游戏时钟和弹体，并显式拒绝射击输入。
- **菜单时间**由 `Time.unscaledDeltaTime` 推进。暂停、恢复和重开按钮继续响应。
- **生命周期**保存暂停前的 `Time.timeScale`。恢复、重开和组件停用时还原原值，这样原先的慢动作倍率也能保留。

实现集中在 [PauseDemo.cs](Assets/PauseDemo.cs)。本场景只有一个时间倍率管理者。接入已有项目时，先核对谁管理时间状态，再为动画、音频、物理和联网等系统分别确定暂停规则。[Unity Time.timeScale](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Time-timeScale.html) · [Unity Time.unscaledDeltaTime](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Time-unscaledDeltaTime.html)

## Windows Player 自动检查

安装 Windows 构建支持，关闭练习副本的 Editor。从示例副本根目录运行下列命令。构建入口见 [PauseDemoBuild.cs](Assets/Editor/PauseDemoBuild.cs)。

```powershell
$editor = 'C:\Program Files\Unity\Hub\Editor\6000.3.13f1\Editor\Unity.exe'
$project = (Get-Location).Path
$build = Start-Process $editor -ArgumentList @(
    '-batchmode', '-nographics', '-quit', '-projectPath', ('"' + $project + '"'),
    '-executeMethod', 'PauseDemoBuild.BuildWindows', '-logFile', 'pause-build.log'
) -WorkingDirectory $project -WindowStyle Hidden -PassThru
if (!$build.WaitForExit(300000)) { throw 'Build timed out. See pause-build.log.' }
if ($build.ExitCode -ne 0) { throw 'Build failed. See pause-build.log.' }

$player = Start-Process "$project/Builds/PauseDemo.exe" -ArgumentList @(
    '-batchmode', '-nographics', '-pause-demo-check', '-logFile', 'pause-player.log'
) -WorkingDirectory $project -WindowStyle Hidden -PassThru
if (!$player.WaitForExit(45000)) {
    Stop-Process -Id $player.Id
    throw 'Pause check timed out. See pause-player.log.'
}
$checks = @(Select-String -LiteralPath 'pause-player.log' -Pattern 'PAUSE_DEMO PASS:')
$checks | ForEach-Object Line
if ($player.ExitCode -ne 0 -or $checks.Count -ne 6) { throw 'Pause check failed.' }
```

通过条件是退出码 0 和六条 `PAUSE_DEMO PASS`。自动检查直接调用与按钮相同的逻辑，验证两轮暂停与恢复、慢动作倍率、暂停中重开与停用清理。鼠标操作、界面显示和输入是否穿透，按上面的试玩步骤另行验收。

2026 年 11 月 26 日在 Windows 和 Unity `6000.3.13f1` 的独立工程副本中复核。Windows x64 Development Player 构建成功，无图形运行的六项断言全部通过，退出码为 0。
