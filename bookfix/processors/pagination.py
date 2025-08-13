"""
Pagination removal processor for Bookfix.

This module provides functionality to remove pagination elements from text
based on file type, using BeautifulSoup for HTML/XHTML and simple line
checks for TXT files.
"""

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..context import BookfixContext

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


def remove_pagination(ctx: 'BookfixContext') -> 'BookfixContext':
    """
    Attempts to remove pagination elements from the text based on file type.
    Uses BeautifulSoup for HTML/XHTML and simple line checks for TXT files.
    Logs removed elements to a debug file.
    
    Args:
        ctx: BookfixContext object containing text and filepath
        
    Returns:
        Updated BookfixContext with pagination elements removed
    """
    # Import here to avoid circular imports
    from ..logging import log_message
    
    log_message("Starting removing pagination.")
    original_text = ctx.text
    pagination_log = []  # List to record what was removed

    try:
        # Check if the file is HTML or XHTML
        if ctx.filepath and ctx.filepath.lower().endswith((".xhtml", ".html")):
            if BeautifulSoup is None:
                log_message("BeautifulSoup not available, skipping HTML pagination removal", level="WARNING")
                return ctx
                
            soup = BeautifulSoup(ctx.text, 'xml')  # Parse the text using BeautifulSoup's XML parser

            # Find elements commonly used for pagination based on class or ID
            page_number_elements = soup.find_all(class_=re.compile(r"page-number", re.IGNORECASE))
            page_number_elements.extend(soup.find_all(id=re.compile(r"page-number", re.IGNORECASE)))
            # Find <p> tags containing only digits (common for simple page numbers)
            page_number_elements.extend(soup.find_all(name=re.compile(r"p", re.IGNORECASE), string=re.compile(r"^\s*\d+\s*$", re.IGNORECASE)))

            # Iterate through found elements
            for element in page_number_elements:
                pagination_log.append(f"Removed: {element}")  # Log the element
                element.decompose()  # Remove the element from the soup

            ctx.text = str(soup)  # Convert the modified soup back to a string
            # Remove any empty lines that might result from element removal
            lines = ctx.text.splitlines()
            filtered_lines = [line for line in lines if line.strip()]
            ctx.text = "\n".join(filtered_lines)

        # Check if the file is a plain text file
        elif ctx.filepath and ctx.filepath.lower().endswith(".txt"):
            lines = ctx.text.splitlines()  # Split text into lines
            filtered_lines = []  # List for lines to keep
            # Iterate through each line
            for line in lines:
                # If the line contains only digits (potential page number)
                if line.strip().isdigit():
                    pagination_log.append(f"Removed: {line}")  # Log the line
                    # Skip adding this line to filtered_lines (effectively removing it)
                else:
                    filtered_lines.append(line)  # Keep lines that are not just digits
            ctx.text = "\n".join(filtered_lines)  # Join filtered lines back

    except Exception as e:
        # Handle errors during pagination removal
        log_message(f"Error removing pagination: {e}", level="ERROR")
        # Note: removed messagebox dependency since it's GUI-specific

    # Save the log of removed pagination to a file
    try:
        with open("pagination_debug.txt", "w", encoding="utf-8") as log_file:
            log_file.write("\n".join(pagination_log))
        log_message("Pagination removal log saved to pagination_debug.txt.")
    except Exception as e:
        log_message(f"Error saving pagination debug log: {e}", level="ERROR")

    ctx.log_change('remove_pagination',
                   f"Removed {len(pagination_log)} pagination elements",
                   len(original_text), len(ctx.text))

    log_message("Finished removing pagination.")
    return ctx