"""
Logging configuration for Accessible PDF Toolkit.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
from logging.handlers import RotatingFileHandler

from .constants import LOG_FILE, APP_NAME, ensure_directories


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color support for terminal output."""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        # Add color to levelname for terminal output
        if hasattr(sys.stdout, "isatty") and sys.stdout.isatty():
            color = self.COLORS.get(record.levelname, "")
            record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(
    level: int = logging.INFO,
    log_to_file: bool = True,
    log_to_console: bool = True,
) -> logging.Logger:
    """
    Configure application-wide logging.

    Args:
        level: Logging level (default: INFO)
        log_to_file: Whether to write logs to file
        log_to_console: Whether to write logs to console

    Returns:
        Configured logger instance
    """
    ensure_directories()

    logger = logging.getLogger(APP_NAME)
    logger.setLevel(level)
    logger.handlers.clear()

    # File handler with rotation
    if log_to_file:
        file_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    # Console handler with colors
    if log_to_console:
        console_formatter = ColoredFormatter(
            "%(levelname)s | %(message)s"
        )
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (uses APP_NAME if not provided)

    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(f"{APP_NAME}.{name}")
    return logging.getLogger(APP_NAME)


class LogCapture:
    """Context manager to capture log output for testing or display."""

    def __init__(self, logger_name: Optional[str] = None, level: int = logging.DEBUG):
        self.logger = get_logger(logger_name)
        self.level = level
        self.handler: Optional[logging.Handler] = None
        self.records: list[logging.LogRecord] = []

    def __enter__(self) -> "LogCapture":
        self.handler = logging.Handler()
        self.handler.setLevel(self.level)
        self.handler.emit = lambda record: self.records.append(record)
        self.logger.addHandler(self.handler)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.handler:
            self.logger.removeHandler(self.handler)

    def get_messages(self) -> list[str]:
        """Get all captured log messages."""
        return [record.getMessage() for record in self.records]

    def get_by_level(self, level: int) -> list[str]:
        """Get log messages filtered by level."""
        return [
            record.getMessage()
            for record in self.records
            if record.levelno == level
        ]


def log_exception(logger: logging.Logger, exc: Exception, context: str = "") -> None:
    """
    Log an exception with context information.

    Args:
        logger: Logger instance
        exc: Exception to log
        context: Additional context about where the exception occurred
    """
    if context:
        logger.error(f"{context}: {type(exc).__name__}: {exc}", exc_info=True)
    else:
        logger.error(f"{type(exc).__name__}: {exc}", exc_info=True)


def log_operation(logger: logging.Logger, operation: str):
    """
    Decorator to log function entry and exit.

    Args:
        logger: Logger instance
        operation: Description of the operation
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger.debug(f"Starting: {operation}")
            start_time = datetime.now()
            try:
                result = func(*args, **kwargs)
                elapsed = (datetime.now() - start_time).total_seconds()
                logger.debug(f"Completed: {operation} ({elapsed:.2f}s)")
                return result
            except Exception as e:
                elapsed = (datetime.now() - start_time).total_seconds()
                logger.error(f"Failed: {operation} ({elapsed:.2f}s) - {e}")
                raise
        return wrapper
    return decorator
