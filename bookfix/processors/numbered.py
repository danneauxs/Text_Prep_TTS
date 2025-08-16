"""
Numbered line editing processor for Bookfix.

This module provides functionality for interactive editing of lines containing
3 or more digit numbers, typically for converting Roman numerals manually.
"""

import re
from typing import TYPE_CHECKING, List, Tuple, Dict, Optional, Callable

if TYPE_CHECKING:
    from ..context import BookfixContext


class NumberedLineProcessor:
    """
    Handles interactive numbered line editing with GUI callback support.
    
    This class manages the state for processing lines with numbers,
    supporting both Tkinter and PyQt5 GUI frameworks through callbacks.
    """
    
    def __init__(self):
        self.numbered_lines: List[Tuple[int, str, List[Tuple[int, int]]]] = []
        self.current_numbered_idx: int = 0
        self.numbered_edits: Dict[int, str] = {}
        
        # GUI callbacks - set by the GUI framework
        self.line_display_callback: Optional[Callable[[int, str, List[Tuple[int, int]]], None]] = None
        self.navigation_callback: Optional[Callable[[int, int], None]] = None  # current, total
        self.completion_callback: Optional[Callable[[Dict[int, str]], None]] = None
        self.status_callback: Optional[Callable[[str], None]] = None
    
    def find_numbered_lines(self, text: str) -> List[Tuple[int, str, List[Tuple[int, int]]]]:
        """
        Find lines containing 3+ digit numbers.
        
        Args:
            text: Text to search
            
        Returns:
            List of (line_number, line_content, match_spans) tuples
            where match_spans is a list of (start_idx, end_idx) for each number match
        """
        lines = text.splitlines()
        numbered_lines = []
        number_pattern = re.compile(r'\d{3,}')
        
        for idx, line in enumerate(lines):
            spans = [m.span() for m in number_pattern.finditer(line)]
            if spans:
                numbered_lines.append((idx, line, spans))
        
        return numbered_lines
    
    def start_numbered_line_edit(self, ctx: 'BookfixContext') -> bool:
        """
        Start the numbered line editing process.
        
        Args:
            ctx: BookfixContext containing text to process
            
        Returns:
            True if lines found and editing started, False if no lines found
        """
        self.numbered_lines = self.find_numbered_lines(ctx.text)
        self.current_numbered_idx = 0
        self.numbered_edits = {}
        
        if not self.numbered_lines:
            if self.status_callback:
                self.status_callback("No lines with 3+ digit numbers found.")
            return False
        
        self._show_current_line()
        return True
    
    def _show_current_line(self):
        """Display the current numbered line for editing."""
        if self.current_numbered_idx < len(self.numbered_lines):
            lineno, line, spans = self.numbered_lines[self.current_numbered_idx]
            
            if self.line_display_callback:
                self.line_display_callback(lineno, line, spans)
            
            if self.navigation_callback:
                self.navigation_callback(self.current_numbered_idx + 1, len(self.numbered_lines))
            
            if self.status_callback:
                self.status_callback(f"Editing line {lineno + 1}: {self.current_numbered_idx + 1}/{len(self.numbered_lines)}")
    
    def save_and_next(self, edited_text: str) -> bool:
        """
        Save the current line edit and move to next line.
        
        Args:
            edited_text: The edited line content
            
        Returns:
            True if more lines to edit, False if finished
        """
        if self.current_numbered_idx < len(self.numbered_lines):
            lineno, original_line, spans = self.numbered_lines[self.current_numbered_idx]
            
            # Only save if text was actually changed
            if edited_text.strip() != original_line.strip():
                self.numbered_edits[lineno] = edited_text.strip()
        
        return self.go_next()
    
    def go_next(self) -> bool:
        """
        Move to the next numbered line.
        
        Returns:
            True if more lines to edit, False if finished
        """
        if self.current_numbered_idx < len(self.numbered_lines) - 1:
            self.current_numbered_idx += 1
            self._show_current_line()
            return True
        else:
            return self._finish_editing()
    
    def go_previous(self) -> bool:
        """
        Move to the previous numbered line.
        
        Returns:
            True always (can always go back)
        """
        if self.current_numbered_idx > 0:
            self.current_numbered_idx -= 1
            self._show_current_line()
        return True
    
    def _finish_editing(self) -> bool:
        """
        Finish the numbered line editing process.
        
        Returns:
            False to indicate editing is complete
        """
        if self.completion_callback:
            self.completion_callback(self.numbered_edits)
        
        if self.status_callback:
            if self.numbered_edits:
                self.status_callback("Numbered line editing complete.")
            else:
                self.status_callback("Numbered line editing complete (no changes).")
        
        return False
    
    def apply_edits(self, ctx: 'BookfixContext'):
        """
        Apply all saved edits to the context text.
        
        Args:
            ctx: BookfixContext to modify
        """
        if not self.numbered_edits:
            return
        
        lines = ctx.text.splitlines()
        changes_made = 0
        
        for lineno, replacement in self.numbered_edits.items():
            if lineno < len(lines):
                lines[lineno] = replacement
                changes_made += 1
        
        ctx.text = "\n".join(lines)
        
        ctx.log_change('numbered_line_edit',
                      f"Applied {changes_made} line edits from numbered line editor",
                      None, None)


# Legacy functions for backward compatibility
def find_numbered_lines(text: str) -> List[Tuple[int, str, List[Tuple[int, int]]]]:
    """Legacy function for backward compatibility."""
    processor = NumberedLineProcessor()
    return processor.find_numbered_lines(text)


def start_numbered_line_edit() -> bool:
    """
    Legacy function for backward compatibility.
    
    Note: This requires GUI callbacks to be set up properly and
    a global context to work with the original implementation.
    """
    # This is a placeholder - the original function relied heavily on globals
    # In the new architecture, this should be handled by the GUI directly
    return False


def finish_numbered_line_edit():
    """
    Legacy function for backward compatibility.
    
    Note: This is a placeholder - the original function relied heavily on globals
    """
    pass