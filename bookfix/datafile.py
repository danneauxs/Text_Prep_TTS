"""
Data file handling for Bookfix.

This module provides functionality for loading and saving configuration data
from the .data.txt file, including choices, replacements, and settings.
"""

import os
from pathlib import Path
from typing import TYPE_CHECKING, Set

if TYPE_CHECKING:
    from .context import BookfixContext


# Data file constants
DATA_FILE_NAME = ".data.txt"
CHOICE_SECTION_MARKER = "# CHOICE"
REPLACE_SECTION_MARKER = "# REPLACE"
PERIODS_SECTION_MARKER = "# PERIODS"
IGNORE_SECTION_MARKER = "# CAP_IGNORE"
LOWERCASE_SECTION_MARKER = "# UPPER_TO_LOWER"
ROMAN_IGNORE_SECTION_MARKER = "# ROMAN_IGNORE"
DEFAULT_DIR_SECTION_MARKER = "# DEFAULT_FILE_DIR"

# List of all section markers to help identify the end of a section's content
ALL_SECTION_MARKERS = {
    CHOICE_SECTION_MARKER,
    REPLACE_SECTION_MARKER,
    PERIODS_SECTION_MARKER,
    IGNORE_SECTION_MARKER,
    LOWERCASE_SECTION_MARKER,
    ROMAN_IGNORE_SECTION_MARKER,
    DEFAULT_DIR_SECTION_MARKER
}


def load_data_file(ctx: 'BookfixContext' = None) -> 'BookfixContext':
    """
    Loads all data (choices, replacements, periods, ignore, lowercase, default dir)
    by manually parsing the .data.txt file based on # SECTION markers.
    
    Args:
        ctx: Optional BookfixContext to populate, creates new one if None
        
    Returns:
        BookfixContext populated with data from .data.txt file
    """
    from .context import BookfixContext
    from .logging import log_message
    
    if ctx is None:
        ctx = BookfixContext()

    # Reset all data
    ctx.choices = {}
    ctx.replacements = {}
    ctx.periods = set()
    ctx.ignore_set = set()
    ctx.lowercase_set = set()
    ctx.roman_ignore_set = set()
    ctx.default_file_directory = None

    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level since we're in the bookfix/ subdirectory
    parent_dir = os.path.dirname(script_dir)
    data_file_path = os.path.join(parent_dir, DATA_FILE_NAME)

    log_message(f"Attempting to load data file: {data_file_path}")

    if os.path.exists(data_file_path):
        try:
            with open(data_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            current_section = None
            log_message("DEBUG: Starting data file parsing line by line.")
            
            for i, line in enumerate(lines):
                stripped_line = line.strip()
                # strip out any leading BOM / ZERO‑WIDTH chars
                stripped_line = stripped_line.lstrip('\ufeff\u200b\u00A0')
                log_message(f"DEBUG: Line {i+1}: '{stripped_line}'")

                # Check if the line is a known section marker
                if stripped_line in ALL_SECTION_MARKERS:
                    log_message(f"DEBUG: Found section marker: {stripped_line}")
                    if stripped_line == CHOICE_SECTION_MARKER:
                        current_section = 'choice'
                    elif stripped_line == REPLACE_SECTION_MARKER:
                        current_section = 'replace'
                    elif stripped_line == PERIODS_SECTION_MARKER:
                        current_section = 'periods'
                    elif stripped_line == IGNORE_SECTION_MARKER:
                        current_section = 'ignore'
                    elif stripped_line == LOWERCASE_SECTION_MARKER:
                        current_section = 'lowercase'
                    elif stripped_line == ROMAN_IGNORE_SECTION_MARKER:
                        current_section = 'roman_ignore'
                    elif stripped_line == DEFAULT_DIR_SECTION_MARKER:
                         current_section = 'default_dir'
                    continue

                # If we are in a section and the line is not empty and not a comment, process it
                if current_section and stripped_line and not stripped_line.startswith('#'):
                    log_message(f"DEBUG: Processing content for section '{current_section}': '{stripped_line}'")
                    
                    if current_section == 'choice':
                        parts = stripped_line.split('->')
                        if len(parts) == 2:
                            word, options = parts
                            ctx.choices[word.strip()] = [opt.strip() for opt in options.split(';')]
                            log_message(f"DEBUG: Added choice: '{word.strip()}' -> {ctx.choices[word.strip()]}")
                        else:
                            log_message(f"DEBUG: Skipping malformed choice line: '{stripped_line}'", level="WARNING")
                    
                    elif current_section == 'replace':
                        parts = stripped_line.split('->')
                        if len(parts) == 2:
                            old, new = parts
                            ctx.replacements[old.strip()] = new.strip()
                            log_message(f"DEBUG: Added replacement: '{old.strip()}' -> '{new.strip()}'")
                        else:
                            log_message(f"DEBUG: Skipping malformed replacement line: '{stripped_line}'", level="WARNING")
                    
                    elif current_section == 'periods':
                        ctx.periods.add(stripped_line)
                        log_message(f"DEBUG: Added period abbr: '{stripped_line}'")
                    
                    elif current_section == 'ignore':
                        ctx.ignore_set.add(stripped_line)
                        log_message(f"DEBUG: Added ignore sequence: '{stripped_line}'")
                    
                    elif current_section == 'lowercase':
                        ctx.lowercase_set.add(stripped_line)
                        log_message(f"DEBUG: Added lowercase sequence: '{stripped_line}'")
                    
                    elif current_section == 'roman_ignore':
                        ctx.roman_ignore_set.add(stripped_line.upper())
                        log_message(f"DEBUG: Added roman ignore sequence: '{stripped_line.upper()}'")
                    
                    elif current_section == 'default_dir':
                         if ctx.default_file_directory is None:
                              potential_path = Path(stripped_line).expanduser()
                              if potential_path.is_dir():
                                   ctx.default_file_directory = potential_path
                                   log_message(f"DEBUG: Loaded default directory: '{ctx.default_file_directory}'")
                              else:
                                   log_message(f"DEBUG: Invalid default directory path in file: '{stripped_line}'", level="WARNING")

                elif current_section and stripped_line.startswith('#'):
                     log_message(f"DEBUG: Skipping comment line within section '{current_section}': '{stripped_line}'")
                elif current_section and not stripped_line:
                     log_message(f"DEBUG: Skipping empty line within section '{current_section}'")

            log_message("DEBUG: Finished data file parsing.")
            log_message(f"Loaded {len(ctx.choices)} choice rules, {len(ctx.replacements)} replacement rules, {len(ctx.periods)} period rules.")
            log_message(f"Loaded {len(ctx.ignore_set)} ignore sequences, {len(ctx.lowercase_set)} automatic lowercase sequences, {len(ctx.roman_ignore_set)} roman ignore sequences.")
            
            if ctx.default_file_directory:
                 log_message(f"Loaded default file directory: {ctx.default_file_directory}")
            else:
                 log_message("No valid default file directory found in .data.txt.")

        except Exception as e:
            log_message(f"Error loading data file '{data_file_path}': {e}. Starting with empty rules.", level="ERROR")
            # Ensure sets/dicts are empty in case of error
            ctx.choices = {}
            ctx.replacements = {}
            ctx.periods = set()
            ctx.ignore_set = set()
            ctx.lowercase_set = set()
            ctx.default_file_directory = None

    else:
        log_message(f"Data file '{DATA_FILE_NAME}' not found. Starting with empty rules.", level="WARNING")

    log_message(f"DEBUG: load_data_file complete.  ignore_set={ctx.ignore_set}", level="DEBUG")
    return ctx


def save_default_directory_to_data_file(directory_path: str):
    """
    Saves the given directory path to the # DEFAULT_FILE_DIR section in .data.txt.
    
    Args:
        directory_path: Path to save as default directory
    """
    from .logging import log_message
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    data_file_path = os.path.join(parent_dir, DATA_FILE_NAME)

    log_message(f"Attempting to save default directory '{directory_path}' to data file: {data_file_path}")

    original_lines = []
    if os.path.exists(data_file_path):
        try:
            with open(data_file_path, 'r', encoding='utf-8') as f:
                original_lines = f.readlines()
        except Exception as e:
            log_message(f"Warning: Could not read existing data file '{data_file_path}' for saving default directory: {e}. Will attempt to create/overwrite only the target section.", level="WARNING")
            original_lines = []

    # Find section boundaries
    section_indices = {}
    current_section_start_idx = -1
    current_section_name = None

    for i, line in enumerate(original_lines):
         stripped_line = line.strip()
         if stripped_line in ALL_SECTION_MARKERS:
              if current_section_name and current_section_start_idx != -1:
                   section_indices[current_section_name] = (current_section_start_idx, i)
              
              current_section_name = {
                   CHOICE_SECTION_MARKER: 'choice',
                   REPLACE_SECTION_MARKER: 'replace',
                   PERIODS_SECTION_MARKER: 'periods',
                   IGNORE_SECTION_MARKER: 'ignore',
                   LOWERCASE_SECTION_MARKER: 'lowercase',
                   DEFAULT_DIR_SECTION_MARKER: 'default_dir'
              }.get(stripped_line)
              current_section_start_idx = i + 1

    if current_section_name and current_section_start_idx != -1:
         section_indices[current_section_name] = (current_section_start_idx, len(original_lines))

    # Build new content
    new_default_dir_content_lines = [str(directory_path) + '\n']

    # Construct new file content
    new_lines = []
    i = 0
    default_dir_section_handled = False

    while i < len(original_lines):
        line = original_lines[i]
        stripped_line = line.strip()

        if stripped_line == DEFAULT_DIR_SECTION_MARKER and 'default_dir' in section_indices:
            start_idx, end_idx = section_indices['default_dir']
            new_lines.append(line)
            new_lines.extend(new_default_dir_content_lines)
            i = end_idx
            default_dir_section_handled = True
            continue

        new_lines.append(line)
        i += 1

    # Add section if it didn't exist
    if not default_dir_section_handled:
         if new_lines and new_lines[-1].strip() != '':
              new_lines.append('\n')
         new_lines.append(DEFAULT_DIR_SECTION_MARKER + '\n')
         new_lines.extend(new_default_dir_content_lines)

    try:
        Path(data_file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(data_file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        log_message(f"Default directory '{directory_path}' saved to '{DATA_FILE_NAME}'.")
    except Exception as e:
        log_message(f"Error saving default directory to data file '{data_file_path}': {e}", level="ERROR")


def save_caps_data_file(ignore_set: Set[str], lowercase_set: Set[str]):
    """
    Saves the current ignore and automatic lowercase sequences to the .data.txt file.
    
    Args:
        ignore_set: Set of sequences to ignore
        lowercase_set: Set of sequences to auto-lowercase
    """
    from .logging import log_message
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    data_file_path = os.path.join(parent_dir, DATA_FILE_NAME)

    log_message(f"Attempting to save CAP_IGNORE and UPPER_TO_LOWER sections to data file: {data_file_path}")

    original_lines = []
    if os.path.exists(data_file_path):
        try:
            with open(data_file_path, 'r', encoding='utf-8') as f:
                original_lines = f.readlines()
        except Exception as e:
            log_message(f"Warning: Could not read existing data file '{data_file_path}' for saving caps data: {e}. Overwriting only target sections.", level="WARNING")
            original_lines = []

    # Find section boundaries
    section_indices = {}
    current_section_start_idx = -1
    current_section_name = None

    for i, line in enumerate(original_lines):
         stripped_line = line.strip()
         stripped_line = stripped_line.lstrip('\ufeff\u200b\u00A0')

         if stripped_line in ALL_SECTION_MARKERS:
              if current_section_name and current_section_start_idx != -1:
                   section_indices[current_section_name] = (current_section_start_idx, i)
              
              current_section_name = {
                   CHOICE_SECTION_MARKER: 'choice',
                   REPLACE_SECTION_MARKER: 'replace',
                   PERIODS_SECTION_MARKER: 'periods',
                   IGNORE_SECTION_MARKER: 'ignore',
                   LOWERCASE_SECTION_MARKER: 'lowercase',
                   DEFAULT_DIR_SECTION_MARKER: 'default_dir'
              }.get(stripped_line)
              current_section_start_idx = i + 1

    if current_section_name and current_section_start_idx != -1:
         section_indices[current_section_name] = (current_section_start_idx, len(original_lines))

    # Build new content
    new_ignore_content_lines = [seq + '\n' for seq in sorted(list(ignore_set))]
    new_lowercase_content_lines = [seq + '\n' for seq in sorted(list(lowercase_set))]

    # Construct new file content
    new_lines = []
    i = 0
    ignore_section_handled = False
    lowercase_section_handled = False

    while i < len(original_lines):
        line = original_lines[i]
        stripped_line = line.strip()

        if stripped_line == IGNORE_SECTION_MARKER and 'ignore' in section_indices:
            start_idx, end_idx = section_indices['ignore']
            new_lines.append(line)
            new_lines.extend(new_ignore_content_lines)
            i = end_idx
            ignore_section_handled = True
            continue

        elif stripped_line == LOWERCASE_SECTION_MARKER and 'lowercase' in section_indices:
            start_idx, end_idx = section_indices['lowercase']
            new_lines.append(line)
            new_lines.extend(new_lowercase_content_lines)
            i = end_idx
            lowercase_section_handled = True
            continue

        new_lines.append(line)
        i += 1

    # Add sections if they didn't exist
    if not ignore_section_handled and ignore_set:
         if new_lines and new_lines[-1].strip() != '':
              new_lines.append('\n')
         new_lines.append(IGNORE_SECTION_MARKER + '\n')
         new_lines.extend(new_ignore_content_lines)

    if not lowercase_section_handled and lowercase_set:
         if new_lines and new_lines[-1].strip() != '':
              new_lines.append('\n')
         new_lines.append(LOWERCASE_SECTION_MARKER + '\n')
         new_lines.extend(new_lowercase_content_lines)

    try:
        Path(data_file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(data_file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        log_message(f"Data file '{DATA_FILE_NAME}' updated successfully (CAP_IGNORE, UPPER_TO_LOWER sections).")
    except Exception as e:
        log_message(f"Error saving data file '{data_file_path}' (CAP_IGNORE, UPPER_TO_LOWER sections): {e}", level="ERROR")