#!/bin/bash
# KittyCode Installer for Mac/Linux
echo "ฅ^•ﻌ•^ฅ 🐾 Welcome to the KittyCode Installation Wizard!"

# Check for Python
if ! command -v python3 &> /dev/null
then
    echo "❌ Error: Python 3 is not installed. Please install it first."
    exit 1
fi

echo "📦 Setting up virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

echo "🚀 Installing dependencies..."
pip install --upgrade pip
pip install -e .

echo ""
echo "✨ ✨ ✨ ✨ ✨ ✨ ✨ ✨ ✨ ✨ ✨ ✨ ✨ ✨"
echo "✨ KITTYCODE INSTALLED SUCCESSFULLY! ✨"
echo "✨ ✨ ✨ ✨ ✨ ✨ ✨ ✨ ✨ ✨ ✨ ✨ ✨ ✨"
echo ""
echo "To get started, run:"
echo "  source .venv/bin/activate"
echo "  kitty setup"
echo ""
echo "Happy coding! nya~"
