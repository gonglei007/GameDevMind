# 工具脚本使用说明

本目录包含用于处理文档和生成输出的各种工具脚本。

## 📋 目录

- [脚本列表](#脚本列表)
- [环境要求](#环境要求)
- [使用方法](#使用方法)
- [常见问题](#常见问题)

## 📝 脚本列表

### 文档合并脚本

#### `merge2one.sh`
将所有 Markdown 文档合并为一个文件。

**用法**：
```bash
./merge2one.sh
```

#### `mergeByGroup.sh`
按组合并文档。

**用法**：
```bash
./mergeByGroup.sh
```

#### `merge-overview.sh`
合并总览图片。

**用法**：
```bash
./merge-overview.sh
```

#### `groups/mergeGroup*.sh`
按特定组合并文档（共6组，对应6大能力模块）。

**用法**：
```bash
./groups/mergeGroup1.sh  # 基础能力
./groups/mergeGroup2.sh  # 技术能力
# ... 以此类推
```

### PDF 生成脚本

#### `markdown2pdf.sh`
将 Markdown 文档转换为 PDF。

**用法**：
```bash
./markdown2pdf.sh
```

#### `createPDFs.sh`
批量创建 PDF 文档。

**用法**：
```bash
./createPDFs.sh
```

#### `books/images2pdf*.sh`
将图片转换为 PDF（共6个脚本，对应6大能力模块）。

**用法**：
```bash
./books/images2pdf1.sh  # 基础能力
./books/images2pdf2.sh  # 技术能力
# ... 以此类推
```

### 测试脚本

#### `test.sh`
运行测试脚本。

**用法**：
```bash
./test.sh
```

## 🔧 环境要求

### Linux/macOS

- Bash shell
- 基本的 Unix 工具（`find`, `cat`, `sed` 等）
- （可选）PDF 生成工具（如 `pandoc`、`wkhtmltopdf`）

### Windows

**注意**：当前脚本为 Shell 脚本，Windows 用户需要使用以下方式之一：

1. **Git Bash**（推荐）
   - 安装 Git for Windows
   - 使用 Git Bash 运行脚本

2. **WSL**（Windows Subsystem for Linux）
   - 安装 WSL
   - 在 WSL 环境中运行脚本

3. **PowerShell 版本**（计划中）
   - 未来将提供 PowerShell 版本的脚本

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

3. **赋予执行权限**（Linux/macOS）
   ```bash
   chmod +x *.sh
   chmod +x groups/*.sh
   chmod +x books/*.sh
   ```

4. **运行脚本**
   ```bash
   ./脚本名.sh
   ```

### 示例：合并所有文档

```bash
# 合并所有文档为一个文件
./merge2one.sh

# 输出文件通常在上级目录或指定目录
```

### 示例：生成 PDF

```bash
# 生成单个 PDF
./markdown2pdf.sh input.md output.pdf

# 批量生成 PDF
./createPDFs.sh
```

## ⚠️ 注意事项

1. **路径问题**
   - 脚本使用相对路径，请确保在正确的目录中运行
   - 某些脚本可能需要从项目根目录运行

2. **权限问题**
   - Linux/macOS 需要执行权限
   - Windows 用户使用 Git Bash 时通常不需要额外权限

3. **依赖工具**
   - PDF 生成需要安装相应工具（如 `pandoc`）
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

### Q: PDF 生成失败

**A**: 
- 检查是否安装了 PDF 生成工具
- 检查输入文件是否存在
- 查看错误信息

## 🔮 未来计划

- [ ] 添加 PowerShell 版本的脚本
- [ ] 添加 Node.js 版本的脚本（跨平台）
- [ ] 添加配置文件支持
- [ ] 添加更详细的错误处理
- [ ] 添加进度显示
- [ ] 添加单元测试

## 📚 相关资源

- [Bash 脚本教程](https://www.gnu.org/software/bash/manual/)
- [Markdown 转 PDF 工具](https://pandoc.org/)
- [Git Bash 下载](https://git-scm.com/downloads)

## 🤝 贡献

如果您想改进这些工具脚本，请：

1. Fork 仓库
2. 创建特性分支
3. 提交更改
4. 创建 Pull Request

更多信息请查看 [CONTRIBUTING.md](../CONTRIBUTING.md)。

---

*最后更新：2024年*

