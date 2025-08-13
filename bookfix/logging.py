"""
Logging utilities for Bookfix.

This module provides centralized logging functionality for the application,
including timestamped messages to stderr and log files.
"""

import datetime
import sys


# Global log file path
log_file_path = "bookfix_execution.log"


def log_message(message: str, level: str = "INFO"):
    """
    Logs a timestamped message to stderr and a log file, flushing immediately.
    
    Args:
        message: The message to log
        level: The log level (INFO, ERROR, WARNING, DEBUG)
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}"
    print(log_entry, file=sys.stderr)  # Print to stderr
    try:
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
            f.flush()  # Explicitly flush the buffer to ensure immediate writing
    except Exception as e:
        print(f"Error writing to log file {log_file_path}: {e}", file=sys.stderr)