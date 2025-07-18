#!/usr/bin/env python3

# --- bookfix.py ---
# This script provides a GUI tool to process text files (primarily ebooks in .txt, .html, .xhtml formats).
# It reads replacement rules and choices from a .data.txt file,
# allows the user to interactively make choices for specific words,
# applies automatic replacements and text cleaning (like removing pagination and converting Roman numerals),
# and saves the modified text to a new file.
# Added checkboxes to control processing steps, including integrated All-Caps Sequence Processing.
# Handles .data.txt manually for compatibility with # SECTION markers.
# Fixed SyntaxError related to global variable declaration.
# Corrected the main execution block to properly call the main GUI setup function.
# Fixed NameError for progress_bar and progress_label in process_choices.
# Fixed UnboundLocalError for all_matches_original in process_all_caps_sequences_gui by removing duplicated logic.
# Added a "Start Processing" button to initiate the workflow after GUI setup.
# Corrected processing order to match checkbox order.
# Fixed NameError for lowercased_spans_pass2 in handle_caps_choice.
# Reviewed interactive all-caps processing logic and keyboard binding.
# Added detailed logging to track execution flow in run_processing and individual steps.
# CORRECTED load_data_file parsing logic and added logging within it.
# Added logging around the run_processing call.
# Added file.flush() in log_message for immediate writing to log file.
# Implemented loading default directory from .data.txt and GUI prompt/save if not found.
# Added message boxes for prompting and confirming default directory selection.
# Last generated: 05-01-25 18:05

import tkinter as tk # Import the Tkinter library for creating the GUI
from tkinter import messagebox, filedialog, ttk # Import specific modules, including ttk
import os # Import the os module for interacting with the operating system (file paths, etc.)
import sys # Import the sys module for system-specific parameters and functions (like stderr)
from bs4 import BeautifulSoup # Import BeautifulSoup for parsing HTML/XML content
from tkinter.font import Font # Import Font for custom text styling in the GUI
from tkinter.ttk import Progressbar # Import Progressbar for showing processing progress
from tkinter import BooleanVar # Import BooleanVar for checkboxes
import datetime # Import datetime for timestamps in logs
from pathlib import Path # Use pathlib for easier path manipulation
import re # Import the regular expression module for text pattern matching
from dataclasses import dataclass, field
from typing import Dict, Set, List, Optional, Any


# --- Context Object for Processing State ---
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
    processor: callable
    description: str
    enabled: bool = True
    requires_interaction: bool = False


def create_processing_pipeline() -> List[ProcessingStep]:
    """Create the standard processing pipeline in the correct logical order."""
    return [
        ProcessingStep(
            name='automatic_replacements',
            processor=apply_automatic_replacements,
            description='Apply automatic find/replace rules',
            requires_interaction=False
        ),
        ProcessingStep(
            name='insert_periods',
            processor=insert_periods_into_abbreviations,
            description='Insert periods into abbreviations',
            requires_interaction=False
        ),
        ProcessingStep(
            name='remove_pagination',
            processor=remove_pagination,
            description='Remove pagination elements',
            requires_interaction=False
        ),
        ProcessingStep(
            name='roman_numerals',
            processor=convert_roman_numerals,
            description='Convert Roman numerals to Arabic',
            requires_interaction=False
        ),
        ProcessingStep(
            name='convert_lowercase',
            processor=convert_to_lowercase,
            description='Convert entire text to lowercase',
            requires_interaction=False
        ),
        ProcessingStep(
            name='remove_blank_lines',
            processor=remove_blank_lines,
            description='Remove blank lines',
            requires_interaction=False
        ),
        # Interactive steps handled separately after non-interactive pipeline
        ProcessingStep(
            name='interactive_choices',
            processor=lambda ctx: ctx,  # Will be handled separately
            description='Interactive word choices',
            requires_interaction=True
        ),
        ProcessingStep(
            name='all_caps_processing',
            processor=lambda ctx: ctx,  # Will be handled separately
            description='Process all-caps sequences',
            requires_interaction=True
        ),
        ProcessingStep(
            name='numbered_line_edit',
            processor=lambda ctx: ctx,  # Will be handled separately
            description='Edit lines with numbers',
            requires_interaction=True
        )
    ]


def run_processing_pipeline(ctx: BookfixContext, enabled_steps: Dict[str, bool], 
                          progress_callback=None) -> BookfixContext:
    """Run the processing pipeline with enabled steps."""
    pipeline = create_processing_pipeline()
    
    for i, step in enumerate(pipeline):
        if enabled_steps.get(step.name, False) and not step.requires_interaction:
            log_message(f"Starting {step.description}...")
            ctx = step.processor(ctx)
            
            # Update GUI with processed text
            update_text_area(ctx)
            
            if progress_callback:
                progress_callback(i + 1, len(pipeline), step.description)
    
    return ctx


# --- Global Variables (used across functions) ---
text_area = None
choice_frame = None
status_label = None
save_button = None
filepath = None
root = None
choice_var = None # Variable to signal choice handling completion
start_processing_button = None # New global variable for the start button
text = "" # Global variable to hold the text content
log_file_path = "bookfix_execution.log" # Path for the execution log file
matches = [] # List to hold match objects for the current word
enable_numbered_line_edit_var = None

# Global context object for maintaining state
global_ctx = None
# --- Numbered Line Editing Globals ---
current_numbered_idx = 0
numbered_lines = []  # [(lineno, orig_line, spans)]
numbered_edits = {}  # lineno: replacement_text


# Data loaded from .data.txt
choices = {} # Dictionary for interactive word choices (original bookfix)
replacements = {} # Dictionary for automatic replacements (original bookfix)
periods = set() # Set for abbreviations needing periods (original bookfix)
ignore_set = set() # Set for all-caps sequences to ignore (integrated caps.py)
lowercase_set = set() # Set for all-caps sequences to auto-lowercase (integrated caps.py)
roman_ignore_set = set() # Set for roman numerals to ignore during conversion
default_file_directory = None # New global variable for the default file dialog directory

# Variables for interactive all-caps processing
current_caps_sequence = None # The all-caps sequence text being processed
current_caps_span = None # The (start, end) span of the current all-caps sequence in the text list
all_caps_matches_original = [] # List of all original regex matches for all-caps sequences
cumulative_offset = 0 # Offset due to text modifications
decided_sequences_text = set() # Set to track sequence texts that have been decided upon (for skipping future occurrences in this run)
lowercased_original_spans = set() # Set to track original spans that were lowercased (Pass 1 or Pass 2 'y'/'i')


# Variables for original choice processing (declared globally here, used in process_choices)
progress_bar = None
progress_label = None

# Variables for controlling processing steps with checkboxes
process_choices_var = None # Original bookfix checkbox
apply_replacements_var = None # Original bookfix checkbox
insert_periods_var = None # Original bookfix checkbox
remove_pagination_var = None # Original bookfix checkbox
convert_roman_var = None # Original bookfix checkbox
convert_lowercase_var = None # Original bookfix checkbox
process_all_caps_var = None # New checkbox for all-caps processing
    # New checkbox variable for blank-line removal
remove_blank_lines_var = None

# --- Helper function for logging match data ---
def log_matches_state(location):
    """Logs the state of current_word, current_match, and matches to matches.txt."""
    print(f"DEBUG: Entering log_matches_state from location: {location}") # Added print statement
    global current_word, current_match, matches
    try:
        with open('matches.txt', 'a', encoding='utf-8') as f:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"--- Log Entry ({timestamp}) ---\n")
            f.write(f"Location: {location}\n")
            f.write(f"Current Word: '{current_word}'\n")
            f.write(f"Current Match Index: {current_match}\n")
            f.write(f"Total Matches Found: {len(matches)}\n")
            f.write("Matches Details:\n")
            if matches:
                for i, match in enumerate(matches):
                    # Safely get the matched text, handling potential issues
                    try:
                         matched_text = match.group(0)
                    except IndexError:
                         matched_text = "[Error getting match text]"
                         # You might also want to log this error to your main log_file_path
                         # log_message(f"Error getting match group(0) for match {i} at location {location}", level="WARNING")

                    f.write(f"  Match {i}: Span=({match.start()}, {match.end()}), Text='{matched_text}'\n")
            else:
                f.write("  No matches found.\n")
            f.write("---\n\n")
    except Exception as e:
        # You might also want to log this error to your main log_file_path
        # log_message(f"Error writing to matches.txt: {e}", level="ERROR")
        print(f"ERROR: Failed to write to matches.txt: {e}") # Added print for the error

# --- Applies defined upper to lower section of datafile before interactive ---
def apply_upper_to_lower(ctx: BookfixContext, upper_to_lower: Dict[str, str]) -> BookfixContext:
    """
    Apply uppercase to lowercase mappings to the text.
    upper_to_lower is a dict mapping UPPER → lower.
    We want to lowercase EVERY standalone occurrence of UPPER
    (even when it's part of a longer all‑caps phrase).
    """
    original_text = ctx.text
    replacements_made = 0
    
    for up, low in upper_to_lower.items():
        # Count occurrences before replacement
        pattern = re.compile(rf'\b{re.escape(up)}\b')
        matches = pattern.findall(ctx.text)
        replacements_made += len(matches)
        # \b ensures we replace whole words only
        ctx.text = pattern.sub(low, ctx.text)
    
    ctx.log_change('apply_upper_to_lower', 
                   f"Applied {len(upper_to_lower)} uppercase-to-lowercase rules, made {replacements_made} replacements",
                   len(original_text), len(ctx.text))
    
    return ctx


# ---- Center main window on screen ---
def center_window(win):
    """
    Centers the given Tk window on the screen.
    """
    win.update_idletasks()   # make sure winfo_width/height are up to date
    w = win.winfo_width()
    h = win.winfo_height()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = (sw // 2) - (w // 2)
    y = (sh // 2) - (h // 2)
    win.geometry(f"{w}x{h}+{x}+{y}")


# --- Logging Function ---
def log_message(message, level="INFO"):
    """Logs a timestamped message to stderr and a log file, flushing immediately."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}"
    print(log_entry, file=sys.stderr) # Print to stderr
    try:
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
            f.flush() # Explicitly flush the buffer to ensure immediate writing
    except Exception as e:
        print(f"Error writing to log file {log_file_path}: {e}", file=sys.stderr)


# --- Data File Handling (Manual Parsing) ---
DATA_FILE_NAME = ".data.txt"
CHOICE_SECTION_MARKER = "# CHOICE" # Corrected marker spacing based on user file
REPLACE_SECTION_MARKER = "# REPLACE" # Corrected marker spacing based on user file
PERIODS_SECTION_MARKER = "# PERIODS" # Corrected marker spacing based on user file
IGNORE_SECTION_MARKER = "# CAP_IGNORE" # From caps.py
LOWERCASE_SECTION_MARKER = "# UPPER_TO_LOWER" # From caps.py
ROMAN_IGNORE_SECTION_MARKER = "# ROMAN_IGNORE" # For roman numerals to ignore during conversion
DEFAULT_DIR_SECTION_MARKER = "# DEFAULT_FILE_DIR" # New marker for default directory

# List of all section markers to help identify the end of a section's content
ALL_SECTION_MARKERS = {
    CHOICE_SECTION_MARKER,
    REPLACE_SECTION_MARKER,
    PERIODS_SECTION_MARKER,
    IGNORE_SECTION_MARKER,
    LOWERCASE_SECTION_MARKER,
    ROMAN_IGNORE_SECTION_MARKER,
    DEFAULT_DIR_SECTION_MARKER # Include the new marker
}


def load_data_file(ctx: BookfixContext = None) -> BookfixContext:
    """
    Loads all data (choices, replacements, periods, ignore, lowercase, default dir)
    by manually parsing the .data.txt file based on # SECTION markers.
    Corrected parsing logic to stop collecting content only at the *next* section marker.
    """
    global default_file_directory  # Keep this global for GUI compatibility
    
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
    default_file_directory = None # Reset default directory on load

    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_file_path = os.path.join(script_dir, DATA_FILE_NAME)

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
                    elif stripped_line == DEFAULT_DIR_SECTION_MARKER: # Handle new section
                         current_section = 'default_dir'
                    continue # Skip to the next line after processing a marker

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
                        ctx.roman_ignore_set.add(stripped_line.upper())  # Store in uppercase for consistency
                        log_message(f"DEBUG: Added roman ignore sequence: '{stripped_line.upper()}'")
                    elif current_section == 'default_dir': # Process default directory line
                         # Take the first non-comment, non-empty line as the default directory
                         if ctx.default_file_directory is None: # Only set if not already set
                              potential_path = Path(stripped_line).expanduser()
                              if potential_path.is_dir():
                                   ctx.default_file_directory = potential_path
                                   default_file_directory = potential_path  # Keep global sync
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
            ctx.default_file_directory = None # Ensure this is also reset
            default_file_directory = None

    else:
        log_message(f"Data file '{DATA_FILE_NAME}' not found. Starting with empty rules.", level="WARNING")

    log_message(f"DEBUG: load_data_file complete.  ignore_set={ctx.ignore_set}", level="DEBUG")
    return ctx


def save_default_directory_to_data_file(directory_path):
    """
    Saves the given directory path to the # DEFAULT_FILE_DIR section in .data.txt.
    Reads the existing file, updates/creates the section, and writes back,
    preserving other sections and comments.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_file_path = os.path.join(script_dir, DATA_FILE_NAME)

    log_message(f"Attempting to save default directory '{directory_path}' to data file: {data_file_path}")

    original_lines = []
    if os.path.exists(data_file_path):
        try:
            with open(data_file_path, 'r', encoding='utf-8') as f:
                original_lines = f.readlines()
        except Exception as e:
            log_message(f"Warning: Could not read existing data file '{data_file_path}' for saving default directory: {e}. Will attempt to create/overwrite only the target section.", level="WARNING")
            original_lines = [] # Start with empty lines if reading fails

    # Find the start and end line indices for the content within the target section
    section_indices = {}
    current_section_start_idx = -1
    current_section_name = None

    for i, line in enumerate(original_lines):
         stripped_line = line.strip()
         # Check if the line is any known section marker
         if stripped_line in ALL_SECTION_MARKERS:
              # If we were in a section, mark its end
              if current_section_name and current_section_start_idx != -1:
                   section_indices[current_section_name] = (current_section_start_idx, i) # End is line *before* next marker
              # Start the new section
              current_section_name = {
                   CHOICE_SECTION_MARKER: 'choice',
                   REPLACE_SECTION_MARKER: 'replace',
                   PERIODS_SECTION_MARKER: 'periods',
                   IGNORE_SECTION_MARKER: 'ignore',
                   LOWERCASE_SECTION_MARKER: 'lowercase',
                   DEFAULT_DIR_SECTION_MARKER: 'default_dir'
              }.get(stripped_line)
              current_section_start_idx = i + 1 # Content starts on the line after the marker

    # After the loop, if we were in a section, its content ends at the end of the file
    if current_section_name and current_section_start_idx != -1:
         section_indices[current_section_name] = (current_section_start_idx, len(original_lines))


    # Build the new content lines for the default directory section
    new_default_dir_content_lines = [str(directory_path) + '\n'] # The path itself, followed by a newline

    # Construct the new list of lines by replacing the content within the default dir section
    new_lines = []
    i = 0
    default_dir_section_handled = False

    while i < len(original_lines):
        line = original_lines[i]
        stripped_line = line.strip()

        # Check if this line is the start of the default directory section
        if stripped_line == DEFAULT_DIR_SECTION_MARKER and 'default_dir' in section_indices:
            start_idx, end_idx = section_indices['default_dir']
            new_lines.append(line) # Keep the section marker line
            new_lines.extend(new_default_dir_content_lines) # Insert the new content
            i = end_idx # Jump past the old content lines
            default_dir_section_handled = True
            continue # Continue to the next line after the skipped block

        # If it's not the start of the default dir section, keep the original line
        new_lines.append(line)
        i += 1

    # If the default directory section didn't exist in the original file, append it
    if not default_dir_section_handled:
         # Add newline only if the file is not empty and the last line is not empty
         if new_lines and new_lines[-1].strip() != '':
              new_lines.append('\n')
         new_lines.append(DEFAULT_DIR_SECTION_MARKER + '\n')
         new_lines.extend(new_default_dir_content_lines)


    try:
        # If the file didn't exist, create its parent directories first
        Path(data_file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(data_file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        log_message(f"Default directory '{directory_path}' saved to '{DATA_FILE_NAME}'.")
    except Exception as e:
        log_message(f"Error saving default directory to data file '{data_file_path}': {e}", level="ERROR")


def save_caps_data_file(ignore_set, lowercase_set):
    """
    Saves the current ignore and automatic lowercase sequences to the .data.txt file.
    Reads the existing file, updates the specific sections, and writes back,
    preserving other sections and comments.
    Adjusted parsing logic to correctly find section boundaries.
    NOTE: This function only saves the CAP_IGNORE and UPPER_TO_LOWER sections.
    A more comprehensive save function handling all sections would be needed
    if other sections are modified by the GUI.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_file_path = os.path.join(script_dir, DATA_FILE_NAME)

    log_message(f"Attempting to save CAP_IGNORE and UPPER_TO_LOWER sections to data file: {data_file_path}")

    original_lines = []
    if os.path.exists(data_file_path):
        try:
            with open(data_file_path, 'r', encoding='utf-8') as f:
                original_lines = f.readlines()
        except Exception as e:
            log_message(f"Warning: Could not read existing data file '{data_file_path}' for saving caps data: {e}. Overwriting only target sections.", level="WARNING")
            original_lines = [] # Start with empty lines if reading fails

    # Find the start and end line indices for the content within the target sections
    # Content starts after the marker and ends before the next marker or end of file
    section_indices = {}
    current_section_start_idx = -1
    current_section_name = None

    for i, line in enumerate(original_lines):
         stripped_line = line.strip()
        # strip out any leading BOM / ZERO‑WIDTH chars
         stripped_line = stripped_line.lstrip('\ufeff\u200b\u00A0')

         # Check if the line is any known section marker
         if stripped_line in ALL_SECTION_MARKERS:
              # If we were in a section, mark its end
              if current_section_name and current_section_start_idx != -1:
                   section_indices[current_section_name] = (current_section_start_idx, i) # End is line *before* next marker
              # Start the new section
              current_section_name = {
                   CHOICE_SECTION_MARKER: 'choice',
                   REPLACE_SECTION_MARKER: 'replace',
                   PERIODS_SECTION_MARKER: 'periods',
                   IGNORE_SECTION_MARKER: 'ignore',
                   LOWERCASE_SECTION_MARKER: 'lowercase',
                   DEFAULT_DIR_SECTION_MARKER: 'default_dir'
              }.get(stripped_line)
              current_section_start_idx = i + 1 # Content starts on the line after the marker

    # After the loop, if we were in a section, its content ends at the end of the file
    if current_section_name and current_section_start_idx != -1:
         section_indices[current_section_name] = (current_section_start_idx, len(original_lines))


    # Build the new content lines for the sections we are saving (ignore and lowercase)
    new_ignore_content_lines = [seq + '\n' for seq in sorted(list(ignore_set))]
    new_lowercase_content_lines = [seq + '\n' for seq in sorted(list(lowercase_set))]

    # Construct the new list of lines by replacing the content within the found sections
    new_lines = []
    i = 0
    ignore_section_handled = False
    lowercase_section_handled = False

    while i < len(original_lines):
        line = original_lines[i]
        stripped_line = line.strip()

        # Check if this line is the start of a section we are replacing the content for
        if stripped_line == IGNORE_SECTION_MARKER and 'ignore' in section_indices:
            start_idx, end_idx = section_indices['ignore']
            new_lines.append(line) # Keep the section marker line
            new_lines.extend(new_ignore_content_lines) # Insert the new content
            i = end_idx # Jump past the old content lines
            ignore_section_handled = True
            continue # Continue to the next line after the skipped block

        elif stripped_line == LOWERCASE_SECTION_MARKER and 'lowercase' in section_indices:
            start_idx, end_idx = section_indices['lowercase']
            new_lines.append(line) # Keep the section marker line
            new_lines.extend(new_lowercase_content_lines) # Insert the new content
            i = end_idx # Jump past the old content lines
            lowercase_section_handled = True
            continue # Continue to the next line after the skipped block

        # If it's not the start of a section we are replacing, keep the original line
        new_lines.append(line)
        i += 1

    # If sections didn't exist in the original file but have content now, append them
    # Append only if the section wasn't found and handled in the original file
    if not ignore_section_handled and ignore_set:
         # Add newline only if last line is not empty
         if new_lines and new_lines[-1].strip() != '':
              new_lines.append('\n')
         new_lines.append(IGNORE_SECTION_MARKER + '\n')
         new_lines.extend(new_ignore_content_lines)

    if not lowercase_section_handled and lowercase_set:
         # Add newline only if last line is not empty
         if new_lines and new_lines[-1].strip() != '':
              new_lines.append('\n')
         new_lines.append(LOWERCASE_SECTION_MARKER + '\n')
         new_lines.extend(new_lowercase_content_lines)


    try:
        # If the file didn't exist, create its parent directories first
        Path(data_file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(data_file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        log_message(f"Data file '{DATA_FILE_NAME}' updated successfully (CAP_IGNORE, UPPER_TO_LOWER sections).")
    except Exception as e:
        log_message(f"Error saving data file '{data_file_path}' (CAP_IGNORE, UPPER_TO_LOWER sections): {e}", level="ERROR")


# --- File Selection Function ---
def select_file():
    """
    Opens a file dialog for the user to select an input text file.
    Uses the global default_file_directory for the initial directory.
    Includes settings to show hidden files.

    Returns:
        str or None: The full path to the selected file, or None if cancelled.
    """
    global default_file_directory # Need access to the global default

    log_message("Opening file selection dialog.")

    # Determine the initial directory based on the global default_file_directory
    initial_dir = default_file_directory if default_file_directory and default_file_directory.is_dir() else Path.home()
    log_message(f"Using initial directory for file dialog: {initial_dir}")


    # Define the types of files the dialog should display
    filetypes = [
        ("Text files", "*.txt"),
        ("HTML files", "*.html *.xhtml"),
        ("All files", "*.*")
    ]

    # --- Settings to control the hidden file display in the dialog ---
    # This Tk command forces the file dialog code to load, necessary for setvar to work reliably
    # 'catch' prevents the error from the badoption from stopping the script
    root.tk.eval('catch {tk_getOpenFile -badoption}')
    # This Tk command enables the "Show hidden files" checkbox in the dialog window
    root.tk.setvar('::tk::dialog::file::showHiddenBtn', 1)
    # This Tk command sets the initial state of the checkbox. 0 hides hidden files, 1 shows them.
    root.tk.setvar('::tk::dialog::file::showHiddenVar', 0)
    # --- End of hidden file settings ---


    # Open the file selection dialog
    selected_file = filedialog.askopenfilename(
        title="Select file to process", # Title of the dialog window
        filetypes=filetypes, # Filter the files shown
        initialdir=str(initial_dir) # Set the initial directory
    )

    # If a file was selected (the user didn't ancel)
    if selected_file:
        log_message(f"File selected: {selected_file}")
        # Change the current working directory to the directory of the selected file.
        # This is often useful if the script needs to access other files relative to the input file.
        os.chdir(os.path.dirname(selected_file))
        # Return the full path of the selected file
        return selected_file
    # If the user cancelled the dialog
    log_message("File selection cancelled.")
    return None

# --- Interactive Choice Processing Function (Original Bookfix) ---
# Modified process_choices function with logging
def process_choices(ctx: BookfixContext = None) -> BookfixContext:
    """
    Iterates through words loaded from the data file that require a choice.
    For each word found in the text, it highlights the match, presents buttons
    for the user to select the replacement, and updates the text accordingly.
    Includes a progress bar. Implemented re-searching after each replacement for accurate highlighting.
    Includes logging to matches.txt.
    """
    global text, current_word, current_match, matches, progress_bar, progress_label, choice_var
    
    # Use global context if none provided (for backward compatibility)
    if ctx is None:
        global global_ctx
        ctx = global_ctx
    
    # Clearing matches.txt is now handled in start_processing_button_command

    # Get the total number of unique words requiring choices to track progress
    total_words = len(ctx.choices)
    processed_words = 0 # Counter for words finished

    # Create and display the progress bar and label
    # Ensure they are not already packed from a previous run
    if progress_bar is None:
        progress_bar = Progressbar(root, orient=tk.HORIZONTAL, length=200, mode='determinate')
    progress_bar.pack(pady=5)

    if progress_label is None:
        progress_label = tk.Label(root, text="Progress: 0%")
    progress_label.pack(pady=5)


    # Clear the text area and load the current state of the text before starting choices
    # Ensure text_area contains the current context text content at the start
    text_area.delete("1.0", tk.END)
    text_area.insert("1.0", ctx.text)

    # Loop through each word that needs interactive replacement
    for word in ctx.choices.keys():
        current_word = word # Set the current word being processed
        current_match = 0 # Reset the match index for the new word

        # Find all occurrences of the current word in the *current* text.
        # This search happens once per word, at the start of processing that word.
        # The matches list will be updated dynamically within handle_choice.
        # Use re.finditer to find all matches and store them as a list
        # \b ensures whole word matching
        # re.escape handles special characters in the word
        # re.IGNORECASE makes the search case-insensitive
        matches[:] = list(re.finditer(r'\b' + re.escape(current_word) + r'\b', ctx.text, re.IGNORECASE))


        # Log initial matches state for the word
        log_matches_state(f"Start_of_word_{current_word}_in_process_choices")


        # If there are matches for the current word
        if matches:
            # Clear any existing buttons from the choice frame
            for widget in choice_frame.winfo_children():
                widget.destroy()

            # Create buttons for each option
            options = ctx.choices[current_word] # Get the list of options for the current word
            # Define a monospace font for consistent button text width
            mono_font = Font(family="Courier New", size=10, weight="bold")

            for i, option in enumerate(options):
                # Use lambda to pass the option value to handle_choice when the button is clicked
                button = tk.Button(choice_frame, text=option, command=lambda opt=option: handle_choice(opt, ctx), bg="blue", fg="white", font=mono_font)
                button.pack(side=tk.LEFT, padx=5)
                # Bind number keys (1-9) to the first 9 options
                if i < 9:
                     # Use lambda to pass the event and option value to handle_choice
                     root.bind(str(i + 1), lambda event, opt=option: handle_choice(opt, ctx))
                     root.bind(f'<KP_{i + 1}>', lambda event, opt=option: handle_choice(opt, ctx))
            root.update_idletasks()
            root.geometry(f"{root.winfo_reqwidth()}x{root.winfo_reqheight()}")


            # Start processing the matches for the current word.
            # Call highlight_current_match *once* before entering the loop to highlight the first match.
            # Subsequent highlighting is handled within handle_choice after each replacement.
            if matches: # Double check there are matches before highlighting
                 highlight_current_match()


            # Process each match for the current word interactively.
            # The loop continues as long as current_match is less than the *current* number of matches.
            # handle_choice increments current_match and updates the matches list dynamically.
            while current_match < len(matches):
                # Wait here until handle_choice signals completion by setting choice_var
                choice_var.set(0) # Reset choice_var before waiting
                root.wait_variable(choice_var)


            # After the while loop finishes (all matches for the word are processed or skipped)
            # Log final state for the word
            log_matches_state(f"End_of_word_{current_word}_in_process_choices")


            # Unbind number keys after completing a word's choices
            for i in range(1, 10):
                 root.unbind(str(i))
                 root.unbind(f'<KP_{i}>')


        # Update progress after processing all matches for a word (or skipping if no matches)
        processed_words += 1
        progress_percent = int((processed_words / total_words) * 100)
        progress_bar['value'] = progress_percent
        progress_label.config(text=f"Progress: {progress_percent}%")
        root.update_idletasks() # Update the GUI to show the progress change


    # Hide the progress bar and label once all words are processed
    progress_bar.pack_forget()
    progress_label.pack_forget()

    # Clear choice buttons after processing is complete
    for widget in choice_frame.winfo_children():
        widget.destroy()

    # Update the context with the final changes made
    ctx.text = text_area.get("1.0", tk.END).strip() # Ensure final text is synced
    text = ctx.text  # Keep global text in sync for GUI compatibility
    
    # Log the completion
    ctx.log_change('interactive_choices', 
                   f"Processed {processed_words} words with interactive choices",
                   None, None)

    status_label.config(text="Interactive choices processing complete.")
    return ctx


# --- Helper Functions for Original Choice Processing ---
def highlight_current_match():
    """Highlights the currently selected match in the text area."""
    global current_match, matches, text_area, current_word
    # Remove any existing highlight tags
    text_area.tag_remove("highlight", "1.0", tk.END)
    # Check if there are matches and the current index is valid
    if matches and current_match < len(matches):
        # Get the start and end indices (span) of the current match
        start, end = matches[current_match].span()
        # Add a highlight tag to the text area at the match's position
        # Tkinter text indices are like "line.column"
        text_area.tag_add("highlight", f"1.0+{start}c", f"1.0+{end}c")
        # Configure the appearance of the highlight tag
        text_area.tag_config("highlight", background="lightblue", foreground="black")
        # Scroll the text area to make the highlighted match visible
        text_area.see(f"1.0+{start}c")
        # Update the status label to show progress for the current word
        status_label.config(text=f"Replacing {current_word}: {current_match + 1}/{len(matches)}")
    else:
        # If no more matches for the current word, update status
        status_label.config(text=f"Finished {current_word}") # More specific status

# Modified handle_choice function (text management changed to match bookfixold.py)
def handle_choice(choice, ctx: BookfixContext = None):
    """
    Handles the user's selection of a replacement option.
    Modifies the context text string, updates the text area from the string,
    re-finds matches, logs it, and prepares for the next match or word.
    Includes logging to matches.txt.
    """
    global text_area, current_match, matches, choice_var, text, current_word
    
    # Use global context if none provided (for backward compatibility)
    if ctx is None:
        global global_ctx
        ctx = global_ctx


    # Log state before replacement
    log_matches_state("Before_handle_choice_replacement")


    # Check if there is a valid match to process at the current_match index
    if matches and current_match < len(matches):
        # Get the start and end indices (span) of the current match from the *current* matches list
        # These are relative to the context text string *before* this replacement is applied
        start, end = matches[current_match].span()

        # ─── "No‐change" check (improved) ───
        matched_sub = ctx.text[start:end]
        if choice.lower() == matched_sub.lower():
            # We want to skip *only* this one span, without altering `ctx.text`.
            # So remove it from the existing `matches` list and highlight what's next.

            # Remove the match at index current_match:
            matches.pop(current_match)

            # If there is another match at the same index, highlight it:
           # Now call highlight_current_match() so that Tkinter
        # will both re‐tag "wind" and update the status label:
            if current_match < len(matches):
                highlight_current_match()
            else:
                # no matches left for this word ⇒ clear highlight & update status
                text_area.tag_remove("highlight", "1.0", tk.END)
                status_label.config(text=f"Finished {current_word}")  # same text used inside highlight_current_match's else‐clause

            choice_var.set(choice_var.get() + 1)
            return
            # ─────────────────────────────────────

        # --- Perform the replacement in the context text string ---
        # Modify the context text string using slicing
        ctx.text = ctx.text[:start] + choice + ctx.text[end:] # Modified: Update context text string first
        text = ctx.text  # Keep global text in sync for GUI compatibility
        # --- End of context text string replacement ---

        # --- Update the text area from the modified context text string ---
        text_area.delete("1.0", tk.END) # Modified: Clear the entire text area
        text_area.insert("1.0", ctx.text) # Modified: Insert the entire updated text string
        # --- End of text area update ---


        # Log the replacement made to debug.txt (assuming debug.txt logging is desired)
        try:
            with open('debug.txt', 'a', encoding='utf-8') as debug_file:
                debug_file.write(f"{current_word} -> {choice}\n")
        except Exception as e:
            log_message(f"Error writing to debug.txt: {e}", level="ERROR")


         # Re-find *all* matches for the current word in the *updated* context text.
        matches[:] = list(re.finditer(r'\b' + re.escape(current_word) + r'\b', ctx.text, re.IGNORECASE))

        # Find the next match that starts at or after the just-replaced position
        next_index = 0
        for i, m in enumerate(matches):
            if m.start() >= end:
                next_index = i
                break
        else:
            next_index = len(matches)  # No more matches left

        current_match = next_index



        # Log state after re-finding matches and incrementing current_match
        log_matches_state("After_handle_choice_replacement_and_refind")

        # Explicitly update the GUI to ensure visual changes are processed before highlighting
        root.update_idletasks() # Added: Force GUI update


        # --- Handle highlighting and signaling ---
        # If there are more matches for the current word in the updated list, highlight the next one
        if current_match < len(matches):
            highlight_current_match() # Call highlight *after* updating matches and index


        # Signal that a choice has been processed. This releases the root.wait_variable in process_choices.
        # We increment choice_var to ensure the wait variable state changes, triggering the release.
        choice_var.set(choice_var.get() + 1)


    else:
        # If for some reason handle_choice was called without a valid match at the current index,
        # or if the last match was just processed and current_match is now equal to len(matches),
        # signal to move on. This condition is also hit after the last match is processed above.
        # Log state when no valid match is found or after processing the last match
        log_matches_state("End_of_matches_for_word_in_handle_choice")
        choice_var.set(choice_var.get() + 1) # Signal to move on


def handle_caps_choice(choice, ctx: BookfixContext = None):
    """
    Handles the user's selection for an all‑caps sequence (y/n/a/i).
    choice is one of: "y"/"yes", "n"/"no", "a"/"add", "i"/"auto"
    """
    global text, choice_var
    global current_caps_sequence, current_caps_span, text_area
    
    # Use global context if none provided (for backward compatibility)
    if ctx is None:
        global global_ctx
        ctx = global_ctx

    # 0) Sentinel to confirm we hit this patched function
    log_message(f"[PATCH ACTIVE] handle_caps_choice() got choice={choice!r}", level="DEBUG")

    seq = current_caps_sequence                     # e.g. "CHAPTER"
    start_pos, end_pos = current_caps_span          # widget offsets

    # 1) Find the original span we're working on
    original_span = None
    for m in ctx.all_caps_matches_original:
        if m.group(0) == seq and m.span() not in ctx.lowercased_original_spans:
            original_span = m.span()
            break

    # 2) Prepare the regex for whole‑word matching
    pattern = re.compile(r'\b' + re.escape(seq) + r'\b')

    # --- Handle each button ---
    if choice.lower() in ('y', 'yes'):
        # YES: lowercase just this instance, record its span
        text_area.delete(f"1.0+{start_pos}c", f"1.0+{end_pos}c")
        text_area.insert(f"1.0+{start_pos}c", seq.lower())
        ctx.text = text_area.get("1.0", tk.END).strip()
        text = ctx.text  # Keep global sync
        if original_span:
            ctx.lowercased_original_spans.add(original_span)
        ctx.decided_sequences_text.add(seq)
        
        # Bulk-lower all remaining instances of this sequence
        bulk_pattern = re.compile(rf'\b{re.escape(seq)}\b')
        ctx.text = bulk_pattern.sub(seq.lower(), ctx.text)
        text = ctx.text  # Keep global sync
        update_text_area(ctx)
        log_message(f"Bulk-lowercased all remaining instances of '{seq}'")

    elif choice.lower() in ('n', 'no'):
        # NO: leave uppercase, skip it for the rest of this session
        ctx.decided_sequences_text.add(seq)

    elif choice.lower() in ('a', 'add'):
        # ADD TO IGNORE: persist and never prompt on this word again
        log_message(f"Adding '{seq}' to ignore list.", level="DEBUG")
        ctx.ignore_set.add(seq)
        save_caps_data_file(ctx.ignore_set, ctx.lowercase_set)
        ctx.decided_sequences_text.add(seq)

    elif choice.lower() in ('i', 'auto'):
        # AUTO LOWERCASE: persist, then bulk‑lowercase EVERY instance now
        log_message(f"Adding '{seq}' to auto‑lowercase list.", level="DEBUG")
        ctx.lowercase_set.add(seq)
        save_caps_data_file(ctx.ignore_set, ctx.lowercase_set)

        # Bulk‑lowercase _all_ persisted sequences in the buffer
        for w in ctx.lowercase_set:
            p = re.compile(r'\b' + re.escape(w) + r'\b')
            ctx.text = p.sub(w.lower(), ctx.text)
        text = ctx.text  # Keep global sync
        update_text_area(ctx)

        # Mark all original spans for this seq as done
        for m in ctx.all_caps_matches_original:
            if m.group(0) == seq:
                ctx.lowercased_original_spans.add(m.span())
        ctx.decided_sequences_text.add(seq)

    else:
        log_message(f"Unknown choice '{choice}' in handle_caps_choice()", level="WARNING")
        return

    # 3) Advance to the next prompt
    choice_var.set(choice_var.get() + 1)
    log_message(f"Choice handled for '{seq}' → '{choice}'. Moving on.", level="DEBUG")



# --- All-Caps Sequence Processing Function (Integrated from caps.py) ---

# Updated all-caps sequence processing with inline comments and detailed logging

# Updated all-caps sequence processing with inline comments and detailed logging

def process_all_caps_sequences_gui(ctx: BookfixContext = None) -> BookfixContext:
    """
    Finds contiguous sequences of all-caps words (2+ letters),
    highlighting each in the GUI and prompting user choices.
    """
    global choice_var, current_caps_sequence, current_caps_span, text_area, status_label, choice_frame, \
           decided_sequences_text, lowercased_original_spans
    
    # Use global context if none provided (for backward compatibility)
    if ctx is None:
        global global_ctx
        ctx = global_ctx

    # Log entry
    log_message("=== Entering process_all_caps_sequences_gui ===", level="DEBUG")
    log_message(f"DEBUG: process sees ignore_set = {ctx.ignore_set}", level="DEBUG")

    # 1) Snapshot text for regex detection
    original_for_detection = ctx.text  # keep original for matching only
    log_message(f"Original text length: {len(original_for_detection)} chars", level="DEBUG")

    # 2) Compile regex (no newlines, uppercase & spaces only)
    sequence_pattern = re.compile(r"\b[A-Z](?:[A-Z ]*[A-Z])\b")
    log_message(f"Using sequence_pattern: {sequence_pattern.pattern}", level="DEBUG")

    # 3) Detect sequences in the original text
    ctx.all_caps_matches_original = list(sequence_pattern.finditer(original_for_detection))
    log_message(
        "All-caps sequences detected: " + ", ".join(m.group(0) for m in ctx.all_caps_matches_original),
        level="DEBUG"
    )

    # Initialize tracking sets
    ctx.decided_sequences_text = set()
    ctx.lowercased_original_spans = set()

    # 4) Pre-pass: auto-lowercase words from lowercase_set in the text buffer
    log_message("Pre-pass: applying lowercase_set auto-lowercasing", level="DEBUG")
    working_text = original_for_detection
    for w in ctx.lowercase_set:
        working_text = re.sub(rf'\b{re.escape(w)}\b', w.lower(), working_text)

    # Update the main text variable to include pre-pass changes
    ctx.text = working_text

    # Initialize the text area with the current text
    text_area.delete("1.0", tk.END)
    text_area.insert("1.0", ctx.text)
    log_message("Text area initialized with current text", level="DEBUG")

    # 5) Prepare the UI
    status_label.config(text="Processing All-Caps sequences...")
    root.update_idletasks()

    # Clear old buttons
    for widget in choice_frame.winfo_children():
        widget.destroy()
    log_message("Cleared old choice buttons", level="DEBUG")

    # Create choice buttons
    tk.Button(choice_frame, text="Yes (y)",    command=lambda: handle_caps_choice('y', ctx)).pack(side=tk.LEFT, padx=5)
    tk.Button(choice_frame, text="No (n)",     command=lambda: handle_caps_choice('n', ctx)).pack(side=tk.LEFT, padx=5)
    tk.Button(choice_frame, text="Add to Ignore (a)", command=lambda: handle_caps_choice('a', ctx)).pack(side=tk.LEFT, padx=5)
    tk.Button(choice_frame, text="Auto Lowercase (i)", command=lambda: handle_caps_choice('i', ctx)).pack(side=tk.LEFT, padx=5)

    # Resize window to fit buttons
    root.update_idletasks()
    root.geometry(f"{root.winfo_reqwidth()}x{root.winfo_reqheight()}")
    log_message("UI buttons created and window resized", level="DEBUG")

    # Bind keyboard shortcuts
    for key in ('y','n','a','i'):
        root.bind(key, lambda e, ch=key: handle_caps_choice(ch, ctx))
    log_message("Keyboard shortcuts bound", level="DEBUG")

    # 6) Interactive loop over each detected sequence
    for m in ctx.all_caps_matches_original:
        seq_text = m.group(0)
        log_message(f"DEBUG: Checking sequence '{seq_text}' against ignore_set: {ctx.ignore_set}", level="DEBUG")
        if seq_text in ctx.ignore_set:
            log_message(f"Skipping ignored sequence '{seq_text}' (found in ignore_set)", level="DEBUG")
            continue
        if seq_text in ctx.decided_sequences_text:
            continue


        # Prepare highlighting
        span = m.span()
        start, end = span
        current_caps_sequence = seq_text
        current_caps_span = (start, end)
        log_message(f"Highlighting sequence '{seq_text}' at span {span}", level="DEBUG")

        # Display current text (with any prior modifications) and highlight the span
        text_area.delete("1.0", tk.END)
        text_area.insert("1.0", ctx.text)
        text_area.tag_remove("highlight_caps", "1.0", tk.END)
        text_area.tag_add("highlight_caps", f"1.0+{start}c", f"1.0+{end}c")
        text_area.tag_config("highlight_caps", background="yellow", foreground="black")
        text_area.see(f"1.0+{start}c")
        root.update_idletasks()

        # Wait for user choice
        status_label.config(text=f"Processing: '{seq_text}'")
        choice_var.set(0)
        log_message(f"Waiting for user choice on '{seq_text}'", level="DEBUG")
        root.wait_variable(choice_var)
        log_message(f"User completed choice for '{seq_text}'", level="DEBUG")

    # 7) Cleanup after interactive pass
    for key in ('y','n','a','i'):
        root.unbind(key)
    for widget in choice_frame.winfo_children():
        widget.destroy()
    status_label.config(text="Finished all-caps processing.")
    root.update_idletasks()
    
    # Sync back to global text for GUI compatibility
    global text
    text = ctx.text
    
    # Log the completion
    ctx.log_change('all_caps_processing', 
                   f"Processed all-caps sequences interactively",
                   None, None)
    
    log_message("=== Exiting process_all_caps_sequences_gui ===", level="DEBUG")
    return ctx





# --- Automatic Text Processing Functions (Original Bookfix) ---
def apply_automatic_replacements(ctx: BookfixContext) -> BookfixContext:
    """Applies all find and replace rules loaded from the data file."""
    log_message("Starting automatic replacements.")
    original_text = ctx.text
    replacement_count = 0
    
    # Iterate through each old/new pair in the replacements dictionary
    for old, new in ctx.replacements.items():
        # Count replacements for logging
        before_count = ctx.text.count(old)
        # Replace all occurrences of 'old' with 'new' in the text
        ctx.text = ctx.text.replace(old, new)
        replacement_count += before_count
    
    ctx.log_change('automatic_replacements', 
                   f"Applied {len(ctx.replacements)} rules, made {replacement_count} replacements",
                   len(original_text), len(ctx.text))
    
    log_message("Finished automatic replacements.")
    return ctx


def insert_periods_into_abbreviations(ctx: BookfixContext) -> BookfixContext:
    """Inserts periods into specified abbreviations (e.g., 'Mr' -> 'M.r.')."""
    log_message("Starting inserting periods into abbreviations.")
    original_text = ctx.text
    replacements_made = 0
    
    # Iterate through each abbreviation that needs periods
    for abbr in ctx.periods:
        # Create a regex pattern to find the whole word abbreviation
        pattern = r'\b' + re.escape(abbr) + r'\b'
        # Create the replacement string with periods inserted between characters and at the end
        replacement = '.'.join(abbr) + '.'
        # Count matches before replacement
        matches = re.findall(pattern, ctx.text)
        replacements_made += len(matches)
        # Use re.sub to replace all matches of the pattern with the replacement string
        ctx.text = re.sub(pattern, replacement, ctx.text)
    
    ctx.log_change('insert_periods', 
                   f"Processed {len(ctx.periods)} abbreviations, made {replacements_made} insertions",
                   len(original_text), len(ctx.text))
    
    log_message("Finished inserting periods.")
    return ctx


def convert_to_lowercase(ctx: BookfixContext) -> BookfixContext:
    """Converts the entire text to lowercase."""
    log_message("Starting converting to lowercase.")
    original_text = ctx.text
    ctx.text = ctx.text.lower()
    
    ctx.log_change('convert_lowercase', 
                   "Converted entire text to lowercase",
                   len(original_text), len(ctx.text))
    
    log_message("Finished converting to lowercase.")
    return ctx


# --- Roman Numeral Conversion Functions ---


def convert_roman_numerals(ctx: BookfixContext) -> BookfixContext:
    """Convert Roman numerals to Arabic numbers with abbreviation protection."""
    log_message("Starting converting Roman numerals.", level="INFO")
    original_text = ctx.text
    conversions_made = 0

    # --- Clear or create the conversion log at the start of each run ---
    try:
        open('roman_conversions.log', 'w', encoding='utf-8').close()
    except Exception as e:
        log_message(f"Error clearing roman_conversions.log: {e}", level="ERROR")
    
    # Use raw string with single backslashes for word boundaries
    # Less restrictive: avoid roman numerals bracketed by symbols (like R&D, I.D., Ph.D., etc.)
    # Allow conversion of cases like "tallos IV" while protecting abbreviations
    roman_pattern = r"(?<![A-Za-z&.\-+:;/\\])\b([VXLCDM]|[MDCLXVI]{2,})\b(?![A-Za-z&.\-+:;/\\])"

    def _replace(m):
        nonlocal conversions_made
        # For the simpler pattern, the roman numeral is the entire match
        token = m.group(1) if m.lastindex and m.lastindex >= 1 else m.group(0)
        
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




def roman_to_arabic(roman):
    """
    Converts a single Roman numeral string to its Arabic integer equivalent.
    Returns None if the string is not a valid Roman numeral or is "I".
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


# --- Pagination Removal Function ---
def remove_pagination(ctx: BookfixContext) -> BookfixContext:
    """
    Attempts to remove pagination elements from the text based on file type.
    Uses BeautifulSoup for HTML/XHTML and simple line checks for TXT files.
    Logs removed elements to a debug file.
    """
    log_message("Starting removing pagination.")
    original_text = ctx.text
    pagination_log = [] # List to record what was removed

    try:
        # Check if the file is HTML or XHTML
        if ctx.filepath and ctx.filepath.lower().endswith((".xhtml", ".html")):
            soup = BeautifulSoup(ctx.text, 'xml') # Parse the text using BeautifulSoup's XML parser

            # Find elements commonly used for pagination based on class or ID
            page_number_elements = soup.find_all(class_=re.compile(r"page-number", re.IGNORECASE))
            page_number_elements.extend(soup.find_all(id=re.compile(r"page-number", re.IGNORECASE)))
            # Find <p> tags containing only digits (common for simple page numbers)
            page_number_elements.extend(soup.find_all(name=re.compile(r"p", re.IGNORECASE), string=re.compile(r"^\s*\d+\s*$", re.IGNORECASE)))

            # Iterate through found elements
            for element in page_number_elements:
                pagination_log.append(f"Removed: {element}") # Log the element
                element.decompose() # Remove the element from the soup

            ctx.text = str(soup) # Convert the modified soup back to a string
            # Remove any empty lines that might result from element removal
            lines = ctx.text.splitlines()
            filtered_lines = [line for line in lines if line.strip()]
            ctx.text = "\n".join(filtered_lines)

        # Check if the file is a plain text file
        elif ctx.filepath and ctx.filepath.lower().endswith(".txt"):
            lines = ctx.text.splitlines() # Split text into lines
            filtered_lines = [] # List for lines to keep
            # Iterate through each line
            for line in lines:
                # If the line contains only digits (potential page number)
                if line.strip().isdigit():
                    pagination_log.append(f"Removed: {line}") # Log the line
                    # Skip adding this line to filtered_lines (effectively removing it)
                else:
                    filtered_lines.append(line) # Keep lines that are not just digits
            ctx.text = "\n".join(filtered_lines) # Join filtered lines back

    except Exception as e:
        # Handle errors during pagination removal
        log_message(f"Error removing pagination: {e}", level="ERROR")
        messagebox.showerror("Error", f"Error removing pagination: {e}")

    # Save the log of removed pagination to a file
    try:
        with open("pagination_debug.txt", "w", encoding="utf-8") as log_file:
            log_file.write("\n".join(pagination_log))
        log_message("Pagination removal log saved to pagination_debug.txt.")
    except Exception as e:
        log_message(f"Error saving pagination debug log: {e}", level="ERROR")

    ctx.log_change('remove_pagination', 
                   f"Removed {len(pagination_log)} pagination elements",
                   len(original_text), len(ctx.text))

    log_message("Finished removing pagination.")
    return ctx

# --- Remove blank lines from doucment

def remove_blank_lines(ctx: BookfixContext) -> BookfixContext:
    """Removes blank lines (including lines with only whitespace) from the text content."""
    log_message("Removing blank lines...")
    original_text = ctx.text
    original_line_count = len(original_text.splitlines())
    
    # Split the text into lines
    lines = ctx.text.splitlines()
    # Filter out lines that are empty or contain only whitespace
    non_blank_lines = [line for line in lines if line.strip()]
    # Join the remaining lines back together with newline characters
    ctx.text = "\n".join(non_blank_lines)
    
    final_line_count = len(non_blank_lines)
    removed_lines = original_line_count - final_line_count
    
    ctx.log_change('remove_blank_lines', 
                   f"Removed {removed_lines} blank lines ({original_line_count} → {final_line_count} lines)",
                   len(original_text), len(ctx.text))
    
    log_message("Blank line removal complete.")
    return ctx

def find_numbered_lines(text):
    """
    Return a list of (lineno, line, match_spans) for lines with 3+ digit numbers.
    match_spans is a list of (start_idx, end_idx) for each match in the line.
    """
    lines = text.splitlines()
    numbered_lines = []
    number_pat = re.compile(r'\d{3,}')
    for idx, line in enumerate(lines):
        spans = [m.span() for m in number_pat.finditer(line)]
        if spans:
            numbered_lines.append((idx, line, spans))
    return numbered_lines

def start_numbered_line_edit():
    global numbered_lines, current_numbered_idx, numbered_edits
    numbered_lines = find_numbered_lines(text)
    current_numbered_idx = 0
    numbered_edits = {}
    if not numbered_lines:
        messagebox.showinfo("No Numbers", "No lines with 3+ digit numbers found.")
        return finish_numbered_line_edit()  # Just proceed if nothing found
    show_current_numbered_line()

def show_current_numbered_line():
    global current_numbered_idx, numbered_lines
    frame = choice_frame  # reuse your choice_frame as with process_choices
    for widget in frame.winfo_children():
        widget.destroy()
    lineno, line, spans = numbered_lines[current_numbered_idx]
    tk.Label(frame, text=f"Line {lineno+1}:").pack()
    entry = tk.Text(frame, height=6, width=100, wrap="word", font=("Courier New", 13))
    entry.pack()
    entry.insert("1.0", line)
    # Highlight all numbers in yellow
    for start, end in spans:
        entry.tag_add("num", f"1.0+{start}c", f"1.0+{end}c")
    entry.tag_config("num", background="yellow", foreground="black")
    if spans:
        entry.see(f"1.0+{spans[0][0]}c")


    def save_and_next():
        numbered_edits[lineno] = entry.get("1.0", "end-1c")
        go_next()

    def go_next():
        global current_numbered_idx
        if current_numbered_idx < len(numbered_lines)-1:
            current_numbered_idx += 1
            show_current_numbered_line()
        else:
            finish_numbered_line_edit()

    def go_prev():
        global current_numbered_idx
        if current_numbered_idx > 0:
            current_numbered_idx -= 1
            show_current_numbered_line()

    button_frame = tk.Frame(frame)
    button_frame.pack(pady=4)
    tk.Button(button_frame, text="Prev", command=go_prev).pack(side=tk.LEFT, padx=5)
    tk.Button(button_frame, text="Apply/Next", command=save_and_next).pack(side=tk.LEFT, padx=5)
    tk.Button(button_frame, text="Skip", command=go_next).pack(side=tk.LEFT, padx=5)
    message_label = tk.Label(frame, text="V: 5   X: 10   L: 50   C: 100   D: 500   M: 1000", fg="yellow")
    message_label.pack(pady=4)


def finish_numbered_line_edit():
    global text, numbered_edits, numbered_lines
    if not numbered_edits:
        # Nothing changed; just clean up and continue
        for widget in choice_frame.winfo_children():
            widget.destroy()
        status_label.config(text="Numbered line editing complete (no changes).")
        return
    lines = text.splitlines()
    for lineno, replacement in numbered_edits.items():
        lines[lineno] = replacement
    text = "\n".join(lines)
    update_text_area()
    for widget in choice_frame.winfo_children():
        widget.destroy()
    status_label.config(text="Numbered line editing complete.")
    display_save_button()





# --- Main Processing Workflow ---
def run_processing():
    """
    Manages the main text processing workflow based on checkbox states.
    Uses Context Object pattern for clean state management.
    """
    global text, choices, replacements, periods, \
           process_choices_var, apply_replacements_var, insert_periods_var, \
           remove_pagination_var, convert_roman_var, convert_lowercase_var, \
           process_all_caps_var, ignore_set, lowercase_set, roman_ignore_set, \
           lowercased_original_spans, decided_sequences_text # Keep globals for now during transition

    log_message("Starting run_processing with Context Object pattern.")

    # Create context object from current global state
    ctx = BookfixContext(
        text=text,
        filepath=filepath,
        choices=choices,
        replacements=replacements,
        periods=periods,
        ignore_set=ignore_set,
        lowercase_set=lowercase_set,
        roman_ignore_set=roman_ignore_set
    )
    
    # Initialize interactive processing state
    ctx.decided_sequences_text = set()
    ctx.lowercased_original_spans = set()
    log_message("Initialized BookfixContext for processing run.")


    # --- Processing Steps using Pipeline ---
    # Get enabled steps from checkboxes
    enabled_steps = {
        'automatic_replacements': apply_replacements_var.get(),
        'insert_periods': insert_periods_var.get(),
        'remove_pagination': remove_pagination_var.get(),
        'roman_numerals': convert_roman_var.get(),
        'convert_lowercase': convert_lowercase_var.get(),
        'remove_blank_lines': remove_blank_lines_var.get(),
        # Interactive steps handled separately
        'interactive_choices': process_choices_var.get(),
        'all_caps_processing': process_all_caps_var.get(),
        'numbered_line_edit': enable_numbered_line_edit_var.get()
    }
    
    # Progress callback to update GUI
    def progress_callback(current, total, description):
        update_status_label(f"Step {current}/{total}: {description}")
        root.update_idletasks()
    
    # Run non-interactive processing pipeline
    log_message("Starting non-interactive processing pipeline.")
    ctx = run_processing_pipeline(ctx, enabled_steps, progress_callback)
    
    # Update global text and GUI after pipeline
    text = ctx.text
    update_text_area()
    log_message("Non-interactive processing pipeline completed.")

    # Interactive Processing Steps (handled separately in logical order)
    
    # 1. Interactive Choices - After automatic processing, let user make word choices
    if enabled_steps['interactive_choices']:
        log_message("Checkbox 'Interactive Choices' is checked. Executing process_choices().")
        update_status_label("Starting interactive choices...")
        ctx = process_choices(ctx) # Handle interactive replacements based on choices
        # Sync back to global for GUI compatibility
        text = ctx.text
        log_message("process_choices() finished.")
    else:
        log_message("Checkbox 'Interactive Choices' is NOT checked. Skipping process_choices().")

    # 2. Process All-Caps Sequences - After other processing, handle caps interactively
    if enabled_steps['all_caps_processing']:
        log_message("Checkbox 'Process All-Caps Sequences' is checked.")

        # Pre-apply UPPER_TO_LOWER rules
        update_status_label("Applying auto-lowercase rules...")
        if ctx.lowercase_set:
            mapping = { word: word.lower() for word in ctx.lowercase_set }
            ctx = apply_upper_to_lower(ctx, mapping)
            text = ctx.text  # Sync to global for GUI
            update_text_area()
            log_message(f"Auto-lowercased {len(mapping)} words from lowercase_set: {mapping.keys()}")

        # Run interactive all-caps processing
        update_status_label("Starting all-caps interactive processing...")
        ctx = process_all_caps_sequences_gui(ctx)
        # Sync back to global for GUI compatibility
        text = ctx.text
        log_message("process_all_caps_sequences_gui() finished.")
    else:
        log_message("Checkbox 'Process All-Caps Sequences' is NOT checked. Skipping process_all_caps_sequences_gui().")

    # 3. Interactive Numbered Line Edit - Final manual editing step
    if enabled_steps['numbered_line_edit']:
        log_message("Checkbox 'Enable Numbered Line Edit' is checked. Starting interactive numbered line editor.")
        # TODO: Update numbered line editing to use context
        start_numbered_line_edit()
        # Sync back to context
        ctx.text = text
        log_message("Numbered line editing completed.")
    else:
        log_message("Checkbox 'Enable Numbered Line Edit' is NOT checked. Skipping numbered line edit.")




    # --- Final Processing Steps ---
    # Update global text with final processed result
    text = ctx.text
    update_text_area()
    
    # Display processing summary
    log_message("Processing Summary:")
    log_message(ctx.get_processing_summary())
    
    # Update the GUI display and status
    log_message("All processing steps completed.")
    update_status_label("Processing complete.")
    display_save_button() # Make the save button available
    log_message("run_processing finished with Context Object pattern.")


# Modified start_processing_button_command function (includes moved debug.txt clearing)
def start_processing_button_command():
    """
    Command to be executed when the 'Start Processing' button is clicked.
    Initiates the main text processing workflow and clears log files.
    """
    global start_processing_button, text_area, text, log_file_path # Added log_file_path needed for clearing
    print(f"DEBUG: Current working directory: {os.getcwd()}") # Added to show current directory
    log_message("Start Processing button clicked.")

    # Disable the start button while processing is running
    start_processing_button.config(state=tk.DISABLED)
    log_message("Start Processing button disabled.")

    # Clear the text area and load the current state of the text before starting processing
    # This ensures we start with the text loaded after file selection, not a potentially old state
    # The 'text' global variable holds the content loaded from the file initially.
    # Processing functions will modify this 'text' variable.
    text_area.delete("1.0", tk.END)
    text_area.insert("1.0", text)
    log_message("Text area cleared and re-populated with initial text.")

    # Clear the execution log file at the start of a new run
    try:
        with open(log_file_path, "w", encoding="utf-8") as f:
            f.write(f"--- New Execution Start: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        log_message(f"Cleared previous log file: {log_file_path}")
    except Exception as e:
        log_message(f"Error clearing log file {log_file_path}: {e}", level="ERROR")

    # Clear the debug.txt file at the start of processing a new file
    # MOVED from __main__ block
    try:
        open('debug.txt', 'w').close()
        log_message("Cleared debug.txt file.")
    except Exception as e:
        log_message(f"Error clearing debug.txt file: {e}", level="ERROR")

    # Added: Clear the matches.txt file at the start of processing
    try:
        open('matches.txt', 'w', encoding='utf-8').close()
        log_message("Cleared matches.txt log file.")
    except Exception as e:
        log_message(f"Error clearing matches.txt log file: {e}", level="ERROR")


    log_message("Calling run_processing().")
    # Assuming run_processing calls process_choices if the checkbox is checked
    run_processing() # Call the main processing function
    log_message("Returned from run_processing().")


    # Re-enable the start button after processing
    start_processing_button.config(state=tk.NORMAL)
    log_message("Start Processing button re-enabled.")

# --- GUI Update Functions ---
def update_text_area(ctx: BookfixContext = None):
    """Refreshes the main text area with the current content of the 'text' variable or context."""
    global text, text_area # Need global text_area here
    log_message("Updating text area with current text variable content.")
    text_area.delete("1.0", tk.END) # Clear existing content
    
    # Use context text if provided, otherwise use global text
    display_text = ctx.text if ctx else text
    text_area.insert("1.0", display_text) # Insert the current text

def update_status_label(message):
    """Updates the status label with a given message."""
    global status_label # Need global status_label here
    log_message(f"Updating status label: {message}")
    status_label.config(text=message)

def save_file():
    """Saves the final processed text to a new file."""
    global text, filepath

    log_message("Save button clicked. Attempting to save file.")

    # Construct the output filename based on the original file name, adding "_output"
    base_name = os.path.basename(filepath) # Get filename from the full path
    file_stem = os.path.splitext(base_name)[0] # Get the filename without extension
    output_filename = file_stem + "_output.txt" # Append "_output" and set extension to .txt

    # Construct the full output file path in the current working directory (which was set in select_file)
    output_filepath = os.path.join(os.getcwd(), output_filename)
    log_message(f"Saving output to: {output_filepath}")

    try:
        # Open the output file for writing (overwriting if it exists)
        with open(output_filepath, "w", encoding="utf-8") as output_file:
            output_file.write(text) # Write the processed text to the file
        # Show a success message box
        log_message("File saved successfully.")
        messagebox.showinfo("Info", f"Output saved to {output_filepath}")
    except Exception as e:
        # Show an error message box if saving fails
        log_message(f"Error saving output file: {e}", level="ERROR")
        messagebox.showerror("Error", f"Error saving output: {e}")

def display_save_button():
    """Makes the Save button visible and forces the window to expand."""
    # Show the Save button alongside Start/Quit
    save_button.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

    # Flush any pending layout changes
    save_button.master.update_idletasks()

    # Resize the root window to fit all widgets
    root.geometry(f"{root.winfo_reqwidth()}x{root.winfo_reqheight()}")




# --- Program Exit Function ---
def quit_program():
    """Exits the program cleanly."""
    global root
    log_message("Quitting program.")
    # Check if the root window exists and destroy it if it does
    if 'root' in globals() and root:
        root.destroy()
    # Force exit the script
    os._exit(0)

# --- Main Application Entry Point ---
# This ensures the main() function is called when the script is executed directly
if __name__ == "__main__":
    # Create the main Tkinter window. This MUST happen before any calls that use 'root'.
    root = tk.Tk()
    root.title("Bookfix GUI") # Set the window title

    log_message("Bookfix GUI application started.")

    # Load data from .data.txt first, which includes the default directory
    global_ctx = load_data_file()
    
    # Update global variables with loaded data
    choices = global_ctx.choices
    replacements = global_ctx.replacements
    periods = global_ctx.periods
    ignore_set = global_ctx.ignore_set
    lowercase_set = global_ctx.lowercase_set
    roman_ignore_set = global_ctx.roman_ignore_set
    
    log_message(f"DEBUG: Updated global ignore_set from loaded context: {ignore_set}", level="DEBUG")

    # Check if a default directory was loaded and is valid
    if default_file_directory is None or not default_file_directory.is_dir():
         log_message("No valid default file directory found. Prompting user to select one.")

         # --- Display message box before asking for directory ---
         messagebox.showinfo(
             "Set Default Directory",
             "A default start directory for the file dialog has not been set or is invalid.\n\n"
             "For best use, please select a default directory now.\n\n"
             "Your Calibre Library folder is best, OR a folder you keep your ebook text files.\n\n"
             "Click OK to select a directory."
         )
         # --- End message box ---

         # Prompt the user to select a default directory
         initial_prompt_dir = Path.home() # Start the directory dialog in the user's home
         selected_default_dir_path = filedialog.askdirectory(
              title="Select Default Directory for File Dialog",
              initialdir=str(initial_prompt_dir)
         )

         if selected_default_dir_path:
              # If user selected a directory, set it as the default and save it
              default_file_directory = Path(selected_default_dir_path).resolve()
              log_message(f"User selected default directory: {default_file_directory}")
              save_default_directory_to_data_file(default_file_directory) # Save the selected path

              # --- Display confirmation message box ---
              messagebox.showinfo(
                  "Default Directory Set",
                  f"Default directory set to:\n{default_file_directory}\n\n"
                  "Click OK to proceed to file selection."
              )
              # --- End confirmation message box ---

         else:
              # If user cancelled the default directory selection, exit
              log_message("Default directory selection cancelled. Exiting.", level="INFO")
              quit_program() # Exit gracefully


    # Now that default_file_directory is established (either loaded or selected),
    # proceed to file selection using this default.
    filepath = select_file()

    # Check if a file was successfully selected (user didn't cancel)
    if filepath:
        # If a file was selected, set up the rest of the main GUI elements

        # Read the content of the selected file immediately after selection
        try:
            with open(filepath, "r", encoding="utf-8") as file:
                text = file.read()
            log_message(f"Successfully read file: {filepath}")
        except Exception as e:
            log_message(f"Error reading file '{filepath}': {e}", level="ERROR")
            messagebox.showerror("File Read Error", f"Error reading file '{filepath}': {e}")
            # Exit or return to file selection if reading fails
            quit_program() # Or implement a 'Load New File' option
            sys.exit(1) # Exit script


        # Initialize BooleanVars for processing steps (pre-checked by default)
        process_choices_var = BooleanVar(value=True)
        apply_replacements_var = BooleanVar(value=True)
        insert_periods_var = BooleanVar(value=False) # Keep as True even if function is commented
        remove_pagination_var = BooleanVar(value=True)
        convert_roman_var = BooleanVar(value=True)
        convert_lowercase_var = BooleanVar(value=False)
        process_all_caps_var = BooleanVar(value=True) # New checkbox variable
        remove_blank_lines_var = BooleanVar(value=True)
        enable_numbered_line_edit_var = BooleanVar(value=True)


        # Frame to hold the processing step checkboxes
        processing_options_frame = ttk.LabelFrame(root, text="Processing Steps", padding="10")
        processing_options_frame.pack(pady=10, padx=10, fill=tk.X)

        # Create and pack the checkboxes
        ttk.Checkbutton(processing_options_frame, text="Interactive Choices", variable=process_choices_var).grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Checkbutton(processing_options_frame, text="Apply Automatic Replacements", variable=apply_replacements_var).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Checkbutton(processing_options_frame, text="Insert Periods into Abbreviations", variable=insert_periods_var).grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        ttk.Checkbutton(processing_options_frame, text="Remove Pagination", variable=remove_pagination_var).grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Checkbutton(processing_options_frame, text="Convert Roman Numerals", variable=convert_roman_var).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Checkbutton(processing_options_frame, text="Convert to Lowercase", variable=convert_lowercase_var).grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
        ttk.Checkbutton(processing_options_frame, text="Process All-Caps Sequences (Last)", variable=process_all_caps_var).grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Checkbutton(processing_options_frame, text="Enable Numbered Line Edit (numbers.txt)", variable=enable_numbered_line_edit_var).grid(row=2, column=2, sticky=tk.W, padx=5, pady=2)
        ttk.Checkbutton(processing_options_frame, text="Remove Blank Lines", variable=remove_blank_lines_var).grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)

        # Configure columns to expand evenly
        processing_options_frame.columnconfigure(0, weight=1)
        processing_options_frame.columnconfigure(1, weight=1)
        processing_options_frame.columnconfigure(2, weight=1)


        # Text area to display and show highlighted text
        text_area = tk.Text(root, wrap=tk.WORD, width=80, height=20)
        text_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        # Display initial text content
        update_text_area()


        # Label to display current status messages
        status_label = tk.Label(root, text="File loaded. Select options and click 'Start Processing'.")
        status_label.pack(pady=5)

        # Frame to hold replacement choice buttons (used during interactive steps)
        choice_frame = tk.Frame(root)
        choice_frame.pack(pady=10)

        # Frame to hold main action buttons (Start, Save, Quit)
        button_frame = tk.Frame(root)
        button_frame.pack(pady=5, fill=tk.X, expand=True)

        # New Start Processing button
        start_processing_button = tk.Button(button_frame, text="Start Processing", command=start_processing_button_command)
        start_processing_button.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)


        # Save button (initially hidden, displayed after processing)
        save_button = tk.Button(button_frame, text="Save", command=save_file)
        # save_button.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True) # Don't pack here, display_save_button does this later

        # An empty frame used as a spacer to push Save and Quit buttons apart
        empty_frame = tk.Frame(button_frame)
        empty_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Quit button
        quit_button = tk.Button(button_frame, text="Quit", command=quit_program)
        quit_button.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # Tkinter variable used to signal when an interactive choice has been handled
        choice_var = tk.IntVar()


        # Start the Tkinter event loop. This makes the GUI interactive.
        # The processing workflow will be triggered by the 'Start Processing' button click.
        log_message("Starting Tkinter main loop.")
        center_window(root)
        root.mainloop()

    else:
        # If no file was selected in the dialog (after default dir is established)
        log_message("No file selected after default directory established. Exiting.", level="INFO") # Use stderr
        # Destroy the root window that was created (it's an empty window if mainloop wasn't called)
        # Check if root exists before destroying
        if 'root' in globals() and root:
             root.destroy()
        # Exit the script immediately
        sys.exit(0) # Use sys.exit for clean exit
