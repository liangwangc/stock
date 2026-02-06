@echo off
cd /d "%~dp0"

echo.
echo Starting server...
echo.

REM Check if XAMPP PHP exists and is executable
if exist "C:\xampp\php\php.exe" (
    echo Found PHP: C:\xampp\php\php.exe
    echo.
    echo Server URL: http://localhost:8000
    echo Press Ctrl+C to stop
    echo.
    cd /d "%~dp0"
    "C:\xampp\php\php.exe" -S localhost:8000
    if errorlevel 1 (
        echo.
        echo ERROR: Failed to start server
        echo Please check if XAMPP is installed correctly
        pause
    )
    exit /b
)

if exist "C:\xampp64\php\php.exe" (
    echo Found PHP: C:\xampp64\php\php.exe
    echo.
    echo Server URL: http://localhost:8000
    echo Press Ctrl+C to stop
    echo.
    cd /d "%~dp0"
    "C:\xampp64\php\php.exe" -S localhost:8000
    if errorlevel 1 (
        echo.
        echo ERROR: Failed to start server
        echo Please check if XAMPP is installed correctly
        pause
    )
    exit /b
)

where php >nul 2>&1
if %errorlevel% == 0 (
    echo Found PHP in system PATH
    echo.
    echo Server URL: http://localhost:8000
    echo Press Ctrl+C to stop
    echo.
    cd /d "%~dp0"
    php -S localhost:8000
    exit /b
)

echo ERROR: PHP not found!
echo.
echo Please install XAMPP from: https://www.apachefriends.org/
echo.
pause
