"""
Interactive text choice processor for Bookfix.

This module provides functionality for interactive word choice processing,
where users can select from predefined replacement options for specific words.
"""

import re
import datetime
from typing import TYPE_CHECKING, List, Tuple, Optional, Callable, Any

if TYPE_CHECKING:
    from ..context import BookfixContext


class InteractiveChoiceProcessor:
    """
    Handles interactive word choice processing with GUI callback support.
    
    This class manages the state for processing interactive word choices,
    supporting both Tkinter and PyQt5 GUI frameworks through callbacks.
    """
    
    def __init__(self):
        # Reset all state each time we process
        self.current_word: Optional[str] = None
        self.current_match: int = 0
        self.matches: List[Any] = []
        self.processed_words: int = 0
        self.total_words: int = 0
        self.current_text: str = ""
        
        # GUI callbacks - set by the GUI framework
        self.progress_callback: Optional[Callable[[int, int, str], None]] = None
        self.choice_display_callback: Optional[Callable[[str, List[str]], None]] = None
        self.text_update_callback: Optional[Callable[[str, bool], None]] = None
        self.status_callback: Optional[Callable[[str], None]] = None
        self.text_edit_widget: Optional[Any] = None  # Direct access to text widget for highlighting
    
    def reset_state(self):
        """Reset all processing state - called before processing new text."""
        self.current_word = None
        self.current_match = 0
        self.matches = []
        self.processed_words = 0
        self.total_words = 0
        self.current_text = ""
    
    def process_choices(self, ctx: 'BookfixContext') -> 'BookfixContext':
        """
        Main entry point for interactive choice processing.
        
        Args:
            ctx: BookfixContext containing text and choice definitions
            
        Returns:
            Updated BookfixContext after interactive processing
        """
        from ..logging import log_message
        
        log_message("Starting interactive choice processing")
        
        # CRITICAL: Reset all state and start fresh with current text
        self.reset_state()
        self.current_text = ctx.text
        log_message(f"Choice processor received text with length: {len(ctx.text)}")
        
        self.total_words = len(ctx.choices)
        self.processed_words = 0
        
        if self.total_words == 0:
            if self.status_callback:
                self.status_callback("No words require interactive choices")
            return ctx
        
        # Clear matches log
        try:
            open('matches.txt', 'w', encoding='utf-8').close()
            log_message("Cleared matches.txt log file.")
        except Exception as e:
            log_message(f"Error clearing matches.txt: {e}", level="ERROR")
        
        # Start processing first word
        self._start_word_processing(ctx)
        
        return ctx
    
    def _start_word_processing(self, ctx: 'BookfixContext'):
        """Start processing the next word in the choices dictionary."""
        if self.processed_words < self.total_words:
            words = list(ctx.choices.keys())
            self.current_word = words[self.processed_words]
            self.current_match = 0
            
            # Find all matches for current word using our current text
            self.matches = list(re.finditer(
                r'\b' + re.escape(self.current_word) + r'\b', 
                self.current_text, 
                re.IGNORECASE
            ))
            
            self._log_matches_state("start_word_processing")
            
            if self.matches:
                # Highlight first match before displaying choices
                self._highlight_current_match(ctx)
                
                # Display choices for this word
                options = ctx.choices[self.current_word]
                if self.choice_display_callback:
                    self.choice_display_callback(self.current_word, options)
            else:
                # No matches, move to next word
                self._finish_current_word(ctx)
    
    def _highlight_current_match(self, ctx: 'BookfixContext'):
        """Highlight the current match and update status."""
        if self.matches and self.current_match < len(self.matches):
            match = self.matches[self.current_match]
            start, end = match.span()
            
            # Handle our own highlighting directly
            self._apply_highlighting(start, end, self.current_word)
            
            if self.status_callback:
                status = f"Replacing {self.current_word}: {self.current_match + 1}/{len(self.matches)}"
                self.status_callback(status)
        else:
            if self.status_callback:
                self.status_callback(f"Finished {self.current_word}")
    
    def _apply_highlighting(self, start: int, end: int, word: str):
        """Apply highlighting directly to our text widget."""
        from ..logging import log_message
        
        if not self.text_edit_widget:
            log_message("No text widget available for highlighting")
            return
            
        log_message(f"Highlighting text: '{word}' at position {start}-{end}")
        
        # Clear previous highlighting
        self._clear_highlighting()
        
        # Validate positions against current text
        widget_text = self.text_edit_widget.toPlainText()
        widget_length = len(widget_text)
        processor_length = len(self.current_text)
        
        if widget_length != processor_length:
            log_message(f"ERROR: Text widget has {widget_length} chars but processor has {processor_length} chars - OUT OF SYNC!")
            log_message(f"Updating widget with current processor text...")
            self.text_edit_widget.setPlainText(self.current_text)
            widget_text = self.current_text
        
        if start < 0 or end > len(widget_text) or start >= end:
            log_message(f"Invalid highlight range: {start}-{end} (text length: {len(widget_text)})")
            return
        
        # Import Qt classes for highlighting
        try:
            from PyQt5.QtGui import QTextCursor, QTextCharFormat, QColor
            
            # Get cursor and create highlight format
            cursor = self.text_edit_widget.textCursor()
            format_highlight = QTextCharFormat()
            format_highlight.setBackground(QColor("yellow"))
            format_highlight.setForeground(QColor("black"))
            format_highlight.setFontWeight(700)
            
            # Apply highlight to the specific range
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.KeepAnchor)
            cursor.setCharFormat(format_highlight)
            
            # Center the highlighted text in viewport after a small delay to ensure highlighting is applied
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(50, lambda: self._center_text_in_viewport(start))
            
            log_message(f"Applied highlighting to range {start}-{end}")
            
        except Exception as e:
            log_message(f"Error applying highlighting: {e}", level="ERROR")
    
    def _center_text_in_viewport(self, position: int):
        """Position the highlighted text with context lines above it."""
        if not self.text_edit_widget:
            return
            
        try:
            from PyQt5.QtGui import QTextCursor
            from ..logging import log_message
            
            # Find the block (line) containing our position
            document = self.text_edit_widget.document()
            target_block = document.findBlock(position)
            target_line = target_block.blockNumber()
            
            # Go back 3 lines to show context above the highlighted word
            context_line = max(0, target_line - 3)
            context_block = document.findBlockByNumber(context_line)
            
            # Position cursor at the context line (3 lines above highlighted word)
            cursor = self.text_edit_widget.textCursor()
            cursor.setPosition(context_block.position())
            self.text_edit_widget.setTextCursor(cursor)
            
            # Ensure this position is at the top of the viewport
            self.text_edit_widget.ensureCursorVisible()
            
            # Now set cursor back to the highlighted position but don't scroll
            cursor.setPosition(position)
            self.text_edit_widget.setTextCursor(cursor)
            
            log_message(f"Positioned text at line {target_line}, showing context from line {context_line}")
            
        except Exception as e:
            from ..logging import log_message
            log_message(f"Error positioning text: {e}", level="ERROR")
    
    def _clear_highlighting(self):
        """Clear all highlighting from the text widget."""
        if not self.text_edit_widget:
            return
            
        try:
            from PyQt5.QtGui import QTextCursor, QTextCharFormat
            
            # Get the current document and clear all formatting
            document = self.text_edit_widget.document()
            cursor = QTextCursor(document)
            cursor.select(QTextCursor.Document)
            format_default = QTextCharFormat()
            cursor.setCharFormat(format_default)
            cursor.clearSelection()
            self.text_edit_widget.setTextCursor(cursor)
            
        except Exception as e:
            from ..logging import log_message
            log_message(f"Error clearing highlighting: {e}", level="ERROR")
    
    def handle_choice(self, choice: str, ctx: 'BookfixContext') -> bool:
        """
        Handle user's choice selection.
        
        Args:
            choice: The selected replacement text
            ctx: BookfixContext to modify
            
        Returns:
            True if more choices needed, False if word is complete
        """
        from ..logging import log_message
        
        if not self.matches or self.current_match >= len(self.matches):
            return self._finish_current_word(ctx)
        
        match = self.matches[self.current_match]
        start, end = match.span()
        matched_text = self.current_text[start:end]
        
        # Check if no change needed
        if choice.lower() == matched_text.lower():
            # Skip this match, remove from list
            self.matches.pop(self.current_match)
            
            if self.current_match < len(self.matches):
                self._highlight_current_match(ctx)
                return True
            else:
                return self._finish_current_word(ctx)
        
        # Apply replacement to both our current text and context
        self.current_text = self.current_text[:start] + choice + self.current_text[end:]
        ctx.text = self.current_text
        
        # Update text display
        if self.text_update_callback:
            self.text_update_callback(ctx.text, preserve_highlighting=False)
        
        # Log the replacement
        try:
            with open('debug.txt', 'a', encoding='utf-8') as debug_file:
                debug_file.write(f"{self.current_word} -> {choice}\n")
        except Exception as e:
            log_message(f"Error writing to debug.txt: {e}", level="ERROR")
        
        # CRITICAL: Re-find ALL matches in the NEW current text
        self.matches = list(re.finditer(
            r'\b' + re.escape(self.current_word) + r'\b', 
            self.current_text, 
            re.IGNORECASE
        ))
        
        # Find next match position
        next_index = 0
        for i, m in enumerate(self.matches):
            if m.start() >= end:
                next_index = i
                break
        else:
            next_index = len(self.matches)
        
        self.current_match = next_index
        self._log_matches_state("after_replacement")
        
        if self.current_match < len(self.matches):
            self._highlight_current_match(ctx)
            return True
        else:
            return self._finish_current_word(ctx)
    
    def _finish_current_word(self, ctx: 'BookfixContext') -> bool:
        """Finish processing current word and move to next."""
        self.processed_words += 1
        
        # Update progress
        if self.progress_callback:
            progress = int((self.processed_words / self.total_words) * 100)
            self.progress_callback(self.processed_words, self.total_words, f"Progress: {progress}%")
        
        if self.processed_words < self.total_words:
            self._start_word_processing(ctx)
            return True
        else:
            # All words processed
            ctx.log_change('interactive_choices',
                          f"Processed {self.total_words} words with interactive choices",
                          None, None)
            
            if self.status_callback:
                self.status_callback("Interactive choices processing complete.")
            
            return False
    
    def _log_matches_state(self, location: str):
        """Log current matches state for debugging."""
        try:
            with open('matches.txt', 'a', encoding='utf-8') as f:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"--- Log Entry ({timestamp}) ---\n")
                f.write(f"Location: {location}\n")
                f.write(f"Current Word: '{self.current_word}'\n")
                f.write(f"Current Match Index: {self.current_match}\n")
                f.write(f"Total Matches Found: {len(self.matches)}\n")
                f.write("Matches Details:\n")
                
                if self.matches:
                    for i, match in enumerate(self.matches):
                        try:
                            matched_text = match.group(0)
                        except IndexError:
                            matched_text = "[Error getting match text]"
                        f.write(f"  Match {i}: Span=({match.start()}, {match.end()}), Text='{matched_text}'\n")
                else:
                    f.write("  No matches found.\n")
                f.write("---\n\n")
        except Exception as e:
            print(f"ERROR: Failed to write to matches.txt: {e}")


# Legacy function for backward compatibility
def process_choices(ctx: 'BookfixContext') -> 'BookfixContext':
    """
    Legacy function for backward compatibility.
    
    Note: This requires GUI callbacks to be set up properly.
    """
    processor = InteractiveChoiceProcessor()
    return processor.process_choices(ctx)