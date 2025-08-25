"""
Roman numeral conversion processor for Bookfix.

This module provides functionality to convert Roman numerals to Arabic numbers
with protection for abbreviations and configurable ignore lists.
"""

import re
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from ..context import BookfixContext


class RomanNumeralProcessor:
    """Processor for converting Roman numerals to Arabic numbers."""
    
    def process_roman_numerals(self, ctx: 'BookfixContext') -> 'BookfixContext':
        """Process Roman numerals using the function."""
        # Ensure roman_ignore_set exists
        if not hasattr(ctx, 'roman_ignore_set'):
            ctx.roman_ignore_set = set(ctx.roman_ignore) if hasattr(ctx, 'roman_ignore') else set()
        return convert_roman_numerals(ctx)


def convert_roman_numerals(ctx: 'BookfixContext') -> 'BookfixContext':
    """
    Convert Roman numerals to Arabic numbers with abbreviation protection.
    
    Args:
        ctx: BookfixContext object containing text and roman_ignore_set
        
    Returns:
        Updated BookfixContext with Roman numerals converted
    """
    # Import here to avoid circular imports
    from ..logging import log_message
    
    log_message("Starting converting Roman numerals.", level="INFO")
    original_text = ctx.text
    conversions_made = 0

    # Clear or create the conversion log at the start of each run
    try:
        open('roman_conversions.log', 'w', encoding='utf-8').close()
    except Exception as e:
        log_message(f"Error clearing roman_conversions.log: {e}", level="ERROR")

    # Roman numeral pattern from original working version
    # Uses lookbehind/ahead to avoid letters and symbols, preventing matches inside words
    roman_pattern = r"(?<![A-Za-z&\-+:;/\\'`´''])\b([VXLCDM]|[MDCLXVI]{2,})\b(?![A-Za-z&\-+:;/\\]|['`´''][a-rtuvwxyzA-RTUVWXYZ])"

    def _replace(m):
        nonlocal conversions_made
        token = m.group(1) if m.lastindex and m.lastindex >= 1 else m.group(0)
        start_pos = m.start()
        end_pos = m.end()
        
        # Additional context checks for edge cases
        before_char = ctx.text[start_pos - 1] if start_pos > 0 else ' '
        after_char = ctx.text[end_pos] if end_pos < len(ctx.text) else ' '
        
        # Skip if it's like "X.V" (version number) - check both before and after period
        if (after_char == '.' and end_pos + 1 < len(ctx.text) and ctx.text[end_pos + 1] in 'VXLCDMI') or \
           (before_char == '.' and start_pos > 1 and ctx.text[start_pos - 2] in 'VXLCDMI'):
            return token
            
        # Skip common English words that happen to be Roman numerals
        if token.upper() in ['MIX']:  # Add other problematic words as needed
            # Only convert if it looks like a chapter/section context
            context_before = ctx.text[max(0, start_pos-20):start_pos].lower()
            if not any(word in context_before for word in ['chapter', 'section', 'part', 'volume', 'book']):
                return token
        
        # Check if this roman numeral should be ignored
        if token.upper() in ctx.roman_ignore_set:
            log_message(f"Skipping roman numeral '{token}' (found in roman_ignore_set)", level="DEBUG")
            return token

        val = roman_to_arabic(token)

        if isinstance(val, int) and val > 0:
            # Log the conversion with context
            start, end = m.start(), m.end()
            context_start = max(0, start - 10)
            context_end = min(len(ctx.text), end + 10)
            context = ctx.text[context_start:context_end]

            try:
                with open('roman_conversions.log', 'a', encoding='utf-8') as conv_log:
                    conv_log.write(f"Converted '{token}' to '{val}' in context: ...{context}...\n")
            except Exception as e:
                log_message(f"Error writing to roman_conversions.log: {e}", level="ERROR")

            conversions_made += 1
            return str(val)

        # Leave unchanged if not a valid roman numeral
        return token

    # Perform the substitution on the text
    ctx.text = re.sub(roman_pattern, _replace, ctx.text)

    ctx.log_change('roman_numerals',
                   f"Converted {conversions_made} Roman numerals to Arabic numbers",
                   len(original_text), len(ctx.text))

    log_message("Finished converting Roman numerals.", level="INFO")
    return ctx


def roman_to_arabic(roman: str) -> Union[int, None]:
    """
    Converts a single Roman numeral string to its Arabic integer equivalent.
    
    Args:
        roman: Roman numeral string to convert
        
    Returns:
        Integer equivalent or None if not a valid Roman numeral or is "I"
    """
    roman = roman.upper()
    # skip lone "I"
    if roman == "I":
        return None

    # Strict validator for numerals 1–3999
    validator = r"^M{0,3}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3})$"
    if not re.fullmatch(validator, roman):
        return None

    # Map and compute using subtractive notation
    roman_map = {'I': 1, 'V': 5, 'X': 10, 'L': 50,
                 'C': 100, 'D': 500, 'M': 1000}
    total = 0
    prev = 0
    for ch in reversed(roman):
        val = roman_map[ch]
        total += val if val >= prev else -val
        prev = val

    return total