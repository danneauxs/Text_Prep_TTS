"""
Interactive text choice processor for Bookfix.

This module provides functionality for interactive word choice processing,
where users can select from predefined replacement options for specific words.
"""

import re
import datetime
from typing import TYPE_CHECKING, List, Tuple, Optional, Callable, Any, Dict

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
        self.completion_callback: Optional[Callable[[], None]] = None  # Called when manual processing is complete
        self.text_edit_widget: Optional[Any] = None  # Direct access to text widget for highlighting
        
        # Phonetic processing - REMOVED (see phoneticreplacement.txt)
        # self.cmu_dict = None
        # self.g2p_model = None
        # self.phonetic_log: List[Dict] = []  # Log of automatic changes
    
    def reset_state(self):
        """Reset all processing state - called before processing new text."""
        self.current_word = None
        self.current_match = 0
        self.matches = []
        self.processed_words = 0
        self.total_words = 0
        self.current_text = ""
        # self.phonetic_log = []  # Removed with phonetic analysis
    
    def process_choices(self, ctx: 'BookfixContext', use_spacy_auto: bool = False) -> 'BookfixContext':
        """
        Main entry point for interactive choice processing.
        
        Args:
            ctx: BookfixContext containing text and choice definitions
            use_spacy_auto: Ignored (automatic processing removed)
            
        Returns:
            Updated BookfixContext after processing
        """
        from ..logging import log_message
        
        log_message("Starting interactive choice processing")
        
        # CRITICAL: Reset all state and start fresh with current text
        self.reset_state()
        self.current_text = ctx.text
        log_message(f"Choice processor received text with length: {len(ctx.text)}")
        
        # Clear matches and spacy log files in program directory
        try:
            import os
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            matches_path = os.path.join(script_dir, 'matches.txt')
            spacy_path = os.path.join(script_dir, 'spacy.txt')
            
            open(matches_path, 'w', encoding='utf-8').close()
            open(spacy_path, 'w', encoding='utf-8').close()
            log_message(f"Cleared log files in program directory: {script_dir}")
        except Exception as e:
            log_message(f"Error clearing log files: {e}", level="ERROR")
        
        self.total_words = len(ctx.choices)
        self.processed_words = 0
        
        if self.total_words == 0:
            if self.status_callback:
                self.status_callback("No words require interactive choices")
            return ctx
        
        # Start interactive processing first word
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
            # All manual words processed - now check if SpaCy processing should run
            ctx.log_change('interactive_choices',
                          f"Processed {self.total_words} words with interactive choices",
                          None, None)
            
            if self.status_callback:
                self.status_callback("Manual choices processing complete.")
            
            # Automatically trigger completion without requiring user interaction
            if self.completion_callback:
                self.completion_callback()
            
            # Signal that manual processing is done
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
    
    # PHONETIC ANALYSIS METHODS REMOVED - see phoneticreplacement.txt for details
    # These methods were unreliable and have been disabled
    
    def process_choices_with_phonetic_analysis_DISABLED(self, ctx: 'BookfixContext') -> 'BookfixContext':
        """
        Process tagged choices automatically using phonetic analysis for disambiguation.
        
        Args:
            ctx: BookfixContext containing text and tagged choice definitions
            
        Returns:
            Updated BookfixContext with automatic processing applied
        """
        from ..logging import log_message
        
        log_message("Starting phonetic automatic choice processing")
        
        # CRITICAL: Reset processing state and use fresh text from context
        # Manual processing may have changed the text, so we need to start fresh
        self.current_text = ctx.text  # Get the updated text after manual processing
        self.phonetic_log = []  # Clear any previous log entries
        
        log_message(f"Phonetic analysis received updated text with length: {len(self.current_text)}")
        
        # Test debug file creation in program directory and log text sample
        try:
            import os
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            phonetic_path = os.path.join(script_dir, 'phonetic.txt')
            with open(phonetic_path, 'a', encoding='utf-8') as f:
                f.write("=== Phonetic Processing Started ===\n")
                # Debug: Log first 500 chars of UPDATED text being processed
                f.write(f"UPDATED TEXT SAMPLE (first 500 chars): {self.current_text[:500]}\n")
                f.write("=" * 80 + "\n")
        except Exception as e:
            log_message(f"ERROR: Cannot create phonetic.txt: {e}", level="ERROR")
        
        # Load phonetic analysis models
        if not self._load_phonetic_models():
            # Fall back to interactive mode if phonetic analysis fails
            log_message("Phonetic analysis unavailable, falling back to interactive mode", level="WARNING")
            return ctx
        
        if self.status_callback:
            self.status_callback("Processing tagged choices automatically with phonetic analysis...")
        
        # Process tagged choices only
        if not hasattr(ctx, 'tagged_choices') or not ctx.tagged_choices:
            log_message("No tagged choices found for phonetic processing")
            return ctx
        
        # Process each tagged word automatically with fresh text
        processed_text = self.current_text  # Use the fresh text from manual processing
        tagged_words = list(ctx.tagged_choices.keys())
        
        log_message(f"Processing {len(tagged_words)} tagged words in fresh text")
        
        for word_idx, word in enumerate(tagged_words):
            tagged_options = ctx.tagged_choices[word]
            
            if self.progress_callback:
                progress = int((word_idx / len(tagged_words)) * 100)
                self.progress_callback(word_idx + 1, len(tagged_words), f"Phonetic processing: {word} ({progress}%)")
            
            # Find all matches for this word in the CURRENT processed text
            matches = list(re.finditer(r'\b' + re.escape(word) + r'\b', processed_text, re.IGNORECASE))
            
            log_message(f"Processing tagged word '{word}' with {len(matches)} matches")
            
            # Process each match in reverse order to maintain positions
            for match in reversed(matches):
                start, end = match.span()
                matched_text = processed_text[start:end]
                
                # Extract context from the CURRENT processed text (not old text)
                context_before, context_after = self._extract_context(processed_text, start, end, context_words=15)
                local_context = context_before + " " + matched_text + " " + context_after
                
                log_message(f"Analyzing match at position {start}-{end}: '{matched_text}' in local context: '{local_context[:100]}...'")
                
                # Use phonetic analysis to determine best replacement with tagged options
                best_choice = self._disambiguate_with_phonetics(matched_text, tagged_options, local_context)
                
                if best_choice and best_choice.lower() != matched_text.lower():
                    # Replace the text
                    processed_text = processed_text[:start] + best_choice + processed_text[end:]
                    
                    # Calculate length difference for position adjustment
                    length_diff = len(best_choice) - len(matched_text)
                    
                    # Log the change with final position (need to track this properly)
                    self.phonetic_log.append({
                        'original': matched_text,
                        'replacement': best_choice,
                        'context_before': context_before,
                        'context_after': context_after,
                        'position': start,  # This will be adjusted later
                        'length_diff': length_diff,
                        'options': [opt[0] for opt in tagged_options]  # Extract spellings for display
                    })
                    
                    log_message(f"Replaced '{matched_text}' with '{best_choice}' at position {start}")
        
        # Update context and display
        ctx.text = processed_text
        self.current_text = processed_text
        
        if self.text_update_callback:
            self.text_update_callback(ctx.text, preserve_highlighting=False)
        
        # Log completion
        ctx.log_change('phonetic_auto_choices',
                      f"Automatically processed {len(self.phonetic_log)} tagged word replacements using phonetic analysis",
                      None, None)
        
        if self.status_callback:
            self.status_callback(f"Phonetic processing complete. Made {len(self.phonetic_log)} automatic replacements.")
        
        log_message(f"Phonetic automatic processing complete. Made {len(self.phonetic_log)} replacements.")
        
        return ctx
    
    def _load_phonetic_models_DISABLED(self) -> bool:
        """Load CMU dictionary and g2p-en model if not already loaded."""
        if self.cmu_dict is not None and self.g2p_model is not None:
            return True
            
        try:
            import nltk
            from nltk.corpus import cmudict
            import g2p_en
            
            # Download CMU dictionary if needed
            try:
                nltk.data.find('corpora/cmudict')
            except LookupError:
                nltk.download('cmudict')
            
            self.cmu_dict = cmudict.dict()
            self.g2p_model = g2p_en.G2p()
            return True
            
        except ImportError as e:
            from ..logging import log_message
            log_message(f"Phonetic libraries not yet installed, using built-in analysis: {e}", level="WARNING")
            # Use built-in analysis without external libraries
            self.cmu_dict = "builtin"  # Flag for built-in mode
            self.g2p_model = "builtin"
            return True
        except Exception as e:
            from ..logging import log_message
            log_message(f"Error loading phonetic models, using built-in analysis: {e}", level="WARNING")
            # Use built-in analysis as fallback
            self.cmu_dict = "builtin"
            self.g2p_model = "builtin"
            return True
    
    def _extract_context(self, text: str, start: int, end: int, context_words: int = 10) -> Tuple[str, str]:
        """Extract context words before and after a match."""
        import re
        
        # Simple and reliable approach using regex word boundaries
        # Get text before the match
        text_before = text[:start]
        words_before = re.findall(r'\S+', text_before)  # All non-whitespace sequences
        context_before = " ".join(words_before[-context_words:]) if words_before else ""
        
        # Get text after the match  
        text_after = text[end:]
        words_after = re.findall(r'\S+', text_after)  # All non-whitespace sequences
        context_after = " ".join(words_after[:context_words]) if words_after else ""
        
        return context_before, context_after
    
    def _disambiguate_with_phonetics_DISABLED(self, word: str, tagged_options: List[Tuple[str, List[str]]], context: str) -> Optional[str]:
        """Use CMU dictionary and g2p-en to disambiguate word based on phonetic context."""
        if not self.cmu_dict or not self.g2p_model:
            return None
        
        try:
            from ..logging import log_message
            log_message(f"Phonetic analysis for '{word}' with context: '{context[:100]}...'")
            
            # Get pronunciations for each option
            option_pronunciations = {}
            for spelling, tags in tagged_options:
                pronunciations = self._get_pronunciations(spelling)
                option_pronunciations[spelling] = (pronunciations, tags)
                log_message(f"Option '{spelling}': {pronunciations}")
            
            # Analyze context for phonetic and semantic clues
            best_match = None
            best_score = 0
            
            # Simple context analysis for common homographs
            context_lower = context.lower()
            word_lower = word.lower()
            
            for spelling, (pronunciations, tags) in option_pronunciations.items():
                score = 0
                
                log_message(f"Evaluating option '{spelling}' with tags {tags}")
                
                # Context-based scoring for common patterns
                if word_lower == "read":
                    # Past tense indicators
                    past_indicators = ["had", "have", "has", "was", "were", "been", "did", "yesterday", "ago", "last", "already", "before"]
                    if any(indicator in context_lower for indicator in past_indicators):
                        if "past" in [tag.lower() for tag in tags]:
                            score += 15
                            log_message(f"  Past tense context match (+15)")
                    else:
                        # Present/infinitive indicators
                        present_indicators = ["to", "will", "can", "should", "must", "would", "could", "might"]
                        if any(indicator in context_lower for indicator in present_indicators) or "present" in [tag.lower() for tag in tags]:
                            if "present" in [tag.lower() for tag in tags] or "infinitive" in [tag.lower() for tag in tags]:
                                score += 15
                                log_message(f"  Present/infinitive context match (+15)")
                
                elif word_lower == "lead":
                    # Metal/noun indicators - expanded and improved
                    metal_indicators = ["pipe", "pipes", "box", "sheet", "weight", "bullet", "paint", "poisoning", "heavy", "metal", "make-up", "makeup", "pencil", "shot", "ammunition", "roof", "plumbing", "crystal", "glass", "gasoline", "fuel", "based", "-based", "free", "content", "level"]
                    # Verb indicators - more specific phrases
                    verb_indicators = ["to lead", "will lead", "can lead", "should lead", "must lead", "would lead", "could lead", "might lead", "does lead", "did lead", "leading", "leads to", "lead the", "lead a", "lead an"]
                    
                    # Check for metal context first (higher priority)
                    metal_found = any(indicator in context_lower for indicator in metal_indicators)
                    verb_found = any(indicator in context_lower for indicator in verb_indicators)
                    
                    if metal_found:
                        if "metal" in [tag.lower() for tag in tags] or "noun" in [tag.lower() for tag in tags]:
                            score += 20  # Higher score for metal context
                            log_message(f"  Metal/noun context match (+20)")
                    elif verb_found:
                        if "verb" in [tag.lower() for tag in tags]:
                            score += 15
                            log_message(f"  Verb context match (+15)")
                    else:
                        # Check if it's followed by typical metal-related words
                        lead_pattern = r'\blead\b\s*[-\s]*\w+'
                        import re
                        match = re.search(lead_pattern, context_lower)
                        if match:
                            following_word = match.group().split()[-1] if len(match.group().split()) > 1 else ""
                            metal_suffixes = ["based", "free", "paint", "shot", "pipe", "content", "level", "poisoning"]
                            if any(suffix in following_word for suffix in metal_suffixes):
                                if "metal" in [tag.lower() for tag in tags] or "noun" in [tag.lower() for tag in tags]:
                                    score += 18
                                    log_message(f"  Metal pattern match: '{following_word}' (+18)")
                
                elif word_lower == "tear":
                    # Crying indicators
                    cry_indicators = ["eye", "eyes", "cry", "crying", "sad", "weep", "cheek", "face", "emotion", "drop", "roll"]
                    if any(indicator in context_lower for indicator in cry_indicators):
                        if "crying" in [tag.lower() for tag in tags] or "noun" in [tag.lower() for tag in tags]:
                            score += 15
                            log_message(f"  Crying context match (+15)")
                    else:
                        # Ripping indicators  
                        rip_indicators = ["rip", "torn", "paper", "fabric", "cloth", "apart", "shred"]
                        if any(indicator in context_lower for indicator in rip_indicators):
                            if "rip" in [tag.lower() for tag in tags] or "verb" in [tag.lower() for tag in tags]:
                                score += 15
                                log_message(f"  Ripping context match (+15)")
                
                elif word_lower == "wind":
                    # Air/weather indicators
                    air_indicators = ["blow", "blowing", "breeze", "storm", "weather", "air", "gust", "strong", "feel"]
                    if any(indicator in context_lower for indicator in air_indicators):
                        if "air" in [tag.lower() for tag in tags] or "noun" in [tag.lower() for tag in tags]:
                            score += 15
                            log_message(f"  Air/weather context match (+15)")
                
                elif word_lower == "live":
                    # Verb indicators (to live)
                    verb_indicators = ["to", "will", "can", "want", "need", "going", "we", "you", "they", "survive", "exist"]
                    if any(indicator in context_lower for indicator in verb_indicators):
                        if "verb" in [tag.lower() for tag in tags] or "exist" in [tag.lower() for tag in tags]:
                            score += 15
                            log_message(f"  Verb context match (+15)")
                    else:
                        # Adjective indicators (live broadcast)
                        adj_indicators = ["broadcast", "show", "tv", "radio", "stream", "recording", "feed"]
                        if any(indicator in context_lower for indicator in adj_indicators):
                            if "broadcast" in [tag.lower() for tag in tags] or "adj" in [tag.lower() for tag in tags]:
                                score += 15
                                log_message(f"  Broadcast context match (+15)")
                
                # Default scoring if no specific patterns found
                if score == 0:
                    # Prefer first option as default
                    if spelling == tagged_options[0][0]:
                        score = 1
                        log_message(f"  Default first option (+1)")
                
                log_message(f"  Total score for '{spelling}': {score}")
                
                if score > best_score:
                    best_score = score
                    best_match = spelling
            
            # If no scoring worked, fall back to first option
            if best_match is None and tagged_options:
                best_match = tagged_options[0][0]
                log_message(f"No context matches, using default: {best_match}")
            
            log_message(f"Selected: {best_match} (score: {best_score})")
            
            # Write detailed analysis to phonetic.txt debug file
            self._write_phonetic_debug(word, context, tagged_options, best_match, best_score)
            
            return best_match
            
        except Exception as e:
            from ..logging import log_message
            log_message(f"Error in phonetic disambiguation: {e}", level="ERROR")
            return tagged_options[0][0] if tagged_options else None
    
    def _get_pronunciations(self, word: str) -> List[str]:
        """Get pronunciations for a word using CMU dictionary and g2p-en fallback."""
        pronunciations = []
        
        try:
            # Built-in mode - return simple phonetic approximation
            if self.cmu_dict == "builtin":
                return [f"[phonetic: {word.lower()}]"]
            
            # Try CMU dictionary first
            if word.lower() in self.cmu_dict:
                pronunciations = [' '.join(pron) for pron in self.cmu_dict[word.lower()]]
            
            # If not in CMU dict, use g2p-en for pronunciation generation
            if not pronunciations and self.g2p_model != "builtin":
                g2p_result = self.g2p_model(word)
                if g2p_result:
                    pronunciations = [' '.join(g2p_result)]
            
        except Exception as e:
            from ..logging import log_message
            log_message(f"Error getting pronunciations for '{word}': {e}", level="ERROR")
        
        return pronunciations if pronunciations else ["[unknown]"]
    
    def _write_phonetic_debug(self, word: str, context: str, tagged_options: List[Tuple[str, List[str]]], chosen: str, score: int):
        """Write detailed phonetic analysis to debug file."""
        try:
            import os
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            phonetic_path = os.path.join(script_dir, 'phonetic.txt')
            with open(phonetic_path, 'a', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write(f"WORD: {word}\n")
                f.write(f"CHOSEN: {chosen} (score: {score})\n")
                f.write(f"CONTEXT: {context[:150]}...\n")
                f.write("\n")
                
                f.write(f"PHONETIC ANALYSIS:\n")
                for spelling, tags in tagged_options:
                    pronunciations = self._get_pronunciations(spelling)
                    f.write(f"  {spelling}: {pronunciations} (tags: {', '.join(tags)})\n")
                f.write("\n")
                
                f.write(f"CONTEXT ANALYSIS:\n")
                context_lower = context.lower()
                word_lower = word.lower()
                
                if word_lower == "read":
                    past_indicators = ["had", "have", "has", "was", "were", "been", "did", "yesterday", "ago", "last", "already", "before"]
                    present_indicators = ["to", "will", "can", "should", "must", "would", "could", "might"]
                    found_past = [ind for ind in past_indicators if ind in context_lower]
                    found_present = [ind for ind in present_indicators if ind in context_lower]
                    f.write(f"  Past indicators found: {found_past}\n")
                    f.write(f"  Present indicators found: {found_present}\n")
                
                elif word_lower == "lead":
                    metal_indicators = ["pipe", "pipes", "box", "sheet", "weight", "bullet", "paint", "poisoning", "heavy", "metal", "make-up", "makeup", "pencil", "shot", "ammunition", "roof", "plumbing", "crystal", "glass", "gasoline", "fuel", "based", "-based", "free", "content", "level"]
                    verb_indicators = ["to lead", "will lead", "can lead", "should lead", "must lead", "would lead", "could lead", "might lead", "does lead", "did lead", "leading", "leads to", "lead the", "lead a", "lead an"]
                    found_metal = [ind for ind in metal_indicators if ind in context_lower]
                    found_verb = [ind for ind in verb_indicators if ind in context_lower]
                    f.write(f"  Metal indicators found: {found_metal}\n")
                    f.write(f"  Verb indicators found: {found_verb}\n")
                    
                    # Check for pattern matches
                    import re
                    lead_pattern = r'\blead\b\s*[-\s]*\w+'
                    match = re.search(lead_pattern, context_lower)
                    if match:
                        following_word = match.group().split()[-1] if len(match.group().split()) > 1 else ""
                        f.write(f"  Pattern found: '{match.group()}' -> following word: '{following_word}'\n")
                
                elif word_lower == "tear":
                    cry_indicators = ["eye", "eyes", "cry", "crying", "sad", "weep", "cheek", "face", "emotion", "drop", "roll"]
                    rip_indicators = ["rip", "torn", "paper", "fabric", "cloth", "apart", "shred"]
                    found_cry = [ind for ind in cry_indicators if ind in context_lower]
                    found_rip = [ind for ind in rip_indicators if ind in context_lower]
                    f.write(f"  Crying indicators found: {found_cry}\n")
                    f.write(f"  Ripping indicators found: {found_rip}\n")
                
                f.write("\n")
                
        except Exception as e:
            from ..logging import log_message
            log_message(f"Error writing phonetic debug file: {e}", level="ERROR")

    def get_phonetic_log_DISABLED(self) -> List[Dict]:
        """Get the log of phonetic automatic changes - DISABLED."""
        return []  # self.phonetic_log.copy()


# Legacy function for backward compatibility
def process_choices(ctx: 'BookfixContext') -> 'BookfixContext':
    """
    Legacy function for backward compatibility.
    
    Note: This requires GUI callbacks to be set up properly.
    """
    processor = InteractiveChoiceProcessor()
    return processor.process_choices(ctx)