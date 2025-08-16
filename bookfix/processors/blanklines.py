"""
Blank line removal processor for Bookfix.

This module provides functionality to remove blank lines (including lines
with only whitespace) from text content.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..context import BookfixContext


def remove_blank_lines(ctx: 'BookfixContext') -> 'BookfixContext':
    """
    Removes blank lines (including lines with only whitespace) from the text content.
    
    Args:
        ctx: BookfixContext object containing text
        
    Returns:
        Updated BookfixContext with blank lines removed
    """
    # Import here to avoid circular imports
    from ..logging import log_message
    
    log_message("Removing blank lines...")
    original_text = ctx.text
    original_line_count = len(original_text.splitlines())

    # Split the text into lines
    lines = ctx.text.splitlines()
    # Filter out lines that are empty or contain only whitespace
    non_blank_lines = [line for line in lines if line.strip()]
    # Join the remaining lines back together with newline characters
    ctx.text = "\n".join(non_blank_lines)

    final_line_count = len(non_blank_lines)
    removed_lines = original_line_count - final_line_count

    ctx.log_change('remove_blank_lines',
                   f"Removed {removed_lines} blank lines ({original_line_count} → {final_line_count} lines)",
                   len(original_text), len(ctx.text))

    log_message("Blank line removal complete.")
    return ctx