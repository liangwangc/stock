# 单词库导入测试 - PowerShell脚本
# 自动查找PHP并运行测试

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "单词库导入测试工具" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$phpPath = $null

# 检查系统PATH
Write-Host "[1/5] 检查系统PATH..." -ForegroundColor Yellow
try {
    $phpCheck = Get-Command php -ErrorAction Stop
    $phpPath = "php"
    Write-Host "  [OK] 找到 PHP（系统PATH中）" -ForegroundColor Green
    Write-Host "  路径: $($phpCheck.Source)" -ForegroundColor Gray
} catch {
    Write-Host "  [X] 未在PATH中找到" -ForegroundColor Red
}

# 检查XAMPP
if (-not $phpPath) {
    Write-Host "[2/5] 检查XAMPP..." -ForegroundColor Yellow
    $xamppPaths = @(
        "C:\xampp\php\php.exe",
        "C:\xampp64\php\php.exe",
        "D:\xampp\php\php.exe"
    )
    
    foreach ($path in $xamppPaths) {
        if (Test-Path $path) {
            $phpPath = $path
            Write-Host "  [OK] 找到 XAMPP PHP" -ForegroundColor Green
            Write-Host "  路径: $path" -ForegroundColor Gray
            break
        }
    }
    
    if (-not $phpPath) {
        Write-Host "  [X] 未找到XAMPP" -ForegroundColor Red
    }
}

# 检查WAMP
if (-not $phpPath) {
    Write-Host "[3/5] 检查WAMP..." -ForegroundColor Yellow
    $wampBase = "C:\wamp64\bin\php"
    if (Test-Path $wampBase) {
        $phpDirs = Get-ChildItem -Path $wampBase -Directory | Where-Object { $_.Name -like "php*" }
        foreach ($dir in $phpDirs) {
            $phpExe = Join-Path $dir.FullName "php.exe"
            if (Test-Path $phpExe) {
                $phpPath = $phpExe
                Write-Host "  [OK] 找到 WAMP PHP" -ForegroundColor Green
                Write-Host "  路径: $phpExe" -ForegroundColor Gray
                break
            }
        }
    }
    
    if (-not $phpPath) {
        Write-Host "  [X] 未找到WAMP" -ForegroundColor Red
    }
}

# 检查其他常见位置
if (-not $phpPath) {
    Write-Host "[4/5] 检查其他位置..." -ForegroundColor Yellow
    $otherPaths = @(
        "C:\php\php.exe",
        "D:\php\php.exe"
    )
    
    foreach ($path in $otherPaths) {
        if (Test-Path $path) {
            $phpPath = $path
            Write-Host "  [OK] 找到 PHP" -ForegroundColor Green
            Write-Host "  路径: $path" -ForegroundColor Gray
            break
        }
    }
    
    if (-not $phpPath) {
        Write-Host "  [X] 未找到" -ForegroundColor Red
    }
}

# 如果还是没找到，提示用户
if (-not $phpPath) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "未找到 PHP" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "请选择以下方案之一：" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "1. 安装 XAMPP（推荐）" -ForegroundColor Cyan
    Write-Host "   下载: https://www.apachefriends.org/" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. 安装 WAMP" -ForegroundColor Cyan
    Write-Host "   下载: https://www.wampserver.com/" -ForegroundColor Gray
    Write-Host ""
    Write-Host "3. 手动指定PHP路径" -ForegroundColor Cyan
    Write-Host "   编辑此脚本，在最后添加：" -ForegroundColor Gray
    Write-Host "   `$phpPath = '你的PHP路径'" -ForegroundColor Gray
    Write-Host ""
    Read-Host "按回车键退出"
    exit 1
}

# 运行测试
Write-Host "[5/5] 运行测试脚本..." -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$scriptPath = Join-Path $PSScriptRoot "test_import.php"

if (-not (Test-Path $scriptPath)) {
    Write-Host "错误: 找不到 test_import.php" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}

Write-Host "执行命令: $phpPath $scriptPath" -ForegroundColor Gray
Write-Host ""

# 运行PHP脚本
& $phpPath $scriptPath

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "测试完成！" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Read-Host "按回车键退出"
