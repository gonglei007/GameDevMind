# Excel → JSON 策划表导出

演示手游常见的 **Excel 三行表头 + JSON 导出** 流水线，可直接接入 CI 或编辑器一键导出。

对应文档：[游戏数据文件](../../../../mds/4.生产能力/4.2.3.游戏数据文件.md)

## 快速运行

```bash
cd excel_to_json
pip install -r requirements.txt
python create_sample.py    # 生成 sample/hero_config.xlsx
python excel_to_json.py    # 导出 output/hero_config.json
```

## Excel 表头约定

| 行 | 内容 |
|----|------|
| 1 | 字段名（JSON key） |
| 2 | 类型：`int` / `float` / `string` / `bool` |
| 3 | 中文注释（导出忽略） |
| 4+ | 数据行 |

## 输出格式

默认导出为 `{ "1001": { ... }, "1002": { ... } }` 字典，便于客户端按 id 查找。

## 生产环境扩展

- 多 Sheet → 多 JSON 文件
- 导出前跑校验（唯一 id、外键引用）
- 接入 Git diff 做策划表变更 review
