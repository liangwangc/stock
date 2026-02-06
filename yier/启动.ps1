# PowerShell启动脚本
# 启动项目服务器

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "启动项目服务器" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$phpPath = $null

# 检查XAMPP
if (Test-Path "C:\xampp\php\php.exe") {
    $phpPath = "C:\xampp\php\php.exe"
    Write-Host "找到 PHP: $phpPath" -ForegroundColor Green
}
elseif (Test-Path "C:\xampp64\php\php.exe") {
    $phpPath = "C:\xampp64\php\php.exe"
    Write-Host "找到 PHP: $phpPath" -ForegroundColor Green
}
# 检查系统PATH
elseif (Get-Command php -ErrorAction SilentlyContinue) {
    $phpPath = "php"
    Write-Host "找到 PHP（系统PATH中）" -ForegroundColor Green
}

if ($phpPath) {
    Write-Host ""
    Write-Host "正在启动服务器..." -ForegroundColor Yellow
    Write-Host "访问地址: http://localhost:8000" -ForegroundColor Yellow
    Write-Host "按 Ctrl+C 停止服务器" -ForegroundColor Yellow
    Write-Host ""
    
    Set-Location $PSScriptRoot
    & $phpPath -S localhost:8000
}
else {
    Write-Host "错误: 未找到 PHP！" -ForegroundColor Red
    Write-Host ""
    Write-Host "请先安装 XAMPP:" -ForegroundColor Yellow
    Write-Host "  下载地址: https://www.apachefriends.org/" -ForegroundColor Yellow
    Write-Host "  安装到: C:\xampp\" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "按回车键退出"
}
