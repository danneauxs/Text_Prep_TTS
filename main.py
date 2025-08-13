#!/usr/bin/env python3
"""
Bookfix - Ebook Text Processing Tool

Main entry point for the modular Bookfix application.
Launches the PyQt5 GUI interface for interactive text processing.

Usage:
    python main.py

Requirements:
    - PyQt5
    - BeautifulSoup4 (optional, for HTML processing)

Author: Bookfix Development Team
Version: 2.0.0 (Modular PyQt5 Edition)
"""

import sys
import os

# Add the current directory to Python path for module imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_dependencies():
    """Check for required dependencies and provide helpful error messages."""
    missing_deps = []
    
    # Check for PyQt5
    try:
        import PyQt5
    except ImportError:
        missing_deps.append("PyQt5")
    
    # Check for BeautifulSoup (optional but recommended)
    try:
        import bs4
    except ImportError:
        print("Warning: BeautifulSoup4 not found. HTML processing will be limited.")
        print("Install with: pip install beautifulsoup4")
    
    if missing_deps:
        print("ERROR: Missing required dependencies:")
        for dep in missing_deps:
            print(f"  - {dep}")
        print("\nPlease install missing dependencies:")
        if "PyQt5" in missing_deps:
            print("  pip install PyQt5")
        print("\nThen run the application again.")
        sys.exit(1)


def main():
    """Main application entry point."""
    print("Bookfix v2.0.0 - Ebook Text Processing Tool")
    print("=" * 50)
    
    # Check dependencies
    check_dependencies()
    
    try:
        # Import and run the GUI
        from bookfix.gui import main as gui_main
        gui_main()
        
    except ImportError as e:
        print(f"ERROR: Could not import Bookfix modules: {e}")
        print("\nPlease ensure you're running from the correct directory")
        print("and that all required files are present.")
        sys.exit(1)
    
    except Exception as e:
        print(f"ERROR: Application failed to start: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()