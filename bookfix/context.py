"""
Context management for Bookfix processing.

This module defines the BookfixContext class which maintains state
throughout the text processing pipeline.
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class BookfixContext:
    """
    Context object that maintains state throughout the Bookfix processing pipeline.
    
    This class holds the text being processed and all configuration data
    loaded from the .data.txt file, as well as tracking changes made during processing.
    """
    
    # Text being processed
    text: str = ""
    original_text: str = ""
    
    # Configuration from .data.txt
    default_directory: Optional[str] = None
    choices: Dict[str, List[str]] = field(default_factory=dict)
    tagged_choices: Dict[str, List[Tuple[str, List[str]]]] = field(default_factory=dict)
    replacements: Dict[str, str] = field(default_factory=dict)
    periods: Dict[str, str] = field(default_factory=dict)
    upper_to_lower: List[str] = field(default_factory=list)
    cap_ignore: List[str] = field(default_factory=list)
    roman_ignore: List[str] = field(default_factory=list)
    
    # Processing state
    changes_log: List[Dict] = field(default_factory=list)
    current_file_path: Optional[str] = None
    
    def log_change(self, module: str, description: str, original: Optional[str], modified: Optional[str]):
        """Log a change made during processing."""
        change = {
            'module': module,
            'description': description,
            'original': original,
            'modified': modified,
            'timestamp': None  # Could add timestamp if needed
        }
        self.changes_log.append(change)
    
    def get_changes_summary(self) -> str:
        """Get a summary of all changes made."""
        if not self.changes_log:
            return "No changes made."
        
        summary = []
        for change in self.changes_log:
            summary.append(f"{change['module']}: {change['description']}")
        
        return "\n".join(summary)
    
    def reset_text(self, new_text: str):
        """Reset the context with new text."""
        self.text = new_text
        self.original_text = new_text
        self.changes_log.clear()
    
    def apply_replacement(self, old_text: str, new_text: str, module: str = "manual"):
        """Apply a text replacement and log it."""
        if old_text in self.text:
            self.text = self.text.replace(old_text, new_text)
            self.log_change(module, f"Replaced '{old_text}' with '{new_text}'", old_text, new_text)
            return True
        return False