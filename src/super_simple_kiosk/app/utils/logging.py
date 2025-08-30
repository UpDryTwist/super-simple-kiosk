"""
Logging configuration utilities for Super Simple Kiosk.

This module provides logging setup and configuration functionality
for consistent logging throughout the application.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask import Flask


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, "extra"):
            log_record.update(record.extra)  # type: ignore[attr-defined]

        return json.dumps(log_record, ensure_ascii=False)


def setup_logging(
    level: str | None = None,
    format_type: str | None = None,
    log_file: str | None = None,
    app: Flask | None = None,
) -> logging.Logger:
    """
    Set up logging configuration.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Log format type ('text' or 'json')
        log_file: Path to log file (optional)
        app: Flask app instance for app.logger configuration
    """
    # Get values from environment if not provided
    if level is None:
        level = os.environ.get("LOG_LEVEL", "INFO")
    if format_type is None:
        format_type = os.environ.get("LOG_FORMAT", "text")

    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Create formatter
    if format_type.lower() == "json":
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Add file handler if specified
    if log_file:
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Configure Flask app logger if provided
    if app and app.logger:
        app.logger.handlers.clear()
        for handler in root_logger.handlers:
            app.logger.addHandler(handler)
        app.logger.setLevel(numeric_level)

    # Return a logger with the configured level
    logger = logging.getLogger("super_simple_kiosk")
    logger.setLevel(numeric_level)

    # Ensure the logger has at least one handler
    if not logger.handlers:
        logger.addHandler(console_handler)

    logger.info("Logging configured: level=%s, format=%s", level, format_type)
    return logger


class StructuredLogger:
    """Structured logging wrapper for consistent log formatting."""

    def __init__(self, name: str) -> None:
        """
        Initialize structured logger.

        Args:
            name: Logger name
        """
        self.logger = logging.getLogger(name)

    def info(self, message: str, **kwargs: object) -> None:
        """Log info message with structured data."""
        if kwargs:
            self.logger.info(message, extra=kwargs)
        else:
            self.logger.info(message)

    def warning(self, message: str, **kwargs: object) -> None:
        """Log warning message with structured data."""
        if kwargs:
            self.logger.warning(message, extra=kwargs)
        else:
            self.logger.warning(message)

    def error(self, message: str, **kwargs: object) -> None:
        """Log error message with structured data."""
        if kwargs:
            self.logger.error(message, extra=kwargs)
        else:
            self.logger.error(message)

    def debug(self, message: str, **kwargs: object) -> None:
        """Log debug message with structured data."""
        if kwargs:
            self.logger.debug(message, extra=kwargs)
        else:
            self.logger.debug(message)

    def critical(self, message: str, **kwargs: object) -> None:
        """Log critical message with structured data."""
        if kwargs:
            self.logger.critical(message, extra=kwargs)
        else:
            self.logger.critical(message)

    def exception(self, message: str, **kwargs: object) -> None:
        """Log exception message with structured data."""
        if kwargs:
            self.logger.exception(message, extra=kwargs)
        else:
            self.logger.exception(message)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
