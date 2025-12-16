# 工具脚本使用说明

本目录包含用于处理文档和生成输出的各种工具脚本。

## 📋 目录结构

```
tools/
├── merge/              # 文档合并脚本
│   ├── merge2one.sh
│   ├── mergeByGroup.sh
│   ├── merge-overview.sh
│   └── groups/        # 按组合并脚本
│       └── mergeGroup*.sh
├── pdf/               # PDF 生成脚本
│   ├── markdown2pdf.sh
│   ├── createPDFs.sh
│   └── books/         # 图片转PDF脚本
│       └── images2pdf*.sh
├── xmind/             # XMind 转换脚本
│   ├── xmind2md.sh
│   ├── xmind2md.ps1
│   └── xmind2md.py
├── smart/             # Smart API 脚本
│   ├── smart-agent-batch.js
│   ├── smart-agent-config.example.json
│   └── package.json
├── test.sh            # 测试脚本
└── README.md          # 本文件
```

## 📝 脚本列表

### 文档合并脚本 (`merge/`)

#### `merge/merge2one.sh`
将所有 Markdown 文档合并为一个文件。

**用法**：
```bash
cd tools/merge
./merge2one.sh
```

#### `merge/mergeByGroup.sh`
按组合并文档。

**用法**：
```bash
cd tools/merge
./mergeByGroup.sh
```

#### `merge/merge-overview.sh`
合并总览图片。

**用法**：
```bash
cd tools/merge
./merge-overview.sh
```

#### `merge/groups/mergeGroup*.sh`
按特定组合并文档（共6组，对应6大能力模块）。

**用法**：
```bash
cd tools/merge/groups
./mergeGroup1.sh  # 基础能力
./mergeGroup2.sh  # 技术能力
# ... 以此类推
```

### PDF 生成脚本 (`pdf/`)

#### `pdf/markdown2pdf.sh`
将 Markdown 文档转换为 PDF。

**用法**：
```bash
cd tools/pdf
./markdown2pdf.sh
```

#### `pdf/createPDFs.sh`
批量创建 PDF 文档。

**用法**：
```bash
cd tools/pdf
./createPDFs.sh
```

#### `pdf/books/images2pdf*.sh`
将图片转换为 PDF（共6个脚本，对应6大能力模块）。

**用法**：
```bash
cd tools/pdf/books
./images2pdf1.sh  # 基础能力
./images2pdf2.sh  # 技术能力
# ... 以此类推
```

### XMind 转换脚本 (`xmind/`)

#### `xmind/xmind2md.sh` (macOS/Linux) 和 `xmind/xmind2md.ps1` (Windows)
将 `xminds` 目录下的所有 XMind 文件批量导出为同名的 Markdown 文件到 `mds` 目录。

**环境要求**：
- Python 3.7 或更高版本
- （推荐）xmindparser 库：`pip install xmindparser`

**用法**：

**macOS/Linux**：
```bash
cd tools/xmind
./xmind2md.sh
```

**Windows**：
```powershell
cd tools/xmind
.\xmind2md.ps1
```

**功能**：
- 自动遍历 `xminds` 目录下的所有 `.xmind` 文件
- 保持目录结构，将导出的 `.md` 文件放到对应的 `mds` 目录
- 自动安装 xmindparser 库（如果未安装）
- 显示转换进度和统计信息

**注意事项**：
- 如果未安装 xmindparser，脚本会尝试使用基本的 XML 解析器，但效果可能不如 xmindparser
- 建议先安装 xmindparser：`pip install xmindparser`

### Smart API 批量执行脚本 (`smart/`)

#### `smart/smart-agent-batch.js`
通过 Smart API 批量执行 agent，提示词中可以引用文件。

**环境要求**：
- Node.js 14.0 或更高版本

**配置**：
1. 设置环境变量 `SMART_API_KEY`，或编辑 `smart/smart-agent-config.json` 配置文件
2. 编辑 `smart/smart-agent-config.json` 配置文件，添加要执行的任务

**用法**：
```bash
# 设置 API Key（推荐）
export SMART_API_KEY="your-api-key-here"

# 运行脚本
cd tools/smart
node smart-agent-batch.js

# 或使用 npm
npm run smart-agent
```

**配置文件格式**：
```json
{
  "apiKey": "your-api-key",
  "apiUrl": "https://api.smart.sh/v1/chat/completions",
  "model": "gpt-4",
  "tasks": [
    {
      "id": "task-1",
      "prompt": "基于 @INTRODUCTION.md 的内容...",
      "files": [
        "INTRODUCTION.md",
        "xminds/1.基础能力/1.1.1.编程语言基础概念.md"
      ],
      "outputFile": "output/task-1-result.md"
    }
  ]
}
```

**功能**：
- 批量执行多个 agent 任务
- 在提示词中自动引用文件内容
- 自动重试失败的请求
- 生成执行报告
- 支持任务间延迟控制

**注意事项**：
- 需要有效的 Smart API Key
- 文件路径相对于项目根目录
- 输出文件会保存到指定位置或默认输出目录

### 测试脚本

#### `test.sh`
运行测试脚本。

**用法**：
```bash
cd tools
./test.sh
```

## 🔧 环境要求

### Linux/macOS

- Bash shell
- 基本的 Unix 工具（`find`, `cat`, `sed` 等）
- （可选）PDF 生成工具（如 `pandoc`、`wkhtmltopdf`）
- **XMind 转换脚本**：Python 3.7+，推荐安装 xmindparser 库
- **Smart API 脚本**：Node.js 14.0+

### Windows

**注意**：当前大部分脚本为 Shell 脚本，Windows 用户需要使用以下方式之一：

1. **Git Bash**（推荐）
   - 安装 Git for Windows
   - 使用 Git Bash 运行 `.sh` 脚本

2. **WSL**（Windows Subsystem for Linux）
   - 安装 WSL
   - 在 WSL 环境中运行脚本

3. **PowerShell 脚本**
   - `xmind/xmind2md.ps1` 可以直接在 PowerShell 中运行
   - 需要 Python 3.7+ 环境

## 📖 使用方法

### 基本步骤

1. **克隆仓库**
   ```bash
   git clone https://github.com/gonglei007/GameDevMind.git
   cd GameDevMind
   ```

2. **进入工具目录**
   ```bash
   cd tools
   ```

3. **进入对应的工具子目录**
   ```bash
   cd merge    # 文档合并
   cd pdf      # PDF 生成
   cd xmind    # XMind 转换
   cd smart    # Smart API
   ```

4. **赋予执行权限**（Linux/macOS）
   ```bash
   chmod +x *.sh
   chmod +x groups/*.sh
   chmod +x books/*.sh
   ```

5. **运行脚本**
   ```bash
   ./脚本名.sh
   ```

### 示例：合并所有文档

```bash
# 合并所有文档为一个文件
cd tools/merge
./merge2one.sh

# 输出文件通常在上级目录或指定目录
```

### 示例：生成 PDF

```bash
# 生成单个 PDF
cd tools/pdf
./markdown2pdf.sh input.md output.pdf

# 批量生成 PDF
./createPDFs.sh
```

### 示例：XMind 转 Markdown

```bash
# macOS/Linux
cd tools/xmind
./xmind2md.sh

# Windows (PowerShell)
cd tools/xmind
.\xmind2md.ps1
```

### 示例：Smart API 批量执行

```bash
# 设置 API Key
export SMART_API_KEY="your-api-key-here"

# 运行脚本
cd tools/smart
node smart-agent-batch.js
```

## ⚠️ 注意事项

1. **路径问题**
   - 脚本使用相对路径，请确保在正确的目录中运行
   - 某些脚本可能需要从项目根目录运行
   - 合并和PDF脚本中的路径是相对于项目根目录的

2. **权限问题**
   - Linux/macOS 需要执行权限
   - Windows 用户使用 Git Bash 时通常不需要额外权限

3. **依赖工具**
   - PDF 生成需要安装相应工具（如 `pandoc`）
   - XMind 转换需要 Python 3.7+，推荐安装 xmindparser：`pip install xmindparser`
   - Smart API 需要 Node.js 14.0+
   - 检查脚本中的依赖要求

4. **输出位置**
   - 不同脚本的输出位置可能不同
   - 查看脚本内容或注释了解输出位置

## 🐛 常见问题

### Q: 脚本无法执行

**A**: 
- Linux/macOS：检查文件权限，使用 `chmod +x 脚本名.sh`
- Windows：使用 Git Bash 或 WSL

### Q: 找不到命令

**A**: 
- 检查是否安装了所需的依赖工具
- 检查 PATH 环境变量

### Q: 路径错误

**A**: 
- 确保在正确的目录中运行脚本
- 检查脚本中的路径设置
- 合并和PDF脚本的路径是相对于项目根目录的

### Q: PDF 生成失败

**A**: 
- 检查是否安装了 PDF 生成工具
- 检查输入文件是否存在
- 查看错误信息

### Q: XMind 转换失败

**A**: 
- 检查是否安装了 Python 3.7+
- 检查 Python 是否在 PATH 中
- 尝试手动安装 xmindparser：`pip install xmindparser`
- 检查 xminds 目录是否存在
- 查看错误信息

### Q: Smart API 调用失败

**A**: 
- 检查 API Key 是否正确设置
- 检查网络连接
- 查看错误信息和执行报告

## 🔮 未来计划

- [x] 添加 PowerShell 版本的脚本（XMind 转换）
- [x] 添加 Node.js 版本的脚本（跨平台 - Smart API）
- [x] 添加配置文件支持（Smart API 脚本）
- [x] 添加更详细的错误处理（Smart API 脚本）
- [x] 添加进度显示（XMind 转换、Smart API 脚本）
- [x] 整理工具目录结构
- [ ] 添加单元测试
- [ ] 添加包装脚本，支持从项目根目录运行

## 📚 相关资源

- [Bash 脚本教程](https://www.gnu.org/software/bash/manual/)
- [Markdown 转 PDF 工具](https://pandoc.org/)
- [Git Bash 下载](https://git-scm.com/downloads)
- [Node.js 下载](https://nodejs.org/)

## 🤝 贡献

如果您想改进这些工具脚本，请：

1. Fork 仓库
2. 创建特性分支
3. 提交更改
4. 创建 Pull Request

更多信息请查看 [CONTRIBUTING.md](../CONTRIBUTING.md)。

---

*最后更新：2024年*
