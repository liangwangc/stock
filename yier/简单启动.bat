@echo off
cd /d "%~dp0"

echo.
echo Starting server...
echo.

REM Try XAMPP first
if exist "C:\xampp\php\php.exe" (
    echo Found PHP at: C:\xampp\php\php.exe
    echo Server URL: http://localhost:8000
    echo Press Ctrl+C to stop
    echo.
    "C:\xampp\php\php.exe" -S localhost:8000 -t .
    goto :end
)

REM Try XAMPP64
if exist "C:\xampp64\php\php.exe" (
    echo Found PHP at: C:\xampp64\php\php.exe
    echo Server URL: http://localhost:8000
    echo Press Ctrl+C to stop
    echo.
    "C:\xampp64\php\php.exe" -S localhost:8000 -t .
    goto :end
)

REM Try system PATH
where php >nul 2>&1
if %errorlevel% == 0 (
    echo Found PHP in system PATH
    echo Server URL: http://localhost:8000
    echo Press Ctrl+C to stop
    echo.
    php -S localhost:8000 -t .
    goto :end
)

REM Not found
echo ERROR: PHP not found!
echo.
echo Please install XAMPP from: https://www.apachefriends.org/
echo Or add PHP to system PATH
echo.

:end
if errorlevel 1 (
    echo.
    echo ERROR: Failed to start server
    echo Please check if PHP path is correct
    echo.
    pause
)
