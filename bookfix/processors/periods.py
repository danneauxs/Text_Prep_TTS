"""
Period insertion processor for Bookfix.

This module provides functionality to insert periods into specified
abbreviations (e.g., 'Mr' -> 'M.r.').
"""

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..context import BookfixContext


def insert_periods_into_abbreviations(ctx: 'BookfixContext') -> 'BookfixContext':
    """
    Inserts periods into specified abbreviations (e.g., 'Mr' -> 'M.r.').
    
    Args:
        ctx: BookfixContext object containing text and periods set
        
    Returns:
        Updated BookfixContext with periods inserted into abbreviations
    """
    # Import here to avoid circular imports
    from ..logging import log_message
    
    log_message("Starting inserting periods into abbreviations.")
    original_text = ctx.text
    replacements_made = 0

    # Iterate through each abbreviation that needs periods
    for abbr in ctx.periods:
        # Create a regex pattern to find the whole word abbreviation
        pattern = r'\b' + re.escape(abbr) + r'\b'
        # Create the replacement string with periods inserted between characters and at the end
        replacement = '.'.join(abbr) + '.'
        # Count matches before replacement
        matches = re.findall(pattern, ctx.text)
        replacements_made += len(matches)
        # Use re.sub to replace all matches of the pattern with the replacement string
        ctx.text = re.sub(pattern, replacement, ctx.text)

    ctx.log_change('insert_periods',
                   f"Processed {len(ctx.periods)} abbreviations, made {replacements_made} insertions",
                   len(original_text), len(ctx.text))

    log_message("Finished inserting periods.")
    return ctx