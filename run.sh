#!/bin/bash

# Bookfix SpaCy Enhanced Launcher Script

# Function to pause and wait for user input
pause_for_user() {
    echo ""
    echo "Press any key to continue..."
    read -n 1 -s
}

# Change to the script's directory to ensure we're in the right place
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
echo "📁 Script directory: $SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found in $(pwd)"
    echo "Please run install.sh first to create the virtual environment."
    pause_for_user
    exit 1
fi

# Check if activation script exists
if [ ! -f "venv/bin/activate" ]; then
    echo "❌ Virtual environment activation script not found at $(pwd)/venv/bin/activate"
    echo "Virtual environment may be corrupted. Please run install.sh again."
    pause_for_user
    exit 1
fi

# Activate virtual environment and start the application
echo "🚀 Starting Bookfix SpaCy Enhanced..."
echo "📁 Working directory: $(pwd)"
echo "🔄 Activating virtual environment..."

source venv/bin/activate

# Verify activation worked
if [ -z "$VIRTUAL_ENV" ]; then
    echo "❌ Failed to activate virtual environment"
    echo "Please check if venv/bin/activate exists and is readable."
    pause_for_user
    exit 1
fi

echo "✅ Virtual environment activated: $VIRTUAL_ENV"

# Check if main.py exists
if [ ! -f "main.py" ]; then
    echo "❌ main.py not found in current directory: $(pwd)"
    pause_for_user
    exit 1
fi

# Run the application and capture exit code
python main.py
exit_code=$?

# Show result and pause
if [ $exit_code -eq 0 ]; then
    echo "✅ Application completed successfully."
else
    echo "❌ Application exited with error code: $exit_code"
fi

pause_for_user