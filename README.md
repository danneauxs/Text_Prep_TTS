# Bookfix - Ebook Text Processing Tool

A modular PyQt5-based application for interactive ebook text processing and cleanup. Bookfix provides automated text processing with interactive decision-making for ambiguous cases.

## Features

- **Interactive Word Choices** - Select from predefined replacement options for specific words
- **All-Caps Sequence Processing** - Decide whether to lowercase or keep uppercase sequences  
- **Numbered Line Editing** - Manual editing of lines containing 3+ digit numbers
- **Automatic Text Processing** - Find/replace rules, pagination removal, Roman numeral conversion
- **Real-time Highlighting** - Visual feedback with automatic scrolling to highlighted text
- **Modular Architecture** - Independent processors with no cross-module interference

## Installation

### Requirements
- Python 3.7+
- PyQt5
- BeautifulSoup4 (optional, for HTML processing)

### Setup
```bash
pip install PyQt5 beautifulsoup4
python main.py
```

## Usage

1. **Launch Application**
   ```bash
   python main.py
   ```

2. **Select File** - Browse and load a text file (.txt, .html, .xhtml)

3. **Configure Processing** - Enable/disable desired processing steps

4. **Start Processing** - Automated steps run first, followed by interactive steps

5. **Interactive Processing** - Make decisions for highlighted text sequences

6. **Save Output** - Export processed text to a new file

## Architecture

### Core Components

#### `main.py`
Application entry point with dependency checking and error handling.

#### `bookfix/gui.py` 
Main PyQt5 GUI interface providing:
- File selection and loading
- Processing step configuration
- Interactive panels for user decisions
- Text display with syntax highlighting
- Progress tracking and status updates

#### `bookfix/pipeline.py`
Processing pipeline orchestration:
- Defines processing order and dependencies
- Coordinates non-interactive and interactive steps
- Manages context passing between modules

#### `bookfix/context.py`
Central data structure (`BookfixContext`) containing:
- Current text state
- Processing configuration
- Word choice definitions
- Ignore lists and settings
- Change logging

#### `bookfix/datafile.py`
Configuration file management:
- Loads `.data.txt` configuration
- Manages ignore lists and replacement rules
- Handles default directory settings

#### `bookfix/logging.py`
Centralized logging system with file and console output.

### Interactive Processors

#### `bookfix/processors/choices.py`
**Interactive Word Choice Processor**
- Finds words requiring replacement decisions
- Highlights words in main text window
- Provides multiple choice options
- Updates text with user selections
- Independent text state management

**Key Features:**
- Real-time highlighting with context scrolling
- Keyboard shortcuts (1-9) for quick selection
- Fresh match finding in current text state
- Automatic viewport centering

#### `bookfix/processors/allcaps.py`
**All-Caps Sequence Processor**
- Detects sequences of capitalized words
- Excludes known acronyms and abbreviations
- Provides lowercase/uppercase/ignore options
- Bulk processing for repeated sequences

**Key Features:**
- Smart acronym detection
- Auto-lowercase for known sequences
- Visual highlighting with context
- Add-to-ignore functionality

#### `bookfix/processors/numbered.py`
**Numbered Line Editor**
- Finds lines containing 3+ digit numbers
- Provides line-by-line editing interface
- Highlights number sequences within lines
- Navigation controls (previous/next/skip)

**Key Features:**
- Side-panel editing interface
- Number highlighting within text
- Batch edit application
- Undo/skip functionality

### Non-Interactive Processors

#### `bookfix/processors/automatic_replacements.py`
**Automatic Find/Replace Engine**
- Applies regex-based replacement rules from `.data.txt`
- Supports word boundary matching
- Bulk text transformations
- Error handling for invalid regex patterns

#### `bookfix/processors/insert_periods.py`
**Abbreviation Period Insertion**
- Adds periods to common abbreviations (Mr → Mr.)
- Configurable abbreviation lists
- Word boundary aware processing

#### `bookfix/processors/remove_pagination.py`
**Pagination Element Removal**
- Removes page numbers and headers/footers
- Handles various pagination formats
- Preserves content structure
- Debug logging for removed elements

#### `bookfix/processors/roman_numerals.py`
**Roman Numeral Conversion**
- Converts Roman numerals to Arabic numbers (IV → 4)
- Supports standard and extended Roman numeral formats
- Context-aware conversion (avoids names, etc.)
- Comprehensive conversion logging

#### `bookfix/processors/convert_lowercase.py`
**Text Case Conversion**
- Optional full text lowercasing
- Preserves proper nouns when configured
- Bulk text transformation

#### `bookfix/processors/remove_blank_lines.py`
**Whitespace Cleanup**
- Removes empty lines and excess whitespace
- Normalizes line spacing
- Preserves intentional formatting

## Configuration

### `.data.txt` File Structure
```
[PROCESSING_OPTIONS]
automatic_replacements=true
interactive_choices=true
all_caps_processing=true

[IGNORE_SETS]
NASA,FBI,CIA,UK,USA

[CHOICES]
word1=option1,option2,option3
word2=optionA,optionB

[DEFAULT_DIRECTORY]
/path/to/ebooks
```

### Processing Order
1. **Automatic Replacements** - Apply find/replace rules
2. **Insert Periods** - Add periods to abbreviations  
3. **Remove Pagination** - Clean page numbers
4. **Roman Numerals** - Convert to Arabic numbers
5. **Convert Lowercase** - Optional case conversion
6. **Remove Blank Lines** - Whitespace cleanup
7. **Interactive Choices** - User word selections
8. **All-Caps Processing** - Capitalization decisions
9. **Numbered Line Edit** - Manual line editing

## Key Design Principles

### Module Independence
Each processor operates independently:
- Receives current text state fresh
- Finds matches in current text (no stale positions)
- Handles own highlighting and UI interaction
- Returns modified text to pipeline

### Text State Management
- Each module gets the current processed text
- No shared state between modules
- Position calculations always use current text
- Automatic text widget synchronization

### Interactive Highlighting
- Real-time visual feedback
- Automatic scrolling to highlighted content
- Context lines shown above highlighted text
- Consistent highlighting behavior across modules

## Development

### Adding New Processors

1. **Create processor file** in `bookfix/processors/`
2. **Inherit from base patterns** (see existing processors)
3. **Implement required methods:**
   - `process()` - main processing logic
   - `_apply_highlighting()` - for interactive processors
   - `_center_text_in_viewport()` - for text positioning
4. **Register in pipeline** (`bookfix/pipeline.py`)
5. **Add GUI integration** (`bookfix/gui.py`)

### Interactive Processor Template
```python
class NewInteractiveProcessor:
    def __init__(self):
        self.current_text: str = ""
        self.text_edit_widget = None  # Set by GUI
        
    def process(self, ctx: BookfixContext):
        self.current_text = ctx.text  # Always use current text
        # Find matches in current_text
        # Apply highlighting
        # Wait for user input
        
    def _apply_highlighting(self, start: int, end: int, word: str):
        # Standard highlighting implementation
        
    def _center_text_in_viewport(self, position: int):
        # Standard positioning implementation
```

## Troubleshooting

### Common Issues

**Highlighting not visible**
- Check text widget synchronization
- Verify position calculations use current text
- Ensure viewport scrolling is working

**Module interference**
- Verify modules use independent text state
- Check for shared highlighting state
- Ensure proper text widget updates

**Position mismatches**
- Confirm match finding uses current processed text
- Verify no stale position data between modules
- Check character count consistency

## License

[Add your license information here]

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes following the modular architecture
4. Test with various text files
5. Submit a pull request

## Support

For issues and feature requests, please create an issue in the repository.