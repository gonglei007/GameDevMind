## 编辑器开发 — 配套代码

对应文章：四-03-关卡编辑器、剧情编辑器怎么开发？

### 文章章节与示例

| 章节 | 正文骨架类 | 完整实现要点 |
|------|-----------|-------------|
| 关卡编辑器 | `LevelEditor` | 场景视图取点、Prefab 实例化、网格吸附、Undo、触发区域创建 |
| 触发器系统 | `TriggerZone` / `TriggerZoneEditor` | 条件/动作列表编辑、Inspector 自定义绘制 |
| 剧情编辑器 | `StoryNode` / `StoryGraphView` | GraphView 节点画布、端口连线、分支数据结构 |
| 配置表编辑器 | `ConfigTableEditor` | Excel 导入导出、表头/行编辑、数据验证与保存 |
| 自定义工具 | `BatchImportTool` / `AutoBuildTool` | 资源批量导入、版本号更新、AB 打包与上传 |

### 可运行示例

| 示例 | 文件 | 说明 |
|------|------|------|
| 编辑器工具集 | `editor_tool.py` | 批量重命名、资源依赖图、使用统计（纯 Python 标准库） |

### 运行

```bash
python3 editor_tool.py
```
