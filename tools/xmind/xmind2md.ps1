# XMind to Markdown Converter Script for Windows
# 将 xminds 目录下的所有 XMind 文件导出为同名的 Markdown 文件

# 设置错误处理
$ErrorActionPreference = "Stop"

# 颜色输出函数
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

# 获取脚本所在目录
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$XmindDir = Join-Path $ProjectRoot "xminds"
$MdsDir = Join-Path $ProjectRoot "mds"
$PythonScript = Join-Path $ScriptDir "xmind2md.py"

# 检查 Python 是否安装
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Python not found"
    }
    Write-ColorOutput Green "Found: $pythonVersion"
} catch {
    Write-ColorOutput Red "Error: Python is not installed or not in PATH."
    Write-Output "Please install Python 3.7 or higher and add it to PATH."
    exit 1
}

# 检查 Python 脚本是否存在
if (-not (Test-Path $PythonScript)) {
    Write-ColorOutput Red "Error: Python script not found: $PythonScript"
    exit 1
}

# 检查 xminds 目录是否存在
if (-not (Test-Path $XmindDir)) {
    Write-ColorOutput Red "Error: xminds directory not found: $XmindDir"
    exit 1
}

# 检查并安装 xmindparser（可选，但推荐）
Write-ColorOutput Yellow "Checking for xmindparser library..."
try {
    python -c "import xmindparser" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput Green "xmindparser is already installed."
    } else {
        throw "xmindparser not found"
    }
} catch {
    Write-ColorOutput Yellow "xmindparser not found. Installing..."
    python -m pip install xmindparser --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput Green "xmindparser installed successfully."
    } else {
        Write-ColorOutput Yellow "Warning: Failed to install xmindparser. Will use basic XML parser."
        Write-ColorOutput Yellow "For better results, install manually: pip install xmindparser"
    }
}

# 统计变量
$total = 0
$success = 0
$failed = 0

# 函数：转换单个文件
function Convert-File {
    param (
        [string]$XmindFile
    )
    
    $relativePath = $XmindFile.Replace($XmindDir + "\", "").Replace($XmindDir + "/", "")
    $mdFileName = [System.IO.Path]::ChangeExtension($relativePath, ".md")
    $mdFile = Join-Path $MdsDir $mdFileName
    $mdDir = Split-Path -Parent $mdFile
    
    # 创建输出目录
    if (-not (Test-Path $mdDir)) {
        New-Item -ItemType Directory -Path $mdDir -Force | Out-Null
    }
    
    # 转换文件
    try {
        python $PythonScript $XmindFile $mdFile
        if ($LASTEXITCODE -eq 0) {
            $script:success++
            return $true
        } else {
            throw "Conversion failed"
        }
    } catch {
        $script:failed++
        Write-ColorOutput Red "Failed to convert: $XmindFile"
        return $false
    }
}

# 主处理逻辑
Write-ColorOutput Green "Starting XMind to Markdown conversion..."
Write-Output "Source directory: $XmindDir"
Write-Output "Output directory: $MdsDir"
Write-Output ""

# 查找所有 .xmind 文件并处理
$xmindFiles = Get-ChildItem -Path $XmindDir -Filter "*.xmind" -Recurse -File

foreach ($xmindFile in $xmindFiles) {
    $total++
    $relativePath = $xmindFile.FullName.Replace($ProjectRoot + "\", "").Replace($ProjectRoot + "/", "")
    Write-ColorOutput Yellow "[$total] Processing: $relativePath"
    Convert-File -XmindFile $xmindFile.FullName
}

# 输出统计信息
Write-Output ""
Write-ColorOutput Green "========================================"
Write-ColorOutput Green "Conversion completed!"
Write-Output "Total files: $total"
Write-ColorOutput Green "Successful: $success"
if ($failed -gt 0) {
    Write-ColorOutput Red "Failed: $failed"
}
Write-ColorOutput Green "========================================"

# 返回退出码
if ($failed -eq 0) {
    exit 0
} else {
    exit 1
}

