#!/usr/bin/env bash
# XMind to Markdown Converter Script for macOS/Linux
# 将 xminds 目录下的所有 XMind 文件导出为同名的 Markdown 文件

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
XMIND_DIR="$PROJECT_ROOT/xminds"
MDS_DIR="$PROJECT_ROOT/mds"
PYTHON_SCRIPT="$SCRIPT_DIR/xmind2md.py"

# 检查 Python 是否安装
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 is not installed.${NC}"
    echo "Please install Python 3.7 or higher."
    exit 1
fi

# 检查 Python 脚本是否存在
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo -e "${RED}Error: Python script not found: $PYTHON_SCRIPT${NC}"
    exit 1
fi

# 检查 xminds 目录是否存在
if [ ! -d "$XMIND_DIR" ]; then
    echo -e "${RED}Error: xminds directory not found: $XMIND_DIR${NC}"
    exit 1
fi

# 检查并安装 xmindparser（可选，但推荐）
echo -e "${YELLOW}Checking for xmindparser library...${NC}"
if ! python3 -c "import xmindparser" 2>/dev/null; then
    echo -e "${YELLOW}xmindparser not found. Installing...${NC}"
    if python3 -m pip install xmindparser --quiet; then
        echo -e "${GREEN}xmindparser installed successfully.${NC}"
    else
        echo -e "${YELLOW}Warning: Failed to install xmindparser. Will use basic XML parser.${NC}"
        echo -e "${YELLOW}For better results, install manually: pip install xmindparser${NC}"
    fi
else
    echo -e "${GREEN}xmindparser is already installed.${NC}"
fi

# 统计变量
total=0
success=0
failed=0

# 函数：转换单个文件
convert_file() {
    local xmind_file="$1"
    local relative_path="${xmind_file#$XMIND_DIR/}"
    local md_file="$MDS_DIR/${relative_path%.xmind}.md"
    local md_dir="$(dirname "$md_file")"
    
    # 创建输出目录
    mkdir -p "$md_dir"
    
    # 转换文件
    if python3 "$PYTHON_SCRIPT" "$xmind_file" "$md_file"; then
        ((success++))
        return 0
    else
        ((failed++))
        echo -e "${RED}Failed to convert: $xmind_file${NC}"
        return 1
    fi
}

# 主处理逻辑
echo -e "${GREEN}Starting XMind to Markdown conversion...${NC}"
echo "Source directory: $XMIND_DIR"
echo "Output directory: $MDS_DIR"
echo ""

# 查找所有 .xmind 文件并处理
while IFS= read -r -d '' xmind_file; do
    ((total++))
    echo -e "${YELLOW}[$total] Processing: ${xmind_file#$PROJECT_ROOT/}${NC}"
    convert_file "$xmind_file"
done < <(find "$XMIND_DIR" -type f -name "*.xmind" -print0)

# 输出统计信息
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Conversion completed!${NC}"
echo -e "Total files: $total"
echo -e "${GREEN}Successful: $success${NC}"
if [ $failed -gt 0 ]; then
    echo -e "${RED}Failed: $failed${NC}"
fi
echo -e "${GREEN}========================================${NC}"

# 返回退出码
if [ $failed -eq 0 ]; then
    exit 0
else
    exit 1
fi

