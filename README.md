# Bookfix - Ebook Text Processing Tool

Bookfix is a comprehensive GUI-based text processing application designed specifically for cleaning and formatting ebook text files. It provides both automated and interactive tools to transform raw ebook text into polished, readable content.

## Features

### 🔧 **Text Processing Capabilities**

- **Interactive Word Choices** - Manually select replacements for specific words with keyboard shortcuts
- **Automatic Replacements** - Apply predefined find/replace rules from configuration
- **Pagination Removal** - Remove page numbers and pagination elements from HTML/TXT files
- **Roman Numeral Conversion** - Convert Roman numerals to Arabic numbers (II → 2, XIV → 14)
- **All-Caps Sequence Processing** - Interactive handling of uppercase sequences with auto-lowercase options
- **Abbreviation Protection** - Prevents conversion of common abbreviations (I.D., Ph.D., etc.)
- **Numbered Line Editing** - Manual editing interface for lines containing 3+ digit numbers
- **Blank Line Removal** - Clean up excessive whitespace and empty lines

### 📁 **File Support**

- **Input formats**: `.txt`, `.html`, `.xhtml`
- **Output format**: `.txt` (with `_output` suffix)
- **BeautifulSoup integration** for HTML/XHTML processing

### 🎛️ **User Interface**

- **Checkbox controls** for enabling/disabling processing steps
- **Real-time text preview** with syntax highlighting
- **Progress tracking** with visual progress bars
- **Keyboard shortcuts** for faster operation
- **Status updates** throughout processing

## Installation

### Requirements

- Python 3.6 or higher
- Required packages:
  - `tkinter` (usually included with Python)
  - `beautifulsoup4`

### Setup

```bash
# Install required package
pip install beautifulsoup4

# Run the program
python3 bookfix.py
```

### macOS Installation

```bash
# Check Python version
python3 --version

# Install dependencies
pip3 install beautifulsoup4

# If tkinter is missing (rare)
brew install python-tk

# Run
python3 bookfix.py
```

## Usage

### Quick Start

1. **Launch the application**
   ```bash
   python3 bookfix.py
   ```

2. **Set default directory** (first run only)
   - Select your ebook library or text files folder
   - This setting is saved for future use

3. **Select input file**
   - Choose a `.txt`, `.html`, or `.xhtml` file to process

4. **Configure processing options**
   - Check/uncheck desired processing steps
   - All options are enabled by default

5. **Start processing**
   - Click "Start Processing" button
   - Follow interactive prompts as needed

6. **Save results**
   - Click "Save" when processing is complete
   - Output saved as `filename_output.txt`

### Processing Steps

The program processes text in the following order:

1. **Apply Automatic Replacements** - Bulk find/replace operations
2. **Insert Periods into Abbreviations** - Add periods to specified abbreviations
3. **Remove Pagination** - Clean up page numbers and pagination elements
4. **Interactive Choices** - Manual word-by-word replacement decisions
5. **Process All-Caps Sequences** - Handle uppercase text interactively
6. **Convert Roman Numerals** - Transform Roman numerals to Arabic numbers
7. **Convert to Lowercase** - Optional full text lowercasing
8. **Remove Blank Lines** - Clean up excessive whitespace
9. **Numbered Line Editing** - Manual editing of lines with numbers

### Interactive Features

#### Word Choices
- Press number keys (1-9) to select replacement options
- View highlighted matches in context
- Progress tracking shows completion status

#### All-Caps Processing
- **Y/Yes** - Lowercase this instance and all remaining instances
- **N/No** - Keep uppercase, skip for this session
- **A/Add** - Add to ignore list permanently
- **I/Auto** - Add to auto-lowercase list permanently

#### Numbered Line Editing
- Edit lines containing 3+ digit numbers
- Navigate with Previous/Next buttons
- Roman numeral reference guide included

## Configuration

### .data.txt File

The program uses a `.data.txt` file for configuration with the following sections:

```
# CHOICE
word -> option1;option2;option3

# REPLACE
old_text -> new_text

# PERIODS
abbreviation_without_periods

# CAP_IGNORE
SEQUENCE_TO_IGNORE

# UPPER_TO_LOWER
SEQUENCE_TO_LOWERCASE

# DEFAULT_FILE_DIR
/path/to/your/ebook/folder
```

### Example Configuration

```
# CHOICE
colour -> color;colour
realise -> realize;realise

# REPLACE
-- -> —
... -> …

# PERIODS
Mr
Dr
St

# CAP_IGNORE
NASA
FBI

# UPPER_TO_LOWER
CHAPTER
BOOK

# DEFAULT_FILE_DIR
/Users/username/Documents/Ebooks
```

## Output Files

### Generated Files
- `filename_output.txt` - Main processed output
- `debug.txt` - Choice replacement log
- `matches.txt` - Detailed match processing log
- `roman_conversions.log` - Roman numeral conversion log
- `pagination_debug.txt` - Pagination removal log
- `bookfix_execution.log` - Complete execution log

### Log Files
The program generates comprehensive logs for debugging and verification:
- Processing steps and timing
- Match details and replacements
- Error messages and warnings
- Configuration loading status

## Advanced Features

### Roman Numeral Protection
- Protects abbreviations: `I.D.` stays `I.D.`
- Protects pronoun: `I` stays `I`
- Converts numerals: `Chapter II` becomes `Chapter 2`
- Context-aware processing prevents false positives

### Regex Patterns
- Word boundary detection for accurate matching
- Case-insensitive processing where appropriate
- Escape special characters in user input
- Multi-line pattern support

### Error Handling
- Graceful recovery from file access errors
- Detailed error logging
- User-friendly error messages
- Automatic log file management

## Keyboard Shortcuts

### Interactive Choices
- `1-9` - Select replacement option
- `Numpad 1-9` - Select replacement option (alternative)

### All-Caps Processing
- `Y` - Yes (lowercase this and all remaining)
- `N` - No (keep uppercase)
- `A` - Add to ignore list
- `I` - Auto-lowercase (add to permanent list)

## Troubleshooting

### Common Issues

1. **File not found errors**
   - Check file path and permissions
   - Ensure file is not open in another program

2. **Missing dependencies**
   ```bash
   pip install beautifulsoup4
   ```

3. **GUI not appearing**
   - Verify tkinter installation
   - Check Python version compatibility

4. **Slow processing**
   - Large files may take time
   - Monitor progress bar for status

### Platform-Specific Notes

#### Windows
- Use forward slashes in paths: `C:/Users/name/Documents`
- May require additional permissions for file access

#### macOS
- Grant file access permissions when prompted
- Use `python3` command explicitly

#### Linux
- Ensure display server is running for GUI
- Install tkinter if not included: `sudo apt-get install python3-tk`

## Development

### Code Structure
- `bookfix.py` - Main application file
- Global variables for state management
- Modular functions for each processing step
- Tkinter GUI with event-driven architecture

### Extending Functionality
- Add new processing steps to `run_processing()`
- Extend `.data.txt` sections for new configuration options
- Implement additional file format support

## License

This project is open source. Feel free to modify and distribute according to your needs.

## Support

For issues or questions:
1. Check the log files for detailed error information
2. Verify configuration file format
3. Ensure all dependencies are installed
4. Test with smaller files first

---

*Last updated: 2025-01-17*