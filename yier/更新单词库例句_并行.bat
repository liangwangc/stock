@echo off
chcp 65001 >nul
echo ========================================
echo 单词库例句更新工具（多进程并行版本）
echo ========================================
echo.
echo 使用方法：
echo   更新单词库例句_并行.bat [进程数]
echo.
echo 参数说明：
echo   进程数：并行处理的进程数量（1-16，默认4）
echo.
echo 示例：
echo   更新单词库例句_并行.bat 4    （使用4个进程）
echo   更新单词库例句_并行.bat 8    （使用8个进程）
echo.

set PROCESSES=%1
if "%PROCESSES%"=="" set PROCESSES=4

echo 使用 %PROCESSES% 个并行进程...
echo.

php update_word_bank_examples_parallel.php %PROCESSES%

pause
