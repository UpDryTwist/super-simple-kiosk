"""Simple unit tests for validators module."""

from super_simple_kiosk.app.utils.validators import (
    sanitize_string,
    validate_duration,
    validate_topic,
    validate_url,
)


class TestValidatorsSimple:
    """Test validators functionality with simple tests."""

    def test_validate_url_valid_http(self) -> None:
        """Test validate_url with valid HTTP URL."""
        url = "http://example.com"

        is_valid, error = validate_url(url, check_reachable=False)

        assert is_valid is True
        assert error is None

    def test_validate_url_valid_https(self) -> None:
        """Test validate_url with valid HTTPS URL."""
        url = "https://example.com"

        is_valid, error = validate_url(url, check_reachable=False)

        assert is_valid is True
        assert error is None

    def test_validate_url_invalid_format(self) -> None:
        """Test validate_url with invalid format."""
        url = "not-a-url"

        is_valid, error = validate_url(url, check_reachable=False)

        assert is_valid is False
        assert error is not None

    def test_validate_url_invalid_scheme(self) -> None:
        """Test validate_url with invalid scheme."""
        url = "ftp://example.com"

        is_valid, error = validate_url(url, check_reachable=False)

        assert is_valid is False
        assert error is not None

    def test_validate_duration_valid(self) -> None:
        """Test validate_duration with valid duration."""
        duration = 30

        is_valid, error = validate_duration(duration)

        assert is_valid is True
        assert error is None

    def test_validate_duration_invalid_negative(self) -> None:
        """Test validate_duration with negative value."""
        duration = -10

        is_valid, error = validate_duration(duration)

        assert is_valid is False
        assert error is not None

    def test_validate_duration_invalid_zero(self) -> None:
        """Test validate_duration with zero value."""
        duration = 0

        is_valid, error = validate_duration(duration)

        assert is_valid is False
        assert error is not None

    def test_validate_topic_valid(self) -> None:
        """Test validate_topic with valid topic."""
        topic = "test/topic/123"

        is_valid, error = validate_topic(topic)

        assert is_valid is True
        assert error is None

    def test_validate_topic_with_wildcard(self) -> None:
        """Test validate_topic with wildcard."""
        topic = "test/+/wildcard"

        is_valid, error = validate_topic(topic)

        assert is_valid is True
        assert error is None

    def test_validate_topic_invalid_characters(self) -> None:
        """Test validate_topic with invalid characters."""
        topic = "test/topic with spaces"

        is_valid, error = validate_topic(topic)

        assert is_valid is False
        assert error is not None

    def test_sanitize_string_normal(self) -> None:
        """Test sanitize_string with normal string."""
        value = "Hello World"

        result = sanitize_string(value)

        assert result == "Hello World"

    def test_sanitize_string_with_whitespace(self) -> None:
        """Test sanitize_string with whitespace."""
        value = "  Hello World  "

        result = sanitize_string(value)

        assert result == "Hello World"

    def test_sanitize_string_empty(self) -> None:
        """Test sanitize_string with empty string."""
        value = ""

        result = sanitize_string(value)

        assert result == ""

    def test_sanitize_string_whitespace_only(self) -> None:
        """Test sanitize_string with whitespace only."""
        value = "   "

        result = sanitize_string(value)

        assert result == ""

    def test_sanitize_string_none(self) -> None:
        """Test sanitize_string with None."""
        value = None

        result = sanitize_string(value)

        assert result == ""
