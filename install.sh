#!/bin/bash

# Bookfix Installation Script
# This script sets up a Python virtual environment and installs dependencies

set -e  # Exit on any error

echo "🔧 Setting up Bookfix..."

# Detect Python command
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    # Check if it's Python 3
    if python -c "import sys; exit(0 if sys.version_info[0] == 3 else 1)" 2>/dev/null; then
        PYTHON_CMD="python"
    else
        echo "❌ Python 3 is required but only Python 2 found"
        exit 1
    fi
else
    echo "❌ Python is not installed or not in PATH"
    exit 1
fi

echo "✅ Using Python command: $PYTHON_CMD"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "🏗️ Creating virtual environment..."
    $PYTHON_CMD -m venv venv
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

echo "✅ Installation complete!"
echo ""
echo "📝 Note: Phonetic analysis was removed due to poor accuracy"
echo "📖 See phoneticreplacement.txt for details"
echo ""
echo "To run Bookfix:"
echo "  ./run.sh"