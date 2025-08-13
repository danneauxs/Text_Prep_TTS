"""
All-caps sequence processor for Bookfix.

This module provides functionality for processing sequences of all-caps words,
allowing users to interactively decide whether to lowercase them or ignore them.
"""

import re
from typing import TYPE_CHECKING, Set, List, Tuple, Optional, Callable, Any

if TYPE_CHECKING:
    from ..context import BookfixContext


class AllCapsProcessor:
    """
    Handles interactive all-caps sequence processing with GUI callback support.
    
    This class manages the state for processing all-caps sequences,
    supporting both Tkinter and PyQt5 GUI frameworks through callbacks.
    """
    
    def __init__(self):
        self.current_caps_sequence: Optional[str] = None
        self.current_caps_span: Optional[Tuple[int, int]] = None
        self.all_caps_matches_original: List[Any] = []
        self.decided_sequences_text: Set[str] = set()
        self.lowercased_original_spans: Set[Tuple[int, int]] = set()
        self.current_match_index: int = 0
        self.current_text: str = ""
        
        # GUI callbacks - set by the GUI framework
        self.choice_display_callback: Optional[Callable[[str, List[str]], None]] = None
        self.text_update_callback: Optional[Callable[[str, bool], None]] = None
        self.status_callback: Optional[Callable[[str], None]] = None
        self.text_edit_widget: Optional[Any] = None  # Direct access to text widget for highlighting
    
    def process_all_caps_sequences(self, ctx: 'BookfixContext') -> 'BookfixContext':
        """
        Main entry point for all-caps sequence processing.
        
        Args:
            ctx: BookfixContext containing text and processing settings
            
        Returns:
            Updated BookfixContext after processing
        """
        from ..logging import log_message
        
        log_message("=== Entering process_all_caps_sequences ===", level="DEBUG")
        log_message(f"DEBUG: process sees ignore_set = {ctx.ignore_set}", level="DEBUG")
        
        # Store current text state independently
        self.current_text = ctx.text
        
        # Snapshot text for regex detection
        original_for_detection = ctx.text
        log_message(f"Original text length: {len(original_for_detection)} chars", level="DEBUG")
        
        # Compile regex (no newlines, uppercase & spaces only)
        sequence_pattern = re.compile(r"\b[A-Z](?:[A-Z ]*[A-Z])\b")
        log_message(f"Using sequence_pattern: {sequence_pattern.pattern}", level="DEBUG")
        
        # Detect sequences in the original text
        self.all_caps_matches_original = list(sequence_pattern.finditer(original_for_detection))
        detected_sequences = [m.group(0) for m in self.all_caps_matches_original]
        log_message(f"All-caps sequences detected: {', '.join(detected_sequences)}", level="DEBUG")
        
        # Initialize tracking sets
        self.decided_sequences_text = set()
        self.lowercased_original_spans = set()
        
        # Pre-pass: auto-lowercase words from lowercase_set
        log_message("Pre-pass: applying lowercase_set auto-lowercasing", level="DEBUG")
        working_text = original_for_detection
        for word in ctx.lowercase_set:
            working_text = re.sub(rf'\b{re.escape(word)}\b', word.lower(), working_text)
        
        ctx.text = working_text
        
        if self.text_update_callback:
            # Clear previous highlighting when starting all-caps processing
            self.text_update_callback(ctx.text, preserve_highlighting=False)
        
        log_message("Text area initialized with current text", level="DEBUG")
        
        if self.status_callback:
            self.status_callback("Processing All-Caps sequences...")
        
        # Start processing first sequence
        self.current_match_index = 0
        self._process_next_sequence(ctx)
        
        return ctx
    
    def _process_next_sequence(self, ctx: 'BookfixContext'):
        """Process the next all-caps sequence."""
        from ..logging import log_message
        
        while self.current_match_index < len(self.all_caps_matches_original):
            match = self.all_caps_matches_original[self.current_match_index]
            seq_text = match.group(0)
            
            log_message(f"DEBUG: Checking sequence '{seq_text}' against ignore_set: {ctx.ignore_set}", level="DEBUG")
            
            # Skip if in ignore set or already decided
            if seq_text in ctx.ignore_set or seq_text in self.decided_sequences_text:
                if seq_text in ctx.ignore_set:
                    log_message(f"Skipping ignored sequence '{seq_text}' (found in ignore_set)", level="DEBUG")
                else:
                    log_message(f"Skipping already decided sequence '{seq_text}'", level="DEBUG")
                self.current_match_index += 1
                continue
            
            # Found a sequence to process
            span = match.span()
            self.current_caps_sequence = seq_text
            self.current_caps_span = span
            
            log_message(f"Processing sequence '{seq_text}' at span {span}", level="DEBUG")
            
            # Highlight the sequence directly
            start, end = span
            self._apply_highlighting(start, end, seq_text)
            
            # Display choice options
            if self.choice_display_callback:
                choices = ["Yes (lowercase)", "No (keep uppercase)", "Add to Ignore", "Auto Lowercase"]
                self.choice_display_callback(seq_text, choices)
            
            # STOP HERE - wait for user input, don't continue processing
            return
    
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
        current_text = self.text_edit_widget.toPlainText()
        if start < 0 or end > len(current_text) or start >= end:
            log_message(f"Invalid highlight range: {start}-{end} (text length: {len(current_text)})")
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
            
            # Center the highlighted text in viewport after a small delay
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
    
    def handle_caps_choice(self, choice: str, ctx: 'BookfixContext') -> bool:
        """
        Handle user's choice for an all-caps sequence.
        
        Args:
            choice: User's choice ('y'/'yes', 'n'/'no', 'a'/'add', 'i'/'auto')
            ctx: BookfixContext to modify
            
        Returns:
            True if more sequences to process, False if complete
        """
        from ..logging import log_message
        
        log_message(f"[PATCH ACTIVE] handle_caps_choice() got choice={choice!r}", level="DEBUG")
        
        seq = self.current_caps_sequence
        if not seq:
            return False
        
        start_pos, end_pos = self.current_caps_span
        
        # Find the original span we're working on
        original_span = None
        for m in self.all_caps_matches_original:
            if m.group(0) == seq and m.span() not in self.lowercased_original_spans:
                original_span = m.span()
                break
        
        # Handle each choice
        if choice.lower() in ('y', 'yes', '0'):  # '0' for PyQt5 button index
            # YES: lowercase just this instance, record its span
            if self.text_update_callback:
                # Update text and notify GUI
                ctx.text = ctx.text[:start_pos] + seq.lower() + ctx.text[end_pos:]
                self.text_update_callback(ctx.text, preserve_highlighting=False)
            
            if original_span:
                self.lowercased_original_spans.add(original_span)
            self.decided_sequences_text.add(seq)
            
            # Bulk-lower all remaining instances of this sequence
            bulk_pattern = re.compile(rf'\b{re.escape(seq)}\b')
            ctx.text = bulk_pattern.sub(seq.lower(), ctx.text)
            
            if self.text_update_callback:
                self.text_update_callback(ctx.text, preserve_highlighting=False)
            
            log_message(f"Bulk-lowercased all remaining instances of '{seq}'")
        
        elif choice.lower() in ('n', 'no', '1'):  # '1' for PyQt5 button index
            # NO: leave uppercase, skip it for the rest of this session
            self.decided_sequences_text.add(seq)
        
        elif choice.lower() in ('a', 'add', '2'):  # '2' for PyQt5 button index
            # ADD TO IGNORE: persist and never prompt on this word again
            log_message(f"Adding '{seq}' to ignore list.", level="DEBUG")
            ctx.ignore_set.add(seq)
            self._save_caps_data_file(ctx)
            self.decided_sequences_text.add(seq)
        
        elif choice.lower() in ('i', 'auto', '3'):  # '3' for PyQt5 button index
            # AUTO LOWERCASE: persist, then bulk-lowercase EVERY instance now
            log_message(f"Adding '{seq}' to auto-lowercase list.", level="DEBUG")
            ctx.lowercase_set.add(seq)
            self._save_caps_data_file(ctx)
            
            # Bulk-lowercase all persisted sequences in the buffer
            for word in ctx.lowercase_set:
                pattern = re.compile(r'\b' + re.escape(word) + r'\b')
                ctx.text = pattern.sub(word.lower(), ctx.text)
            
            if self.text_update_callback:
                self.text_update_callback(ctx.text, preserve_highlighting=False)
            
            # Mark all original spans for this seq as done
            for m in self.all_caps_matches_original:
                if m.group(0) == seq:
                    self.lowercased_original_spans.add(m.span())
            self.decided_sequences_text.add(seq)
        
        else:
            log_message(f"Unknown choice '{choice}' in handle_caps_choice()", level="WARNING")
            return True
        
        # Move to next sequence
        self.current_match_index += 1
        log_message(f"Choice handled for '{seq}' → '{choice}'. Moving on.", level="DEBUG")
        
        self._process_next_sequence(ctx)
        return self.current_match_index < len(self.all_caps_matches_original)
    
    def _finish_processing(self, ctx: 'BookfixContext'):
        """Complete all-caps sequence processing."""
        from ..logging import log_message
        
        if self.status_callback:
            self.status_callback("Finished all-caps processing.")
        
        ctx.log_change('all_caps_processing',
                      f"Processed all-caps sequences interactively",
                      None, None)
        
        log_message("=== Exiting process_all_caps_sequences ===", level="DEBUG")
    
    def _save_caps_data_file(self, ctx: 'BookfixContext'):
        """Save caps data to the .data.txt file."""
        try:
            # Import here to avoid circular imports
            from ..datafile import save_caps_data_file
            save_caps_data_file(ctx.ignore_set, ctx.lowercase_set)
        except ImportError:
            # Fallback to inline implementation if datafile module not available
            from ..logging import log_message
            log_message("Warning: Could not import save_caps_data_file, changes not persisted", level="WARNING")


# Legacy function for backward compatibility
def process_all_caps_sequences_gui(ctx: 'BookfixContext') -> 'BookfixContext':
    """
    Legacy function for backward compatibility.
    
    Note: This requires GUI callbacks to be set up properly.
    """
    processor = AllCapsProcessor()
    return processor.process_all_caps_sequences(ctx)


def handle_caps_choice(choice: str, ctx: 'BookfixContext') -> None:
    """
    Legacy function for backward compatibility.
    
    Note: This is a simplified version that doesn't maintain processor state.
    """
    processor = AllCapsProcessor()
    processor.handle_caps_choice(choice, ctx)