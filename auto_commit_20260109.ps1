param(
    [string]$Message = "auto commit"
)

# 仓库路径
$repo = "D:\wjw_work"
# 固定使用的分支
$targetBranch = "2026-01-09-n7o0"
# 你的本地代理
$proxy = "http://127.0.0.1:7897"

Set-Location $repo

# 确保在目标分支上（不存在则报错提示）
$currentBranch = git branch --show-current
if ($currentBranch -ne $targetBranch) {
    Write-Host "当前分支是 $currentBranch ，切换到 $targetBranch ..."
    git checkout $targetBranch
    if ($LASTEXITCODE -ne 0) {
        Write-Host "切换到分支 $targetBranch 失败，请先在命令行手动检查分支状态。"
        exit 1
    }
}

# 暂存所有改动
git add -A

# 如果没有暂存改动就直接退出
$changes = git diff --cached --name-only
if (-not $changes) {
    Write-Host "没有需要提交的改动。"
    exit 0
}

# 自动生成提交信息（带时间）
$time = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$fullMsg = "$Message ($time)"

Write-Host "提交信息: $fullMsg"
git commit -m "$fullMsg"
if ($LASTEXITCODE -ne 0) {
    Write-Host "git commit 失败，请检查输出。"
    exit 1
}

# 通过本地代理推送到远程分支
Write-Host "推送到 origin/$targetBranch ..."
git -c http.proxy=$proxy -c https.proxy=$proxy push origin $targetBranch
if ($LASTEXITCODE -ne 0) {
    Write-Host "git push 失败，请检查网络/鉴权。"
    exit 1
}

Write-Host "✅ 已自动提交并推送到 origin/$targetBranch"