"""
PyQt5 GUI interface for Bookfix.

This module provides a modern PyQt5-based interface for the Bookfix application,
replacing the original Tkinter implementation with improved usability and design.
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
        QPushButton, QTextEdit, QLabel, QCheckBox, QProgressBar,
        QFileDialog, QMessageBox, QGroupBox, QGridLayout, QSplitter,
        QButtonGroup, QRadioButton, QSpinBox, QFrame
    )
    from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
    from PyQt5.QtGui import QFont, QTextCursor, QTextCharFormat, QColor
except ImportError:
    print("PyQt5 not installed. Please install with: pip install PyQt5")
    sys.exit(1)

from .context import BookfixContext
from .logging import log_message
from .datafile import load_data_file, save_default_directory_to_data_file
from .pipeline import run_processing, get_available_processors
from .processors.choices import InteractiveChoiceProcessor
from .processors.allcaps import AllCapsProcessor  
from .processors.numbered import NumberedLineProcessor


class ProcessingThread(QThread):
    """Thread for running non-interactive processing steps."""
    
    progress_updated = pyqtSignal(int, int, str)  # current, total, description
    status_updated = pyqtSignal(str)
    processing_complete = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, ctx: BookfixContext, enabled_steps: Dict[str, bool]):
        super().__init__()
        self.ctx = ctx
        self.enabled_steps = enabled_steps
    
    def run(self):
        """Run the processing pipeline in a separate thread."""
        try:
            log_message("Starting processing thread")
            
            def progress_callback(current: int, total: int, description: str):
                self.progress_updated.emit(current, total, description)
            
            def status_callback(status: str):
                self.status_updated.emit(status)
            
            self.ctx = run_processing(
                self.ctx, 
                self.enabled_steps,
                progress_callback=progress_callback,
                status_callback=status_callback
            )
            
            self.processing_complete.emit()
            log_message("Processing thread completed")
            
        except Exception as e:
            error_msg = f"Processing error: {str(e)}"
            log_message(error_msg, level="ERROR")
            self.error_occurred.emit(error_msg)


class BookfixMainWindow(QMainWindow):
    """Main application window for Bookfix."""
    
    def __init__(self):
        super().__init__()
        self.ctx = BookfixContext()
        self.processing_thread: Optional[ProcessingThread] = None
        
        # Interactive processors
        self.choice_processor = InteractiveChoiceProcessor()
        self.caps_processor = AllCapsProcessor()
        self.numbered_processor = NumberedLineProcessor()
        
        # GUI state
        self.current_interactive_step: Optional[str] = None
        self.pending_interactive_steps: List[str] = []
        self.choice_buttons: List[QPushButton] = []
        
        self.init_ui()
        self.setup_callbacks()
        self.load_configuration()
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Bookfix - Ebook Text Processor")
        self.setGeometry(100, 100, 1200, 800)
        
        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # File selection section
        file_section = self.create_file_section()
        main_layout.addWidget(file_section)
        
        # Processing options section
        options_section = self.create_options_section()
        main_layout.addWidget(options_section)
        
        # Main content area with splitter
        content_splitter = QSplitter(Qt.Horizontal)
        
        # Text display area
        text_widget = self.create_text_section()
        content_splitter.addWidget(text_widget)
        
        # Interactive panel (initially hidden)
        self.interactive_panel = self.create_interactive_panel()
        content_splitter.addWidget(self.interactive_panel)
        self.interactive_panel.hide()
        
        content_splitter.setSizes([800, 400])
        main_layout.addWidget(content_splitter)
        
        # Status and progress section
        status_section = self.create_status_section()
        main_layout.addWidget(status_section)
        
        # Action buttons
        button_section = self.create_button_section()
        main_layout.addWidget(button_section)
        
        # Style the interface
        self.apply_styles()
    
    def create_file_section(self) -> QGroupBox:
        """Create the file selection section."""
        group = QGroupBox("File Selection")
        layout = QHBoxLayout()
        
        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("font-weight: bold;")
        
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.browse_file)
        
        layout.addWidget(QLabel("File:"))
        layout.addWidget(self.file_label, 1)
        layout.addWidget(self.browse_button)
        
        group.setLayout(layout)
        return group
    
    def create_options_section(self) -> QGroupBox:
        """Create the processing options section."""
        group = QGroupBox("Processing Options")
        layout = QGridLayout()
        
        self.checkboxes = {}
        processors = get_available_processors()
        
        row = 0
        col = 0
        
        # Define which processors require interaction
        interactive_processors = {'choices', 'allcaps', 'numbered'}
        
        # Define which processors should be unchecked by default
        unchecked_by_default = {'blanklines', 'lowercase'}
        
        for processor_name, description in processors.items():
            checkbox = QCheckBox(description)
            # Check all boxes except blank line removal and lowercase conversion
            checkbox.setChecked(processor_name not in unchecked_by_default)
            
            if processor_name in interactive_processors:
                checkbox.setStyleSheet("color: #0066CC; font-weight: bold;")
                checkbox.setToolTip("This step requires user interaction")
            
            self.checkboxes[processor_name] = checkbox
            layout.addWidget(checkbox, row, col)
            
            col += 1
            if col > 2:  # 3 columns
                col = 0
                row += 1
        
        # Phonetic analysis checkbox - DISABLED (unreliable results)
        # See phoneticreplacement.txt for details on why this was removed
        self.phonetic_auto_checkbox = QCheckBox("Use Phonetic Analysis (DISABLED - unreliable)")
        self.phonetic_auto_checkbox.setChecked(False)
        self.phonetic_auto_checkbox.setEnabled(False)
        self.phonetic_auto_checkbox.setStyleSheet("color: #888888; font-style: italic;")
        self.phonetic_auto_checkbox.setToolTip("Phonetic analysis disabled due to poor accuracy. Manual interactive choices remain fully functional.")
        
        # Add to layout (new row if needed)
        if col != 0:
            row += 1
        layout.addWidget(self.phonetic_auto_checkbox, row, 0, 1, 3)  # Span 3 columns
        
        group.setLayout(layout)
        return group
    
    def create_text_section(self) -> QWidget:
        """Create the text display section."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Text Content:"))
        
        self.text_edit = QTextEdit()
        self.text_edit.setFont(QFont("Courier New", 10))
        self.text_edit.setReadOnly(True)
        layout.addWidget(self.text_edit)
        
        widget.setLayout(layout)
        return widget
    
    def create_interactive_panel(self) -> QWidget:
        """Create the interactive processing panel."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Title
        self.interactive_title = QLabel("Interactive Processing")
        self.interactive_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #0066CC;")
        layout.addWidget(self.interactive_title)
        
        # Current item info
        self.current_item_label = QLabel("")
        layout.addWidget(self.current_item_label)
        
        # Choice buttons frame
        self.choice_frame = QFrame()
        choice_layout = QVBoxLayout()
        self.choice_frame.setLayout(choice_layout)
        layout.addWidget(self.choice_frame)
        
        # Navigation/action buttons
        nav_layout = QHBoxLayout()
        
        self.prev_button = QPushButton("Previous")
        self.prev_button.clicked.connect(self.handle_previous)
        self.prev_button.setEnabled(False)
        
        self.skip_button = QPushButton("Skip")
        self.skip_button.clicked.connect(self.handle_skip)
        
        nav_layout.addWidget(self.prev_button)
        nav_layout.addStretch()
        nav_layout.addWidget(self.skip_button)
        
        layout.addLayout(nav_layout)
        
        # Roman numeral legend (hidden by default, shown only during numbers processing)
        self.legend_label = QLabel("Roman Numerals: V=5, X=10, L=50, C=100, D=500, M=1000")
        self.legend_label.setStyleSheet("color: #333; font-size: 12px; font-style: italic;")
        self.legend_label.setVisible(False)  # Hide by default
        layout.addWidget(self.legend_label)
        
        # Helper text
        self.helper_label = QLabel("")
        self.helper_label.setStyleSheet("color: #666; font-size: 9px;")
        layout.addWidget(self.helper_label)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_status_section(self) -> QWidget:
        """Create the status and progress section."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        widget.setLayout(layout)
        return widget
    
    def create_button_section(self) -> QWidget:
        """Create the action buttons section."""
        widget = QWidget()
        layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start Processing")
        self.start_button.clicked.connect(self.start_processing)
        self.start_button.setStyleSheet("font-weight: bold; padding: 8px 16px;")
        
        self.save_button = QPushButton("Save Output")
        self.save_button.clicked.connect(self.save_output)
        self.save_button.setEnabled(False)
        
        self.quit_button = QPushButton("Quit")
        self.quit_button.clicked.connect(self.close)
        
        layout.addWidget(self.start_button)
        layout.addStretch()
        layout.addWidget(self.save_button)
        layout.addWidget(self.quit_button)
        
        widget.setLayout(layout)
        return widget
    
    def setup_callbacks(self):
        """Setup callbacks for interactive processors."""
        # Choice processor callbacks
        self.choice_processor.progress_callback = self.update_progress
        self.choice_processor.choice_display_callback = self.display_choices
        self.choice_processor.text_update_callback = self.update_text_display
        self.choice_processor.status_callback = self.update_status
        self.choice_processor.completion_callback = self._handle_manual_completion
        self.choice_processor.text_edit_widget = self.text_edit  # Give direct access to text widget
        
        # Caps processor callbacks
        self.caps_processor.choice_display_callback = self.display_caps_choices
        self.caps_processor.text_update_callback = self.update_text_display
        self.caps_processor.status_callback = self.update_status
        self.caps_processor.text_edit_widget = self.text_edit  # Give direct access to text widget
        
        # Numbered processor callbacks
        self.numbered_processor.line_display_callback = self.display_numbered_line
        self.numbered_processor.navigation_callback = self.update_navigation
        self.numbered_processor.completion_callback = self.complete_numbered_edit
        self.numbered_processor.status_callback = self.update_status
    
    def apply_styles(self):
        """Apply custom styles to the interface."""
        style = """
        QMainWindow {
            background-color: #f0f0f0;
        }
        QGroupBox {
            font-weight: bold;
            border: 2px solid #cccccc;
            border-radius: 5px;
            margin-top: 1ex;
            padding: 5px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        QPushButton {
            background-color: #e1e1e1;
            border: 1px solid #999999;
            border-radius: 3px;
            padding: 6px 12px;
        }
        QPushButton:hover {
            background-color: #d4d4d4;
        }
        QPushButton:pressed {
            background-color: #c4c4c4;
        }
        QPushButton:disabled {
            color: #666666;
            background-color: #f0f0f0;
        }
        """
        self.setStyleSheet(style)
    
    def load_configuration(self):
        """Load configuration from .data.txt file."""
        try:
            self.ctx = load_data_file(self.ctx)
            log_message("Configuration loaded successfully")
        except Exception as e:
            log_message(f"Error loading configuration: {e}", level="ERROR")
            QMessageBox.warning(self, "Configuration Error", 
                              f"Could not load configuration: {e}")
    
    def browse_file(self):
        """Handle file browser dialog."""
        file_dialog = QFileDialog()
        
        # Set initial directory
        initial_dir = str(self.ctx.default_directory) if self.ctx.default_directory else str(Path.home())
        
        file_path, _ = file_dialog.getOpenFileName(
            self,
            "Select file to process",
            initial_dir,
            "Text files (*.txt);;HTML files (*.html *.xhtml);;All files (*.*)"
        )
        
        if file_path:
            self.load_file(file_path)
    
    def load_file(self, file_path: str):
        """Load a file for processing."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.ctx.text = content
            self.ctx.filepath = file_path
            
            # Update UI
            self.file_label.setText(os.path.basename(file_path))
            self.file_label.setToolTip(file_path)
            self.text_edit.setPlainText(content)
            self.start_button.setEnabled(True)
            self.update_status(f"Loaded file: {os.path.basename(file_path)}")
            
            # Change working directory
            os.chdir(os.path.dirname(file_path))
            
            log_message(f"File loaded: {file_path}")
            
        except Exception as e:
            error_msg = f"Error loading file: {e}"
            log_message(error_msg, level="ERROR")
            QMessageBox.critical(self, "File Error", error_msg)
    
    def get_enabled_steps(self) -> Dict[str, bool]:
        """Get the currently enabled processing steps."""
        return {
            name: checkbox.isChecked()
            for name, checkbox in self.checkboxes.items()
        }
    
    def start_processing(self):
        """Start the text processing workflow."""
        if not self.ctx.text:
            QMessageBox.warning(self, "No File", "Please select a file to process first.")
            return
        
        enabled_steps = self.get_enabled_steps()
        
        # Clear log files
        self.clear_log_files()
        
        # Disable UI during processing
        self.start_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Determine which steps need interaction
        interactive_steps = []
        if enabled_steps.get('choices', False):
            interactive_steps.append('interactive_choices')
        if enabled_steps.get('allcaps', False):
            interactive_steps.append('all_caps_processing')
        if enabled_steps.get('numbered', False):
            interactive_steps.append('numbered_line_edit')
        
        self.pending_interactive_steps = interactive_steps
        
        # Start processing thread
        self.processing_thread = ProcessingThread(self.ctx, enabled_steps)
        self.processing_thread.progress_updated.connect(self.on_progress_updated)
        self.processing_thread.status_updated.connect(self.update_status)
        self.processing_thread.processing_complete.connect(self.on_processing_complete)
        self.processing_thread.error_occurred.connect(self.on_processing_error)
        self.processing_thread.start()
    
    def clear_log_files(self):
        """Clear debug and log files."""
        for filename in ['debug.txt', 'matches.txt', 'roman_conversions.log', 'pagination_debug.txt']:
            try:
                open(filename, 'w').close()
            except Exception as e:
                log_message(f"Error clearing {filename}: {e}", level="WARNING")
    
    def on_progress_updated(self, current: int, total: int, description: str):
        """Handle progress updates from processing thread."""
        progress_percent = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(progress_percent)
        self.update_status(f"Step {current}/{total}: {description}")
    
    def on_processing_complete(self):
        """Handle completion of non-interactive processing."""
        self.ctx = self.processing_thread.ctx
        self.update_text_display(self.ctx.text)
        
        # Start interactive processing if needed
        if self.pending_interactive_steps:
            self.start_next_interactive_step()
        else:
            self.complete_all_processing()
    
    def on_processing_error(self, error_message: str):
        """Handle processing errors."""
        self.progress_bar.setVisible(False)
        self.start_button.setEnabled(True)
        QMessageBox.critical(self, "Processing Error", error_message)
    
    def start_next_interactive_step(self):
        """Start the next interactive processing step."""
        if not self.pending_interactive_steps:
            self.complete_all_processing()
            return
        
        step = self.pending_interactive_steps.pop(0)
        self.current_interactive_step = step
        
        # Show interactive panel
        self.interactive_panel.show()
        
        if step == 'interactive_choices':
            self.start_interactive_choices()
        elif step == 'all_caps_processing':
            self.start_all_caps_processing()
        elif step == 'numbered_line_edit':
            self.start_numbered_line_edit()
    
    def start_interactive_choices(self):
        """Start interactive word choices processing."""
        # Phonetic auto mode is disabled (always False)
        use_phonetic_auto = False  # self.phonetic_auto_checkbox.isChecked()
        
        # Always start with manual choices if there are any, regardless of phonetic mode
        manual_words = len(self.ctx.choices) if hasattr(self.ctx, 'choices') else 0
        tagged_words = len(self.ctx.tagged_choices) if hasattr(self.ctx, 'tagged_choices') else 0
        
        if manual_words > 0:
            if use_phonetic_auto and tagged_words > 0:
                self.interactive_title.setText("Manual Word Choices (Hybrid Mode)")
                self.helper_label.setText("First: Select replacements for untagged words. Phonetic analysis will process tagged words afterwards.")
            else:
                self.interactive_title.setText("Interactive Word Choices")
                self.helper_label.setText("Select the best replacement for each highlighted word.")
        elif use_phonetic_auto and tagged_words > 0:
            self.interactive_title.setText("Phonetic Automatic Processing")
            self.helper_label.setText("Phonetic analysis is automatically processing tagged word choices...")
        
        # CRITICAL: Update text widget with current processed text before starting
        from .logging import log_message
        
        # Debug: Check what's currently in the widget
        current_widget_text = self.text_edit.toPlainText()
        log_message(f"BEFORE UPDATE: Widget has {len(current_widget_text)} chars")
        log_message(f"BEFORE UPDATE: Widget text sample: '{current_widget_text[:100]}'")
        
        # Debug: Check what we're about to set
        log_message(f"SETTING: Context text has {len(self.ctx.text)} chars") 
        log_message(f"SETTING: Context text sample: '{self.ctx.text[:100]}'")
        
        # Update the widget
        self.text_edit.setPlainText(self.ctx.text)
        
        # Debug: Verify what's actually in the widget after update
        updated_widget_text = self.text_edit.toPlainText()
        log_message(f"AFTER UPDATE: Widget has {len(updated_widget_text)} chars")
        log_message(f"AFTER UPDATE: Widget text sample: '{updated_widget_text[:100]}'")
        
        # Force widget refresh
        self.text_edit.update()
        self.text_edit.repaint()
        
        log_message(f"Updated text widget with current processed text ({len(self.ctx.text)} chars)")
        
        # Start the choice processing - processor handles its own highlighting
        self.choice_processor.process_choices(self.ctx)
    
    
    def start_all_caps_processing(self):
        """Start all-caps sequence processing."""
        self.interactive_title.setText("All-Caps Sequence Processing")
        self.helper_label.setText("Decide how to handle each all-caps sequence.")
        
        # CRITICAL: Update text widget with current processed text before starting
        from .logging import log_message
        self.text_edit.setPlainText(self.ctx.text)
        log_message(f"Updated text widget with current processed text ({len(self.ctx.text)} chars)")
        
        self.caps_processor.process_all_caps_sequences(self.ctx)
    
    def start_numbered_line_edit(self):
        """Start numbered line editing."""
        self.interactive_title.setText("Numbered Line Editing")
        self.helper_label.setText("Edit lines containing numbers (typically Roman numerals).")
        self.legend_label.setVisible(True)  # Show legend during numbers processing
        
        # CRITICAL: Update text widget with current processed text before starting
        from .logging import log_message
        self.text_edit.setPlainText(self.ctx.text)
        log_message(f"Updated text widget with current processed text ({len(self.ctx.text)} chars)")
        
        if not self.numbered_processor.start_numbered_line_edit(self.ctx):
            # No numbered lines found, move to next step
            self.finish_current_interactive_step()
    
    def display_choices(self, word: str, options: List[str]):
        """Display choice options for interactive processing."""
        self.current_item_label.setText(f"Word: '{word}'")
        
        # Clear existing choices
        layout = self.choice_frame.layout()
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)
        
        # Store choice buttons for keyboard access
        self.choice_buttons = []
        
        # Add choice buttons
        for i, option in enumerate(options):
            button = QPushButton(f"{i+1}. {option}")
            button.clicked.connect(lambda checked, opt=option: self.handle_choice_selection(opt))
            
            # Add keyboard shortcut
            if i < 9:  # Support keys 1-9
                button.setShortcut(f"{i+1}")
                button.setToolTip(f"Press {i+1} or click")
            
            self.choice_buttons.append(button)
            layout.addWidget(button)
        
        # Enable keyboard focus and shortcuts for the main window
        self.setFocusPolicy(Qt.StrongFocus)
        self.interactive_panel.setFocusPolicy(Qt.StrongFocus)
    
    def display_caps_choices(self, sequence: str, options: List[str]):
        """Display choices for all-caps sequences."""
        self.current_item_label.setText(f"All-caps sequence: '{sequence}'")
        
        # Clear existing choices
        layout = self.choice_frame.layout()
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)
            elif item and item.layout():
                # Handle nested layouts
                nested_layout = item.layout()
                for j in reversed(range(nested_layout.count())):
                    nested_item = nested_layout.itemAt(j)
                    if nested_item and nested_item.widget():
                        nested_item.widget().setParent(None)
        
        
        # Add choice buttons with specific handlers
        choices = [
            ("Yes (lowercase)", lambda: self.handle_caps_selection('y')),
            ("No (keep uppercase)", lambda: self.handle_caps_selection('n')),
            ("Add to Ignore", lambda: self.handle_caps_selection('a')),
            ("Auto Lowercase", lambda: self.handle_caps_selection('i'))
        ]
        
        for i, (text, handler) in enumerate(choices):
            button = QPushButton(f"{text}")
            button.clicked.connect(handler)
            layout.addWidget(button)
    
    def display_numbered_line(self, line_no: int, line_content: str, spans: List[Tuple[int, int]]):
        """Display numbered line for editing."""
        self.current_item_label.setText(f"Line {line_no + 1}:")
        
        # Clear existing widgets
        layout = self.choice_frame.layout()
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)
            elif item and item.layout():
                # Handle nested layouts
                nested_layout = item.layout()
                for j in reversed(range(nested_layout.count())):
                    nested_item = nested_layout.itemAt(j)
                    if nested_item and nested_item.widget():
                        nested_item.widget().setParent(None)
        
        # Add text edit for the line
        self.line_edit = QTextEdit()
        self.line_edit.setPlainText(line_content)
        self.line_edit.setMaximumHeight(150)
        
        # Highlight numbers in the text
        cursor = self.line_edit.textCursor()
        format_highlight = QTextCharFormat()
        format_highlight.setBackground(QColor("yellow"))
        
        for start, end in spans:
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.KeepAnchor)
            cursor.setCharFormat(format_highlight)
        
        layout.addWidget(self.line_edit)
        
        # Add buttons
        button_layout = QHBoxLayout()
        
        apply_button = QPushButton("Apply & Next")
        apply_button.clicked.connect(self.handle_numbered_apply)
        
        skip_button = QPushButton("Skip")
        skip_button.clicked.connect(self.handle_numbered_skip)
        
        button_layout.addWidget(apply_button)
        button_layout.addWidget(skip_button)
        
        layout.addLayout(button_layout)
    
    def handle_choice_selection(self, choice: str):
        """Handle selection of a word choice."""
        if not self.choice_processor.handle_choice(choice, self.ctx):
            # All manual choices complete - phonetic processing disabled
            # No automatic processing, finish step
            self.finish_current_interactive_step()
    
    def handle_caps_selection(self, choice: str):
        """Handle selection of caps processing choice."""
        if self.caps_processor.handle_caps_choice(choice, self.ctx):
            # More sequences to process
            pass
        else:
            # All sequences complete
            self.finish_current_interactive_step()
    
    def handle_numbered_apply(self):
        """Handle apply button for numbered line editing."""
        edited_text = self.line_edit.toPlainText()
        if not self.numbered_processor.save_and_next(edited_text):
            # Editing complete
            self.numbered_processor.apply_edits(self.ctx)
            self.finish_current_interactive_step()
    
    def handle_numbered_skip(self):
        """Handle skip button for numbered line editing."""
        if not self.numbered_processor.go_next():
            # Editing complete
            self.numbered_processor.apply_edits(self.ctx)
            self.finish_current_interactive_step()
    
    def handle_previous(self):
        """Handle previous button."""
        if self.current_interactive_step == 'numbered_line_edit':
            self.numbered_processor.go_previous()
    
    def handle_skip(self):
        """Handle skip button."""
        if self.current_interactive_step == 'interactive_choices':
            # Skip current word
            self.choice_processor.handle_choice('', self.ctx)
        elif self.current_interactive_step == 'all_caps_processing':
            # Skip current sequence (treat as 'No')
            self.handle_caps_selection('n')
        elif self.current_interactive_step == 'numbered_line_edit':
            self.handle_numbered_skip()
    
    def finish_current_interactive_step(self):
        """Finish the current interactive step and move to next."""
        self.current_interactive_step = None
        
        # Hide roman legend when finishing any step
        self.legend_label.setVisible(False)
        
        # Clear interactive panel
        layout = self.choice_frame.layout()
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)
            elif item.layout():
                # Handle nested layouts
                nested_layout = item.layout()
                for j in reversed(range(nested_layout.count())):
                    nested_item = nested_layout.itemAt(j)
                    if nested_item.widget():
                        nested_item.widget().setParent(None)
        
        # Update text display and clear any highlighting when transitioning between modes
        self.clear_text_highlighting()
        self.update_text_display(self.ctx.text, preserve_highlighting=False)
        
        # Start next step or complete
        if self.pending_interactive_steps:
            self.start_next_interactive_step()
        else:
            self.interactive_panel.hide()
            self.complete_all_processing()
    
    def complete_all_processing(self):
        """Complete all processing and enable saving."""
        self.progress_bar.setVisible(False)
        self.start_button.setEnabled(True)
        self.save_button.setEnabled(True)
        self.update_status("Processing complete. Ready to save output.")
        
        # Show processing summary
        summary = self.ctx.get_changes_summary()
        log_message("Processing completed successfully")
        log_message(summary)
    
    def update_progress(self, current: int, total: int, description: str):
        """Update progress display."""
        if total > 0:
            progress = int((current / total) * 100)
            self.progress_bar.setValue(progress)
        self.update_status(description)
    
    
    def clear_text_highlighting(self):
        """Clear all text highlighting."""
        # Get the current document
        document = self.text_edit.document()
        cursor = QTextCursor(document)
        
        # Select all text and clear formatting
        cursor.select(QTextCursor.Document)
        format_default = QTextCharFormat()
        cursor.setCharFormat(format_default)
        
        # Clear the selection to avoid visual confusion
        cursor.clearSelection()
        self.text_edit.setTextCursor(cursor)
    
    def update_text_display(self, text: str, preserve_highlighting: bool = True):
        """Update the text display."""
        from .logging import log_message
        log_message(f"Updating text display (length: {len(text)}, preserve_highlighting: {preserve_highlighting})")
        
        # Update the text content
        self.text_edit.setPlainText(text)
        self.ctx.text = text  # Keep context in sync
    
    def update_status(self, status: str):
        """Update status display."""
        self.status_label.setText(status)
    
    def update_navigation(self, current: int, total: int):
        """Update navigation display for numbered editing."""
        self.prev_button.setEnabled(current > 1)
    
    def complete_numbered_edit(self, edits: Dict[int, str]):
        """Complete numbered line editing."""
        # Apply edits handled by the processor
        pass
    
    def save_output(self):
        """Save the processed text to a file."""
        if not self.ctx.text:
            QMessageBox.warning(self, "No Content", "No processed content to save.")
            return
        
        # Generate default filename
        if self.ctx.filepath:
            base_name = os.path.splitext(os.path.basename(self.ctx.filepath))[0]
            default_name = f"{base_name}_output.txt"
        else:
            default_name = "bookfix_output.txt"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save processed text",
            default_name,
            "Text files (*.txt);;All files (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.ctx.text)
                
                QMessageBox.information(self, "File Saved", f"Output saved to:\n{file_path}")
                log_message(f"Output saved to: {file_path}")
                
            except Exception as e:
                error_msg = f"Error saving file: {e}"
                log_message(error_msg, level="ERROR")
                QMessageBox.critical(self, "Save Error", error_msg)
    
    def keyPressEvent(self, event):
        """Handle keyboard events for choice shortcuts."""
        # Only handle keyboard events during interactive processing
        if (self.current_interactive_step == 'interactive_choices' and 
            hasattr(self, 'choice_buttons') and self.choice_buttons):
            
            # Handle number keys 1-9
            key = event.key()
            if Qt.Key_1 <= key <= Qt.Key_9:
                button_index = key - Qt.Key_1  # Convert to 0-based index
                if button_index < len(self.choice_buttons):
                    self.choice_buttons[button_index].click()
                    return
        
        # Let parent handle other keys
        super().keyPressEvent(event)
    
    def _show_phonetic_review(self):
        """Show phonetic processing review with unified click-to-edit text interface."""
        phonetic_log = self.choice_processor.get_phonetic_log()
        
        if not phonetic_log:
            self.current_item_label.setText("Phonetic analysis made no changes.")
            # Continue to manual processing if needed
            manual_words = len(self.ctx.choices) if hasattr(self.ctx, 'choices') else 0
            if manual_words == 0:
                self.finish_current_interactive_step()
            return
        
        self.interactive_title.setText("Phonetic Processing Review")
        self.helper_label.setText("💡 TIP: Click any highlighted yellow word to cycle through spelling options. Click Apply Changes when done.")
        self.helper_label.setStyleSheet("color: #000; font-size: 12pt; font-weight: bold; padding: 5px; background-color: #ffffcc; border: 1px solid #ccc;")
        self.current_item_label.setText(f"Phonetic analysis made {len(phonetic_log)} changes:")
        
        # Clear existing choices
        layout = self.choice_frame.layout()
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)
        
        try:
            from PyQt5.QtWidgets import QTextEdit, QPushButton, QVBoxLayout, QWidget, QScrollArea
            from PyQt5.QtGui import QTextCursor, QTextCharFormat, QColor, QFont
            from PyQt5.QtCore import Qt
            
            # Create compact review showing only changes with context
            self.phonetic_review_edit = QTextEdit()
            self.phonetic_review_edit.setMaximumHeight(400)
            self.phonetic_review_edit.setStyleSheet("font-family: 'Courier New', monospace; font-size: 10pt; background-color: #f9f9f9;")
            
            # Build compact text showing only changes with context
            review_text = ""
            self.phonetic_changes = {}
            current_pos = 0
            
            for i, change in enumerate(phonetic_log):
                original = change['original']
                replacement = change['replacement']
                context_before = change['context_before']
                context_after = change['context_after']
                options = change['options']
                
                # Create context snippet: "...context_before [REPLACEMENT] context_after..."
                snippet = f"Change {i+1}: ...{context_before} [{replacement}] {context_after}...\n\n"
                
                # Find position of the replacement word in this snippet
                bracket_start = snippet.find('[')
                word_start = bracket_start + 1
                word_end = word_start + len(replacement)
                
                # Adjust for current position in review text
                absolute_start = current_pos + word_start
                absolute_end = current_pos + word_end
                
                # Store change data for click handling
                self.phonetic_changes[absolute_start] = {
                    'original': original,
                    'current': replacement,
                    'options': options,
                    'option_index': options.index(replacement) if replacement in options else 0,
                    'start': absolute_start,
                    'end': absolute_end,
                    'snippet_start': current_pos,
                    'snippet_text': snippet
                }
                
                review_text += snippet
                current_pos = len(review_text)
            
            # Set the compact review text
            self.phonetic_review_edit.setPlainText(review_text)
            
            # Apply highlighting to all changes
            cursor = self.phonetic_review_edit.textCursor()
            for change_data in self.phonetic_changes.values():
                cursor.setPosition(change_data['start'])
                cursor.setPosition(change_data['end'], QTextCursor.KeepAnchor)
                
                highlight_format = QTextCharFormat()
                highlight_format.setBackground(QColor(255, 255, 0))  # Bright yellow
                highlight_format.setForeground(QColor(0, 0, 0))
                highlight_format.setFontWeight(700)
                cursor.setCharFormat(highlight_format)
            
            # Make text clickable
            self.phonetic_review_edit.mousePressEvent = self._handle_phonetic_compact_click
            
            # Apply changes button
            apply_button = QPushButton("Apply Changes")
            apply_button.clicked.connect(self._apply_compact_phonetic_changes)
            apply_button.setStyleSheet("font-weight: bold; padding: 8px; background-color: #4CAF50; color: white;")
            
            layout.addWidget(self.phonetic_review_edit)
            layout.addWidget(apply_button)
            
        except Exception as e:
            from .logging import log_message
            log_message(f"Error displaying unified phonetic review: {e}", level="ERROR")
            # Fallback to simple text display
            self.current_item_label.setText(f"Phonetic analysis made {len(phonetic_log)} changes.")
            self._accept_phonetic_changes()

    def _start_phonetic_processing(self):
        """Start phonetic processing phase after manual choices are complete."""
        from .logging import log_message
        
        self.interactive_title.setText("Phonetic Automatic Processing")
        self.helper_label.setText("Phonetic analysis is automatically processing tagged word choices...")
        
        # Clear existing choice display
        layout = self.choice_frame.layout()
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)
        
        # Run phonetic processing
        log_message("Starting phonetic processing phase after manual choices")
        self.choice_processor.process_choices_with_phonetic_analysis(self.ctx)
        
        # Show phonetic review
        self._show_phonetic_review()
    
    def _edit_phonetic_changes(self):
        """Allow user to edit individual phonetic changes."""
        phonetic_log = self.choice_processor.get_phonetic_log()
        
        if not phonetic_log:
            return
        
        # Create edit dialog
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QScrollArea, QWidget, QHBoxLayout, QComboBox, QLabel, QPushButton
        from PyQt5.QtCore import Qt
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Phonetic Changes")
        dialog.setModal(True)
        dialog.resize(800, 600)
        
        layout = QVBoxLayout(dialog)
        
        # Create scrollable area for edits
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        self.edit_widgets = []
        
        for i, entry in enumerate(phonetic_log):
            # Create edit widget for each change
            change_widget = QWidget()
            change_layout = QVBoxLayout(change_widget)
            
            # Context display
            context_label = QLabel(f"Context: ...{entry['context_before']} [{entry['original']}] {entry['context_after']}...")
            context_label.setWordWrap(True)
            context_label.setStyleSheet("font-size: 10pt; color: #666;")
            
            # Choice selection
            choice_layout = QHBoxLayout()
            choice_label = QLabel(f"Change {i+1}: '{entry['original']}' →")
            choice_label.setMinimumWidth(120)
            
            choice_combo = QComboBox()
            choice_combo.addItems(entry['options'])
            
            # Set current selection
            if entry['replacement'] in entry['options']:
                choice_combo.setCurrentText(entry['replacement'])
            
            choice_layout.addWidget(choice_label)
            choice_layout.addWidget(choice_combo)
            choice_layout.addStretch()
            
            change_layout.addWidget(context_label)
            change_layout.addLayout(choice_layout)
            change_layout.addWidget(QWidget())  # Spacer
            
            # Store reference for later
            self.edit_widgets.append({
                'combo': choice_combo,
                'entry': entry,
                'index': i
            })
            
            scroll_layout.addWidget(change_widget)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        
        # Dialog buttons
        button_layout = QHBoxLayout()
        
        apply_button = QPushButton("Apply Changes")
        apply_button.clicked.connect(lambda: self._apply_edits(dialog))
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(dialog.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(apply_button)
        
        layout.addWidget(QLabel("Edit individual phonetic changes:"))
        layout.addWidget(scroll_area)
        layout.addLayout(button_layout)
        
        dialog.exec_()
    
    def _apply_phonetic_review_changes(self):
        """Apply user edits from phonetic review and continue processing."""
        # Get current text
        current_text = self.ctx.text
        
        # Apply changes in reverse order to maintain positions
        edits_to_apply = []
        for widget_data in self.phonetic_edit_widgets:
            new_choice = widget_data['combo'].currentText()
            entry = widget_data['entry']
            
            if new_choice != entry['replacement']:
                # User changed this selection
                edits_to_apply.append({
                    'position': entry['position'],
                    'original': entry['original'],
                    'old_replacement': entry['replacement'],
                    'new_replacement': new_choice
                })
        
        # Sort by position (reverse order)
        edits_to_apply.sort(key=lambda x: x['position'], reverse=True)
        
        # Apply changes
        for edit in edits_to_apply:
            # Find and replace in current text
            pos = edit['position']
            old_text = edit['old_replacement']
            new_text = edit['new_replacement']
            
            # Replace at specific position
            if current_text[pos:pos+len(old_text)] == old_text:
                current_text = current_text[:pos] + new_text + current_text[pos+len(old_text):]
        
        # Update context and display
        self.ctx.text = current_text
        self.choice_processor.current_text = current_text
        
        # Update text display directly
        self.update_text_display(self.ctx.text, preserve_highlighting=False)
        
        # Continue to next processing step
        self.finish_current_interactive_step()
    
    def _handle_phonetic_compact_click(self, event):
        """Handle clicking on highlighted words in compact phonetic review."""
        try:
            from PyQt5.QtCore import Qt
            from PyQt5.QtGui import QTextCursor, QTextCharFormat, QColor
            
            # Get click position
            cursor = self.phonetic_review_edit.cursorForPosition(event.pos())
            click_pos = cursor.position()
            
            # Find if click is on a highlighted change
            clicked_change = None
            for start_pos, change_data in self.phonetic_changes.items():
                if change_data['start'] <= click_pos <= change_data['end']:
                    clicked_change = change_data
                    break
            
            if clicked_change:
                # Cycle to next option
                options = clicked_change['options']
                current_index = clicked_change['option_index']
                next_index = (current_index + 1) % len(options)
                new_option = options[next_index]
                
                # Save current scroll position before making changes
                scrollbar = self.phonetic_review_edit.verticalScrollBar()
                saved_scroll_position = scrollbar.value()
                
                # Update the text in the compact view
                start = clicked_change['start']
                end = clicked_change['end']
                current_text = self.phonetic_review_edit.toPlainText()
                
                # Replace text
                new_text = current_text[:start] + new_option + current_text[end:]
                self.phonetic_review_edit.setPlainText(new_text)
                
                # Update positions for all changes after this one
                length_diff = len(new_option) - len(clicked_change['current'])
                if length_diff != 0:
                    for pos, change in self.phonetic_changes.items():
                        if change['start'] > start:
                            change['start'] += length_diff
                            change['end'] += length_diff
                
                # Update clicked change
                clicked_change['current'] = new_option
                clicked_change['option_index'] = next_index
                clicked_change['end'] = start + len(new_option)
                
                # Re-apply all highlighting
                self._reapply_phonetic_highlighting()
                
                # Restore scroll position after changes
                scrollbar.setValue(saved_scroll_position)
                
        except Exception as e:
            from .logging import log_message
            log_message(f"Error handling compact phonetic click: {e}", level="ERROR")
    
    def _reapply_phonetic_highlighting(self):
        """Re-apply highlighting to all phonetic changes."""
        try:
            from PyQt5.QtGui import QTextCursor, QTextCharFormat, QColor
            
            cursor = self.phonetic_review_edit.textCursor()
            
            # Clear all formatting first
            cursor.select(QTextCursor.Document)
            default_format = QTextCharFormat()
            cursor.setCharFormat(default_format)
            cursor.clearSelection()
            
            # Re-apply highlighting to all changes
            for change_data in self.phonetic_changes.values():
                cursor.setPosition(change_data['start'])
                cursor.setPosition(change_data['end'], QTextCursor.KeepAnchor)
                
                highlight_format = QTextCharFormat()
                highlight_format.setBackground(QColor(255, 255, 0, 180))  # Semi-transparent yellow
                highlight_format.setForeground(QColor(0, 0, 0))
                highlight_format.setFontWeight(700)
                cursor.setCharFormat(highlight_format)
                
        except Exception as e:
            from .logging import log_message
            log_message(f"Error re-applying phonetic highlighting: {e}", level="ERROR")
    
    def _apply_compact_phonetic_changes(self):
        """Apply changes from compact phonetic review interface."""
        try:
            # Apply the user's selections to the actual text
            final_text = self.ctx.text  # Start with current processed text
            
            # Get the original phonetic log to find original positions
            phonetic_log = self.choice_processor.get_phonetic_log()
            
            # Apply changes in reverse order to maintain positions
            changes_to_apply = []
            for change_data in self.phonetic_changes.values():
                # Find corresponding entry in phonetic_log to get original position
                for log_entry in phonetic_log:
                    if (log_entry['original'] == change_data['original'] and 
                        log_entry['replacement'] != change_data['current']):
                        # User changed this selection
                        changes_to_apply.append({
                            'position': log_entry['position'],
                            'original_replacement': log_entry['replacement'],
                            'new_replacement': change_data['current'],
                            'original_word': change_data['original']
                        })
                        break
            
            # Sort by position (reverse order for stable replacement)
            changes_to_apply.sort(key=lambda x: x['position'], reverse=True)
            
            # Apply the changes to the actual text
            for change in changes_to_apply:
                pos = change['position']
                old_replacement = change['original_replacement']
                new_replacement = change['new_replacement']
                
                # Replace in the actual text
                if final_text[pos:pos+len(old_replacement)] == old_replacement:
                    final_text = final_text[:pos] + new_replacement + final_text[pos+len(old_replacement):]
            
            # Update context
            self.ctx.text = final_text
            self.choice_processor.current_text = final_text
            
            # Update main text display
            self.update_text_display(final_text, preserve_highlighting=False)
            
            # Continue to next processing step
            self.finish_current_interactive_step()
            
        except Exception as e:
            from .logging import log_message
            log_message(f"Error applying compact phonetic changes: {e}", level="ERROR")
            # Fallback to accepting current changes
            self._accept_phonetic_changes()
    
    def _handle_manual_completion(self):
        """Handle automatic completion of manual choices without requiring user interaction."""
        # Check if phonetic processing should run
        use_phonetic_auto = self.phonetic_auto_checkbox.isChecked()
        if use_phonetic_auto and hasattr(self.ctx, 'tagged_choices') and self.ctx.tagged_choices:
            # Start phonetic processing phase
            self._start_phonetic_processing()
        else:
            # No phonetic processing needed, finish step
            self.finish_current_interactive_step()

    def _accept_phonetic_changes(self):
        """Accept phonetic changes and finish the choice processing step."""
        # Phonetic processing is complete, move to next step
        self.finish_current_interactive_step()

    def _on_phonetic_toggled(self, checked):
        """Handle phonetic checkbox toggle - ensure interactive choices is enabled when phonetic is enabled."""
        if 'interactive_choices' in self.checkboxes:
            interactive_checkbox = self.checkboxes['interactive_choices']
            if checked:
                # Phonetic enabled - ensure interactive choices is checked and inform user
                interactive_checkbox.setChecked(True)
                interactive_checkbox.setToolTip("Enhanced with phonetic automatic processing")
            else:
                # Phonetic disabled - restore normal tooltip
                interactive_checkbox.setToolTip("This step requires user interaction")
    
    def closeEvent(self, event):
        """Handle application close event."""
        # Stop processing thread if running
        if self.processing_thread and self.processing_thread.isRunning():
            self.processing_thread.terminate()
            self.processing_thread.wait()
        
        log_message("Application closing")
        event.accept()


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("Bookfix")
    app.setOrganizationName("Bookfix")
    
    # Load configuration and check default directory
    temp_ctx = load_data_file()
    
    # Check if default directory needs to be set
    if not temp_ctx.default_directory or not Path(temp_ctx.default_directory).is_dir():
        reply = QMessageBox.question(
            None,
            "Set Default Directory",
            "A default start directory for the file dialog has not been set or is invalid.\n\n"
            "Would you like to select a default directory now?\n\n"
            "Your Calibre Library folder is best, OR a folder you keep your ebook text files.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            initial_dir = str(Path.home())
            directory = QFileDialog.getExistingDirectory(
                None,
                "Select Default Directory for File Dialog",
                initial_dir
            )
            
            if directory:
                save_default_directory_to_data_file(directory)
                QMessageBox.information(
                    None,
                    "Default Directory Set",
                    f"Default directory set to:\n{directory}"
                )
            else:
                # User cancelled, exit
                sys.exit(0)
        else:
            # User chose not to set directory, continue anyway
            pass
    
    # Create and show main window
    window = BookfixMainWindow()
    window.show()
    
    log_message("Bookfix PyQt5 application started")
    
    # Run application
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()