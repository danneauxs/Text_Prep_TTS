"""
Automatic text replacement processor for Bookfix.

This module provides functionality to apply automatic find-and-replace rules
loaded from the data file using regex patterns.
"""

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..context import BookfixContext


def apply_automatic_replacements(ctx: 'BookfixContext') -> 'BookfixContext':
    """
    Applies all find and replace rules loaded from the data file using regex.
    
    Args:
        ctx: BookfixContext object containing text and replacement rules
        
    Returns:
        Updated BookfixContext with replacements applied
    """
    # Import here to avoid circular imports
    from ..logging import log_message
    
    log_message("Starting automatic replacements.")
    original_text = ctx.text
    replacement_count = 0

    for old, new in ctx.replacements.items():
        try:
            # Compile and apply as regex
            pattern = re.compile(old)
            matches = list(pattern.finditer(ctx.text))
            ctx.text = pattern.sub(new, ctx.text)
            replacement_count += len(matches)
        except re.error as e:
            log_message(f"Regex error in pattern '{old}': {e}", level="ERROR")

    ctx.log_change('automatic_replacements',
                   f"Applied {len(ctx.replacements)} rules, made {replacement_count} replacements",
                   len(original_text), len(ctx.text))

    log_message("Finished automatic replacements.")
    return ctx