"""
Data file loading and parsing for Bookfix.

This module handles loading and parsing the .data.txt configuration file
which contains replacement rules, choice options, and other settings.
"""

import os
import re
from typing import Dict, List, Tuple, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .context import BookfixContext

from .logging import log_message


def load_data_file(ctx: 'BookfixContext' = None) -> 'BookfixContext':
    """
    Load and parse the .data.txt configuration file.
    
    Args:
        ctx: Existing BookfixContext to populate, or None to create new one
        
    Returns:
        BookfixContext with loaded configuration
    """
    from .context import BookfixContext
    
    if ctx is None:
        ctx = BookfixContext()
    
    # Find .data.txt file in current directory
    data_file_path = os.path.join(os.getcwd(), '.data.txt')
    
    if not os.path.exists(data_file_path):
        log_message(f"Data file not found: {data_file_path}", level="WARNING")
        return ctx
    
    log_message(f"Attempting to load data file: {data_file_path}")
    
    try:
        with open(data_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        _parse_data_file_lines(lines, ctx)
        
    except Exception as e:
        log_message(f"Error loading data file: {e}", level="ERROR")
    
    return ctx


def _parse_data_file_lines(lines: List[str], ctx: 'BookfixContext') -> None:
    """Parse the lines from the data file and populate the context."""
    
    log_message("DEBUG: Starting data file parsing line by line.")
    
    # Initialize context dictionaries
    ctx.choices = {}
    ctx.tagged_choices = {}
    ctx.replacements = {}
    ctx.periods = {}
    ctx.upper_to_lower = []
    ctx.cap_ignore = []
    ctx.roman_ignore = []
    
    current_section = None
    
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        
        log_message(f"DEBUG: Line {line_num}: '{line}'")
        
        # Skip empty lines
        if not line:
            if current_section:
                log_message(f"DEBUG: Skipping empty line within section '{current_section}'")
            continue
        
        # Check for section markers
        if line.startswith('#'):
            if line.startswith('# '):
                section_name = line[2:].strip()
                if section_name in ['DEFAULT_FILE_DIR', 'REPLACE', 'CHOICE', 'UPPER_TO_LOWER', 'CAP_IGNORE', 'ROMAN_IGNORE']:
                    current_section = section_name.lower()
                    log_message(f"DEBUG: Found section marker: {line}")
                    continue
            else:
                # Comment line within a section
                if current_section:
                    log_message(f"DEBUG: Skipping comment line within section '{current_section}': '{line}'")
                continue
        
        # Process content based on current section
        if current_section:
            log_message(f"DEBUG: Processing content for section '{current_section}': '{line}'")
            
            if current_section == 'default_file_dir':
                ctx.default_directory = line
                log_message(f"DEBUG: Loaded default directory: '{line}'")
                
            elif current_section == 'replace':
                _parse_replacement_line(line, ctx)
                
            elif current_section == 'choice':
                _parse_choice_line(line, ctx)
                
            elif current_section == 'upper_to_lower':
                ctx.upper_to_lower.append(line)
                log_message(f"DEBUG: Added upper_to_lower: '{line}'")
                
            elif current_section == 'cap_ignore':
                ctx.cap_ignore.append(line)
                log_message(f"DEBUG: Added cap_ignore: '{line}'")
                
            elif current_section == 'roman_ignore':
                ctx.roman_ignore.append(line)
                log_message(f"DEBUG: Added roman_ignore: '{line}'")
    
    log_message(f"Loaded {len(ctx.choices)} choice rules, {len(ctx.replacements)} replacement rules, {len(ctx.periods)} period rules.")


def _parse_replacement_line(line: str, ctx: 'BookfixContext') -> None:
    """Parse a replacement rule line."""
    if ' -> ' in line:
        parts = line.split(' -> ', 1)
        if len(parts) == 2:
            original, replacement = parts
            ctx.replacements[original] = replacement
            log_message(f"DEBUG: Added replacement: '{original}' -> '{replacement}'")
        else:
            log_message(f"WARNING: Malformed replacement line: '{line}'", level="WARNING")
    else:
        log_message(f"WARNING: DEBUG: Skipping malformed replacement line: '{line}'", level="WARNING")


def _parse_choice_line(line: str, ctx: 'BookfixContext') -> None:
    """Parse a choice rule line."""
    if ' -> ' in line:
        parts = line.split(' -> ', 1)
        if len(parts) == 2:
            word, options_str = parts
            
            # Check if this is tagged format (contains colons)
            if ':' in options_str:
                # Tagged format: word -> option1:tag1,tag2 ; option2:tag3,tag4
                tagged_options = []
                option_parts = options_str.split(' ; ')
                
                for option_part in option_parts:
                    if ':' in option_part:
                        spelling, tags_str = option_part.split(':', 1)
                        tags = [tag.strip() for tag in tags_str.split(',')]
                        tagged_options.append((spelling.strip(), tags))
                    else:
                        # No tags, just spelling
                        tagged_options.append((option_part.strip(), []))
                
                if tagged_options:
                    ctx.tagged_choices[word] = tagged_options
                    log_message(f"DEBUG: Added tagged choice: '{word}' -> {tagged_options}")
            else:
                # Simple format: word -> option1 ; option2
                raw_options = [opt.strip() for opt in options_str.split(' ; ')]
                if raw_options:
                    ctx.choices[word] = raw_options
                    log_message(f"DEBUG: Added choice: '{word}' -> {raw_options}")
        else:
            log_message(f"WARNING: Malformed choice line: '{line}'", level="WARNING")
    else:
        log_message(f"WARNING: Malformed choice line (no ->): '{line}'", level="WARNING")


def save_default_directory_to_data_file(directory: str) -> bool:
    """
    Save the default directory to the .data.txt file.
    
    Args:
        directory: Directory path to save
        
    Returns:
        True if saved successfully, False otherwise
    """
    data_file_path = os.path.join(os.getcwd(), '.data.txt')
    
    try:
        # Read existing file
        lines = []
        if os.path.exists(data_file_path):
            with open(data_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        
        # Find and update DEFAULT_FILE_DIR section
        updated = False
        in_default_section = False
        new_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            if stripped == '# DEFAULT_FILE_DIR':
                in_default_section = True
                new_lines.append(line)
                continue
            elif stripped.startswith('#') and in_default_section:
                # New section started
                in_default_section = False
                if not updated:
                    new_lines.append(f"{directory}\n")
                    updated = True
                new_lines.append(line)
                continue
            elif in_default_section and not stripped.startswith('#') and stripped:
                # Replace existing directory
                new_lines.append(f"{directory}\n")
                updated = True
                continue
            
            new_lines.append(line)
        
        # If no DEFAULT_FILE_DIR section exists, add it
        if not updated:
            new_lines.insert(0, f"# DEFAULT_FILE_DIR\n{directory}\n")
        
        # Write back to file
        with open(data_file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        
        log_message(f"Saved default directory to data file: {directory}")
        return True
        
    except Exception as e:
        log_message(f"Error saving default directory: {e}", level="ERROR")
        return False