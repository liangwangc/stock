@echo off
setlocal

rem 仓库路径、分支、代理
set REPO=D:\wjw_work
set BRANCH=2026-01-09-n7o0
set PROXY=http://127.0.0.1:7897

cd /d "%REPO%"

rem 确保在目标分支上
git branch --show-current > curbranch.tmp
set /p CURBR=<curbranch.tmp
del curbranch.tmp 2>nul

if /I not "%CURBR%"=="%BRANCH%" (
  echo 当前分支是 %CURBR%，切换到 %BRANCH% ...
  git checkout %BRANCH%
  if errorlevel 1 goto :eof
)

rem 暂存所有改动
git add -A

rem 如果没有暂存改动就直接退出
git diff --cached --quiet
if %ERRORLEVEL%==0 (
  echo 没有需要提交的改动。
  goto :eof
)

rem 提交信息：用命令行参数，没传就用默认
set MSG=%*
if "%MSG%"=="" set MSG=auto commit

echo 提交信息: %MSG%
git commit -m "%MSG%"
if errorlevel 1 goto :eof

echo 推送到 origin/%BRANCH% ...
git -c http.proxy=%PROXY% -c https.proxy=%PROXY% push origin %BRANCH%

endlocal