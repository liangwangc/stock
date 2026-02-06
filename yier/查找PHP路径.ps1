# 查找PHP路径工具
# 帮助用户找到系统中安装的PHP

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PHP路径查找工具" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$foundPhp = @()

# 检查系统PATH
Write-Host "[检查1] 系统PATH..." -ForegroundColor Yellow
try {
    $phpCheck = Get-Command php -ErrorAction Stop
    $foundPhp += @{
        Name = "系统PATH"
        Path = $phpCheck.Source
        Command = "php"
    }
    Write-Host "  ✓ 找到: $($phpCheck.Source)" -ForegroundColor Green
} catch {
    Write-Host "  ✗ 未找到" -ForegroundColor Red
}

# 检查XAMPP
Write-Host "[检查2] XAMPP..." -ForegroundColor Yellow
$xamppPaths = @(
    @{Name="XAMPP"; Path="C:\xampp\php\php.exe"},
    @{Name="XAMPP64"; Path="C:\xampp64\php\php.exe"},
    @{Name="XAMPP (D盘)"; Path="D:\xampp\php\php.exe"}
)

foreach ($xampp in $xamppPaths) {
    if (Test-Path $xampp.Path) {
        $foundPhp += @{
            Name = $xampp.Name
            Path = $xampp.Path
            Command = "`"$($xampp.Path)`""
        }
        Write-Host "  ✓ 找到 $($xampp.Name): $($xampp.Path)" -ForegroundColor Green
    }
}

# 检查WAMP
Write-Host "[检查3] WAMP..." -ForegroundColor Yellow
$wampBase = "C:\wamp64\bin\php"
if (Test-Path $wampBase) {
    $phpDirs = Get-ChildItem -Path $wampBase -Directory | Where-Object { $_.Name -like "php*" }
    foreach ($dir in $phpDirs) {
        $phpExe = Join-Path $dir.FullName "php.exe"
        if (Test-Path $phpExe) {
            $foundPhp += @{
                Name = "WAMP ($($dir.Name))"
                Path = $phpExe
                Command = "`"$phpExe`""
            }
            Write-Host "  ✓ 找到: $phpExe" -ForegroundColor Green
        }
    }
} else {
    Write-Host "  ✗ 未找到WAMP" -ForegroundColor Red
}

# 检查其他位置
Write-Host "[检查4] 其他位置..." -ForegroundColor Yellow
$otherPaths = @(
    "C:\php\php.exe",
    "D:\php\php.exe"
)

foreach ($path in $otherPaths) {
    if (Test-Path $path) {
        $foundPhp += @{
            Name = "独立安装"
            Path = $path
            Command = "`"$path`""
        }
        Write-Host "  ✓ 找到: $path" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "查找结果" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($foundPhp.Count -eq 0) {
    Write-Host "未找到任何PHP安装！" -ForegroundColor Red
    Write-Host ""
    Write-Host "建议安装XAMPP:" -ForegroundColor Yellow
    Write-Host "  https://www.apachefriends.org/" -ForegroundColor Cyan
} else {
    Write-Host "找到 $($foundPhp.Count) 个PHP安装：" -ForegroundColor Green
    Write-Host ""
    
    for ($i = 0; $i -lt $foundPhp.Count; $i++) {
        $php = $foundPhp[$i]
        Write-Host "[$($i+1)] $($php.Name)" -ForegroundColor Cyan
        Write-Host "    路径: $($php.Path)" -ForegroundColor Gray
        Write-Host "    命令: $($php.Command)" -ForegroundColor Gray
        Write-Host ""
    }
    
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "使用示例：" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "运行测试导入：" -ForegroundColor Cyan
    Write-Host "  $($foundPhp[0].Command) test_import.php" -ForegroundColor White
    Write-Host ""
    Write-Host "运行完整导入：" -ForegroundColor Cyan
    Write-Host "  $($foundPhp[0].Command) import_word_bank.php" -ForegroundColor White
    Write-Host ""
}

Write-Host "========================================" -ForegroundColor Cyan
Read-Host "按回车键退出"
