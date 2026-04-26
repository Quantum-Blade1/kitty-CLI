@echo off
:: KittyCode Installer for Windows
echo ฅ^•ﻌ•^ฅ 🐾 Welcome to the KittyCode Installation Wizard!

:: Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Error: Python is not installed or not in PATH. Please install it from python.org.
    pause
    exit /b
)

echo 📦 Setting up virtual environment...
python -m venv .venv
call .venv\Scripts\activate

echo 🚀 Installing dependencies...
python -m pip install --upgrade pip
pip install -e .

echo.
echo ✨ ✨ ✨ ✨ ✨ ✨ ✨ ✨ ✨ ✨ ✨ ✨ ✨ ✨
echo ✨ KITTYCODE INSTALLED SUCCESSFULLY! ✨
echo ✨ ✨ ✨ ✨ ✨ ✨ ✨ ✨ ✨ ✨ ✨ ✨ ✨ ✨
echo.
echo To get started, run:
echo   .venv\Scripts\activate
echo   kitty setup
echo.
echo Happy coding! nya~
pause
