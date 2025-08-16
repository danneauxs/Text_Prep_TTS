# Bookfix - Ebook Text Processing Tool v2.0

A modular PyQt5-based application for interactive ebook text processing and cleanup. Bookfix provides automated text processing with interactive decision-making for ambiguous cases, specifically designed for preparing ebooks for Text-to-Speech (TTS) systems.

## Features

- **Interactive Word Choices** - Select from predefined replacement options for homographs and ambiguous words
- **All-Caps Sequence Processing** - Decide whether to lowercase or keep uppercase sequences  
- **Numbered Line Editing** - Manual editing of lines containing 3+ digit numbers
- **Automatic Text Processing** - Find/replace rules, pagination removal, Roman numeral conversion
- **Real-time Highlighting** - Visual feedback with automatic scrolling to highlighted text
- **Modular Architecture** - Independent processors with no cross-module interference
- **Enhanced Unicode Support** - Handles curly quotes, special characters, and various text encodings

## Installation

### Requirements

- Python 3.7+
- PyQt5
- BeautifulSoup4 (optional, for HTML processing)

### Setup

#### Option 1: Quick Start

```bash
./run.sh
```

#### Option 2: Manual Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run application
python main.py
```

#### 

## Usage

### Quick Start

1. **Launch Application**: `./run.sh` or `python main.py`
2. **First run** will ask you to select a default folder for text files. Browse will then open always to this folder first. You can then browse anywhere on your system. It's assume this location will be your text library directory.
3. **Select File**: Browse and load a text file (.txt, .html, .xhtml)
4. **Configure Processing**: Enable/disable desired processing steps via checkboxes
5. **Start Processing**: Automated steps run first, followed by interactive steps
6. **Interactive Processing**: Make decisions for highlighted text sequences
7. **Save Output**: Export processed text to a new file

### Processing Steps

The application processes text in the following order:

1. **Automatic Replacements** - Apply find/replace rules from `.data.txt`
2. **All-Caps Processing** (Interactive) - Handle capitalized sequences
3. **Numbered Line Processing** (Interactive) - Edit lines with numbers
4. **Period Insertion** - Add periods to abbreviations
5. **Roman Numeral Conversion** - Convert Roman numerals to Arabic numbers
6. **Blank Line Removal** - Clean up excess whitespace
7. **Lowercase Conversion** - Optional full text lowercasing
8. **Pagination Removal** - Remove page numbers and headers/footers
9. **Interactive Choices** (Interactive) - User word selections for homographs

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

- Finds words requiring replacement decisions (homographs)
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

#### `bookfix/processors/automatic.py`

**Automatic Find/Replace Engine**

- Applies regex-based replacement rules from `.data.txt`
- Supports word boundary matching
- Bulk text transformations
- Error handling for invalid regex patterns
- Handles Unicode characters and special quotes

#### `bookfix/processors/periods.py`

**Abbreviation Period Insertion**

- Adds periods to common abbreviations (Mr → Mr.)
- Configurable abbreviation lists
- Word boundary aware processing

#### `bookfix/processors/pagination.py`

**Pagination Element Removal**

- Removes page numbers and headers/footers
- Handles various pagination formats
- Preserves content structure
- Debug logging for removed elements

#### `bookfix/processors/roman.py`

**Roman Numeral Conversion**

- Converts Roman numerals to Arabic numbers (IV → 4)
- Enhanced regex patterns for better accuracy
- Context-aware conversion (avoids names, etc.)
- Handles various apostrophe types and edge cases

#### `bookfix/processors/lowercase.py`

**Text Case Conversion**

- Optional full text lowercasing
- Preserves proper nouns when configured
- Bulk text transformation

#### `bookfix/processors/blanklines.py`

**Whitespace Cleanup**

- Removes empty lines and excess whitespace
- Normalizes line spacing
- Preserves intentional formatting

## Configuration

### `.data.txt` File Structure

The configuration file uses a simple format with sections marked by comments:

```
# DEFAULT_FILE_DIR
/path/to/your/ebooks

# REPLACE
Dr. -> Doctor
Mr. -> Mister
' -> '

# CHOICE
lead -> leed ; led
read -> reed ; red
live -> lyve ; liv
tear -> teer ; tair

# UPPER_TO_LOWER
NASA
FBI
CIA

# CAP_IGNORE
USA
UK
DVD
CD

# ROMAN_IGNORE
CD
LCD
DVD
```

### Section Descriptions

- **DEFAULT_FILE_DIR**: Starting directory for file browser
- **REPLACE**: Automatic find/replace rules (supports regex)
- **CHOICE**: Interactive word choices for homographs (word -> option1 ; option2)
- **UPPER_TO_LOWER**: Acronyms to convert to lowercase
- **CAP_IGNORE**: Acronyms to ignore in all-caps processing
- **ROMAN_IGNORE**: Words to ignore in Roman numeral processing

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

**Virtual environment issues**

- Delete and recreate venv after moving project directories
- Use `./run.sh` for automatic environment management

**Roman numeral false positives**

- Add problematic words to ROMAN_IGNORE section in `.data.txt`
- Enhanced regex patterns reduce false matches

## Text-to-Speech Optimization

Bookfix is specifically designed to prepare ebooks for TTS systems by:

- **Homograph Resolution**: Interactive choices for words with multiple pronunciations
- **Number Formatting**: Convert timestamps, dates, and large numbers to readable format
- **Roman Numeral Handling**: Convert "Henry IV" to "Henry 4" for proper pronunciation
- **Acronym Management**: Control whether acronyms are spelled out or pronounced as words
- **Punctuation Cleanup**: Handle curly quotes, em-dashes, and other special characters

See `TTS_GUIDE.md` for detailed TTS preparation guidelines.

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