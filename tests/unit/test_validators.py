"""Tests for utility modules including logging and validation functions."""

import json
import logging
import os
import sys
from unittest.mock import MagicMock, Mock, patch

from requests.exceptions import RequestException

from super_simple_kiosk.app.utils.logging import (
    JSONFormatter,
    get_logger,
    setup_logging,
)
from super_simple_kiosk.app.utils.validators import (
    validate_duration,
    validate_json,
    validate_topic,
    validate_url,
)


class TestJSONFormatter:
    """Test JSON formatter for structured logging."""

    def test_json_formatter_basic(self) -> None:
        """Test basic JSON formatting."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        log_data = json.loads(result)

        assert log_data["level"] == "INFO"
        assert log_data["message"] == "Test message"
        assert log_data["module"] == "test"
        assert "timestamp" in log_data

    def test_json_formatter_with_exception(self) -> None:
        """Test JSON formatting with exception info."""
        formatter = JSONFormatter()

        try:
            raise ValueError("Test exception")
        except ValueError:
            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=1,
                msg="Error occurred",
                args=(),
                exc_info=sys.exc_info(),
            )

        result = formatter.format(record)
        log_data = json.loads(result)

        assert log_data["level"] == "ERROR"
        assert log_data["message"] == "Error occurred"
        assert "exception" in log_data
        assert "ValueError: Test exception" in log_data["exception"]


class TestLoggingSetup:
    """Test logging setup functionality."""

    @patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"})
    def test_setup_logging_with_debug_level(self) -> None:
        """Test logging setup with DEBUG level."""
        logger = setup_logging()
        assert logger.level == logging.DEBUG

    @patch.dict(os.environ, {"LOG_FORMAT": "text"})
    def test_setup_logging_with_text_format(self) -> None:
        """Test logging setup with text format."""
        logger = setup_logging()
        # Should use standard formatter instead of JSON
        assert logger.handlers[0].formatter.__class__ == logging.Formatter

    def test_get_logger(self) -> None:
        """Test get_logger function."""
        logger = get_logger("test_module")
        assert logger.name == "test_module"


class TestJSONValidation:
    """Test JSON schema validation."""

    def test_validate_json_valid_data(self) -> None:
        """Test JSON validation with valid data."""
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
            "required": ["name"],
        }

        data = {"name": "John", "age": 30}
        is_valid, error = validate_json(data, schema)

        assert is_valid is True
        assert error is None

    def test_validate_json_invalid_data(self) -> None:
        """Test JSON validation with invalid data."""
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
            "required": ["name"],
        }

        data = {"age": "not_an_integer"}  # Missing required field and wrong type
        is_valid, error = validate_json(data, schema)

        assert is_valid is False
        assert error is not None
        assert "name" in error  # Should mention missing required field


class TestURLValidation:
    """Test URL validation functionality."""

    def test_validate_url_valid_http(self) -> None:
        """Test URL validation with valid HTTP URL."""
        is_valid, error = validate_url("http://example.com", check_reachable=False)
        assert is_valid is True
        assert error is None

    def test_validate_url_valid_https(self) -> None:
        """Test URL validation with valid HTTPS URL."""
        is_valid, error = validate_url(
            "https://example.com/path?param=value",
            check_reachable=False,
        )
        assert is_valid is True
        assert error is None

    def test_validate_url_invalid_format(self) -> None:
        """Test URL validation with invalid format."""
        is_valid, error = validate_url("not_a_url", check_reachable=False)
        assert is_valid is False
        assert error is not None
        assert "Invalid URL format" in error

    def test_validate_url_invalid_scheme(self) -> None:
        """Test URL validation with invalid scheme."""
        is_valid, error = validate_url("ftp://example.com", check_reachable=False)
        assert is_valid is False
        assert error is not None
        assert "Unsupported scheme: ftp" in error

    @patch("super_simple_kiosk.app.utils.validators.requests.head")
    def test_validate_url_reachable(self, mock_head: Mock) -> None:
        """Test URL reachability checking."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_head.return_value = mock_response

        is_valid, error = validate_url("https://example.com", check_reachable=True)
        assert is_valid is True
        assert error is None

    @patch("super_simple_kiosk.app.utils.validators.requests.head")
    def test_validate_url_not_reachable(self, mock_head: Mock) -> None:
        """Test URL reachability checking with unreachable URL."""
        mock_head.side_effect = RequestException("Connection failed")

        is_valid, error = validate_url("https://example.com", check_reachable=True)
        assert is_valid is False
        assert error is not None
        assert "not reachable" in error


class TestMQTTTopicValidation:
    """Test MQTT topic validation."""

    def test_validate_topic_valid(self) -> None:
        """Test MQTT topic validation with valid topics."""
        valid_topics = [
            "sensor/temperature",
            "device/+/status",
            "home/living-room/#",
            "test-topic",
            "test_topic",
        ]

        for topic in valid_topics:
            is_valid, error = validate_topic(topic)
            assert is_valid is True, f"Topic '{topic}' should be valid: {error}"
            assert error is None

    def test_validate_topic_invalid(self) -> None:
        """Test MQTT topic validation with invalid topics."""
        invalid_cases = [
            ("", "empty string"),
            ("a" * 65536, "too long"),
            ("topic\nwith\nnewlines", "newlines"),
            (123, "non-string"),
        ]

        for topic, description in invalid_cases:
            if isinstance(topic, str):
                is_valid, error = validate_topic(topic)
                assert is_valid is False, (
                    f"Topic '{topic}' ({description}) should be invalid"
                )
                assert error is not None
            else:
                # For non-string inputs, we expect a validation error
                is_valid, error = validate_topic(topic)
                assert is_valid is False
                assert error is not None
                assert "Topic must be a string" in error


class TestDurationValidation:
    """Test duration validation."""

    def test_validate_duration_valid(self) -> None:
        """Test duration validation with valid values."""
        valid_durations = [1, 60, 3600, 86400]  # 1s, 1min, 1hour, 24hours

        for duration in valid_durations:
            is_valid, error = validate_duration(duration)
            assert is_valid is True, f"Duration {duration} should be valid: {error}"
            assert error is None

    def test_validate_duration_invalid(self) -> None:
        """Test duration validation with invalid values."""
        invalid_cases = [
            (0, "zero"),
            (-1, "negative"),
            (86401, "too large"),
            ("not_a_number", "string"),
            (None, "none"),
        ]

        for duration, description in invalid_cases:
            is_valid, error = validate_duration(duration)
            assert is_valid is False, (
                f"Duration {duration} ({description}) should be invalid"
            )
            assert error is not None
