"""
Context and state management for Bookfix.

This module contains the BookfixContext dataclass and related types
that manage the state throughout the processing pipeline.
"""

import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Set, List, Optional, Any, Callable


@dataclass
class BookfixContext:
    """Central state object to replace global variables."""
    text: str = ""
    filepath: Optional[str] = None

    # Configuration data
    choices: Dict[str, List[str]] = field(default_factory=dict)
    replacements: Dict[str, str] = field(default_factory=dict)
    periods: Set[str] = field(default_factory=set)
    ignore_set: Set[str] = field(default_factory=set)
    lowercase_set: Set[str] = field(default_factory=set)
    roman_ignore_set: Set[str] = field(default_factory=set)
    default_file_directory: Optional[Path] = None

    # Processing state
    processing_log: List[Dict[str, Any]] = field(default_factory=list)
    changes_made: List[str] = field(default_factory=list)

    # Interactive processing state
    current_word: Optional[str] = None
    current_match: int = 0
    matches: List[Any] = field(default_factory=list)

    # All-caps processing state
    current_caps_sequence: Optional[str] = None
    current_caps_span: Optional[tuple] = None
    all_caps_matches_original: List[Any] = field(default_factory=list)
    cumulative_offset: int = 0
    decided_sequences_text: Set[str] = field(default_factory=set)
    lowercased_original_spans: Set[tuple] = field(default_factory=set)

    # Numbered line editing state
    current_numbered_idx: int = 0
    numbered_lines: List[tuple] = field(default_factory=list)
    numbered_edits: Dict[int, str] = field(default_factory=dict)

    def log_change(self, step: str, description: str, before_length: int = None, after_length: int = None):
        """Log a processing step change."""
        self.processing_log.append({
            'step': step,
            'description': description,
            'before_length': before_length or len(self.text),
            'after_length': after_length or len(self.text),
            'timestamp': datetime.datetime.now()
        })
        self.changes_made.append(f"{step}: {description}")

    def get_processing_summary(self) -> str:
        """Get a summary of all processing steps performed."""
        if not self.processing_log:
            return "No processing steps completed."

        summary = "Processing Summary:\n"
        for i, log_entry in enumerate(self.processing_log, 1):
            summary += f"{i}. {log_entry['step']}: {log_entry['description']}\n"
        return summary


@dataclass
class ProcessingStep:
    """Represents a single processing step in the pipeline."""
    name: str
    processor: Callable
    description: str
    enabled: bool = True
    requires_interaction: bool = False