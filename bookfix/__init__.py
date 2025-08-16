"""
Bookfix - Ebook Text Processor

A PyQt5-based application for processing ebook text files with features like:
- Interactive word choice replacement (homograph disambiguation)
- Automatic text replacements
- Capitalization processing
- Roman numeral conversion
- Numbered line processing
- Blank line removal
- Period processing
"""

__version__ = "2.0.0"
__author__ = "Bookfix Team"
__description__ = "Ebook Text Processor with Interactive Choice System"

# Import main classes for easy access
from .context import BookfixContext
from .gui import BookfixMainWindow

__all__ = [
    "BookfixContext",
    "BookfixMainWindow",
]