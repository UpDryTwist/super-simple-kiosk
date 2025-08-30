"""Comprehensive unit tests for validators module."""

from unittest.mock import Mock, patch

import requests

from super_simple_kiosk.app.utils.validators import (
    HTTP_ERROR_THRESHOLD,
    HTTP_SCHEMES,
    MAX_DURATION_SECONDS,
    MAX_PORT,
    MAX_TOPIC_LENGTH,
    MIN_DURATION_SECONDS,
    sanitize_string,
    validate_config,
    validate_display_config,
    validate_duration,
    validate_json,
    validate_json_payload,
    validate_mqtt_config,
    validate_topic,
    validate_url,
)


class TestValidateJSON:
    """Test JSON validation functionality."""

    def test_validate_json_valid_data(self) -> None:
        """Test JSON validation with valid data."""
        data = {"name": "test", "value": 123}
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "value": {"type": "number"},
            },
            "required": ["name", "value"],
        }

        is_valid, error = validate_json(data, schema)

        assert is_valid is True
        assert error is None

    def test_validate_json_invalid_data(self) -> None:
        """Test JSON validation with invalid data."""
        data = {"name": 123, "value": "invalid"}  # Wrong types
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "value": {"type": "number"},
            },
            "required": ["name", "value"],
        }

        is_valid, error = validate_json(data, schema)

        assert is_valid is False
        assert error is not None
        # Check for either string or number validation error
        assert any(
            msg in error
            for msg in ["is not of type 'string'", "is not of type 'number'"]
        )

    def test_validate_json_missing_required_field(self) -> None:
        """Test JSON validation with missing required field."""
        data = {"name": "test"}  # Missing 'value'
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "value": {"type": "number"},
            },
            "required": ["name", "value"],
        }

        is_valid, error = validate_json(data, schema)

        assert is_valid is False
        assert error is not None
        assert "required" in error

    def test_validate_json_list_data(self) -> None:
        """Test JSON validation with list data."""
        data = ["item1", "item2", "item3"]
        schema = {
            "type": "array",
            "items": {"type": "string"},
        }

        is_valid, error = validate_json(data, schema)

        assert is_valid is True
        assert error is None

    def test_validate_json_list_invalid_data(self) -> None:
        """Test JSON validation with invalid list data."""
        data = ["item1", 123, "item3"]  # Mixed types
        schema = {
            "type": "array",
            "items": {"type": "string"},
        }

        is_valid, error = validate_json(data, schema)

        assert is_valid is False
        assert error is not None


class TestValidateURL:
    """Test URL validation functionality."""

    def test_validate_url_valid_http(self) -> None:
        """Test URL validation with valid HTTP URL."""
        url = "http://example.com"

        is_valid, error = validate_url(url, check_reachable=False)

        assert is_valid is True
        assert error is None

    def test_validate_url_valid_https(self) -> None:
        """Test URL validation with valid HTTPS URL."""
        url = "https://example.com"

        is_valid, error = validate_url(url, check_reachable=False)

        assert is_valid is True
        assert error is None

    def test_validate_url_with_path(self) -> None:
        """Test URL validation with URL containing path."""
        url = "https://example.com/path/to/resource"

        is_valid, error = validate_url(url, check_reachable=False)

        assert is_valid is True
        assert error is None

    def test_validate_url_with_query_params(self) -> None:
        """Test URL validation with URL containing query parameters."""
        url = "https://example.com/path?param1=value1&param2=value2"

        is_valid, error = validate_url(url, check_reachable=False)

        assert is_valid is True
        assert error is None

    def test_validate_url_with_port(self) -> None:
        """Test URL validation with URL containing port."""
        url = "http://example.com:8080"

        is_valid, error = validate_url(url, check_reachable=False)

        assert is_valid is True
        assert error is None

    def test_validate_url_empty(self) -> None:
        """Test URL validation with empty URL."""
        url = ""

        is_valid, error = validate_url(url, check_reachable=False)

        assert is_valid is False
        assert error == "URL cannot be empty"

    def test_validate_url_none(self) -> None:
        """Test URL validation with None URL."""
        url = None

        is_valid, error = validate_url(url, check_reachable=False)

        assert is_valid is False
        assert error is not None
        assert "URL must be a string" in error

    def test_validate_url_invalid_format(self) -> None:
        """Test URL validation with invalid format."""
        url = "not-a-url"

        is_valid, error = validate_url(url, check_reachable=False)

        assert is_valid is False
        assert error == "Invalid URL format"

    def test_validate_url_missing_scheme(self) -> None:
        """Test URL validation with missing scheme."""
        url = "example.com"

        is_valid, error = validate_url(url, check_reachable=False)

        assert is_valid is False
        assert error == "Invalid URL format"

    def test_validate_url_missing_netloc(self) -> None:
        """Test URL validation with missing netloc."""
        url = "http://"

        is_valid, error = validate_url(url, check_reachable=False)

        assert is_valid is False
        assert error == "Invalid URL format"

    def test_validate_url_unsupported_scheme(self) -> None:
        """Test URL validation with unsupported scheme."""
        url = "ftp://example.com"

        is_valid, error = validate_url(url, check_reachable=False)

        assert is_valid is False
        assert error == "Unsupported scheme: ftp"

    def test_validate_url_reachable_success(self) -> None:
        """Test URL validation with reachability check (success)."""
        url = "https://example.com"

        with patch("requests.head") as mock_head:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_head.return_value = mock_response

            is_valid, error = validate_url(url, check_reachable=True)

            assert is_valid is True
            assert error is None
            mock_head.assert_called_once_with(url, timeout=10, allow_redirects=True)

    def test_validate_url_reachable_http_error(self) -> None:
        """Test URL validation with reachability check (HTTP error)."""
        url = "https://example.com"

        with patch("requests.head") as mock_head:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_head.return_value = mock_response

            is_valid, error = validate_url(url, check_reachable=True)

            assert is_valid is False
            assert error == "URL returned status code: 404"

    def test_validate_url_reachable_connection_error(self) -> None:
        """Test URL validation with reachability check (connection error)."""
        url = "https://example.com"

        with patch("requests.head") as mock_head:
            mock_head.side_effect = requests.ConnectionError("Connection failed")

            is_valid, error = validate_url(url, check_reachable=True)

            assert is_valid is False
            assert error is not None
            assert "URL not reachable" in error

    def test_validate_url_reachable_timeout_error(self) -> None:
        """Test URL validation with reachability check (timeout error)."""
        url = "https://example.com"

        with patch("requests.head") as mock_head:
            mock_head.side_effect = requests.Timeout("Request timeout")

            is_valid, error = validate_url(url, check_reachable=True)

            assert is_valid is False
            assert error is not None
            assert "URL not reachable" in error

    def test_validate_url_reachable_ssl_error(self) -> None:
        """Test URL validation with reachability check (SSL error)."""
        url = "https://example.com"

        with patch("requests.head") as mock_head:
            mock_head.side_effect = requests.ConnectionError("SSL certificate error")

            is_valid, error = validate_url(url, check_reachable=True)

            assert is_valid is False
            assert error is not None
            assert "URL not reachable" in error


class TestValidateDuration:
    """Test duration validation functionality."""

    def test_validate_duration_valid_int(self) -> None:
        """Test duration validation with valid integer."""
        duration = 30

        is_valid, error = validate_duration(duration)

        assert is_valid is True
        assert error is None

    def test_validate_duration_valid_float(self) -> None:
        """Test duration validation with valid float."""
        duration = 30.5

        is_valid, error = validate_duration(duration)

        assert is_valid is True
        assert error is None

    def test_validate_duration_minimum_value(self) -> None:
        """Test duration validation with minimum value."""
        duration = MIN_DURATION_SECONDS

        is_valid, error = validate_duration(duration)

        assert is_valid is True
        assert error is None

    def test_validate_duration_maximum_value(self) -> None:
        """Test duration validation with maximum value."""
        duration = MAX_DURATION_SECONDS

        is_valid, error = validate_duration(duration)

        assert is_valid is True
        assert error is None

    def test_validate_duration_below_minimum(self) -> None:
        """Test duration validation with value below minimum."""
        duration = MIN_DURATION_SECONDS - 1

        is_valid, error = validate_duration(duration)

        assert is_valid is False
        assert error == f"Duration must be at least {MIN_DURATION_SECONDS} seconds"

    def test_validate_duration_zero(self) -> None:
        """Test duration validation with zero value."""
        duration = 0

        is_valid, error = validate_duration(duration)

        assert is_valid is False
        assert error == f"Duration must be at least {MIN_DURATION_SECONDS} seconds"

    def test_validate_duration_negative(self) -> None:
        """Test duration validation with negative value."""
        duration = -10

        is_valid, error = validate_duration(duration)

        assert is_valid is False
        assert error == f"Duration must be at least {MIN_DURATION_SECONDS} seconds"

    def test_validate_duration_above_maximum(self) -> None:
        """Test duration validation with value above maximum."""
        duration = MAX_DURATION_SECONDS + 1

        is_valid, error = validate_duration(duration)

        assert is_valid is False
        assert error == f"Duration cannot exceed {MAX_DURATION_SECONDS} seconds"

    def test_validate_duration_string(self) -> None:
        """Test duration validation with string value."""
        duration = "30"

        is_valid, error = validate_duration(duration)

        assert is_valid is False
        assert error == "Duration must be a number"

    def test_validate_duration_none(self) -> None:
        """Test duration validation with None value."""
        duration = None

        is_valid, error = validate_duration(duration)

        assert is_valid is False
        assert error == "Duration must be a number"

    def test_validate_duration_list(self) -> None:
        """Test duration validation with list value."""
        duration = [30]

        is_valid, error = validate_duration(duration)

        assert is_valid is False
        assert error == "Duration must be a number"


class TestValidateTopic:
    """Test MQTT topic validation functionality."""

    def test_validate_topic_valid(self) -> None:
        """Test topic validation with valid topic."""
        topic = "test/topic"

        is_valid, error = validate_topic(topic)

        assert is_valid is True
        assert error is None

    def test_validate_topic_with_wildcards(self) -> None:
        """Test topic validation with wildcards."""
        topic = "test/+/wildcard/#"

        is_valid, error = validate_topic(topic)

        assert is_valid is True
        assert error is None

    def test_validate_topic_empty(self) -> None:
        """Test topic validation with empty topic."""
        topic = ""

        is_valid, error = validate_topic(topic)

        assert is_valid is False
        assert error == "Topic cannot be empty"

    def test_validate_topic_none(self) -> None:
        """Test topic validation with None topic."""
        topic = None

        is_valid, error = validate_topic(topic)
        assert is_valid is False
        assert error is not None
        assert "Topic must be a string" in error

    def test_validate_topic_too_long(self) -> None:
        """Test topic validation with topic too long."""
        topic = "a" * (MAX_TOPIC_LENGTH + 1)

        is_valid, error = validate_topic(topic)

        assert is_valid is False
        assert error == f"Topic length cannot exceed {MAX_TOPIC_LENGTH} characters"

    def test_validate_topic_with_spaces(self) -> None:
        """Test topic validation with spaces."""
        topic = "test topic"

        is_valid, error = validate_topic(topic)

        assert is_valid is False
        assert error == "Topic contains invalid characters (spaces, newlines, tabs)"

    def test_validate_topic_with_newlines(self) -> None:
        """Test topic validation with newlines."""
        topic = "test\ntopic"

        is_valid, error = validate_topic(topic)

        assert is_valid is False
        assert error == "Topic contains invalid characters (spaces, newlines, tabs)"

    def test_validate_topic_with_tabs(self) -> None:
        """Test topic validation with tabs."""
        topic = "test\ttopic"

        is_valid, error = validate_topic(topic)

        assert is_valid is False
        assert error == "Topic contains invalid characters (spaces, newlines, tabs)"

    def test_validate_topic_with_carriage_returns(self) -> None:
        """Test topic validation with carriage returns."""
        topic = "test\rtopic"

        is_valid, error = validate_topic(topic)

        assert is_valid is False
        assert error == "Topic contains invalid characters (spaces, newlines, tabs)"

    def test_validate_topic_with_special_chars(self) -> None:
        """Test topic validation with special characters (should be valid)."""
        topic = "test/topic-with-dashes_and_underscores"

        is_valid, error = validate_topic(topic)

        assert is_valid is True
        assert error is None

    def test_validate_topic_not_string(self) -> None:
        """Test topic validation with non-string value."""
        topic = 123

        is_valid, error = validate_topic(topic)
        assert is_valid is False
        assert error is not None
        assert "Topic must be a string" in error


class TestValidateConfig:
    """Test configuration validation functionality."""

    def test_validate_config_valid(self) -> None:
        """Test configuration validation with valid config."""
        config = {
            "mqtt": {
                "broker_host": "localhost",
                "broker_port": 1883,
                "client_id": "test-client",
            },
            "display": {
                "default_duration": 30,
                "urls": [
                    {"url": "http://example.com", "duration": 30},
                ],
            },
        }

        is_valid = validate_config(config)

        assert is_valid is True

    def test_validate_config_no_mqtt_or_display(self) -> None:
        """Test configuration validation without MQTT or display config."""
        config = {"other": "value"}

        is_valid = validate_config(config)

        assert is_valid is True

    def test_validate_config_not_dict(self) -> None:
        """Test configuration validation with non-dict data."""
        config = "not a dict"

        is_valid = validate_config(config)

        assert is_valid is False

    def test_validate_config_invalid_mqtt(self) -> None:
        """Test configuration validation with invalid MQTT config."""
        config = {
            "mqtt": "not a dict",  # Should be dict
            "display": {
                "default_duration": 30,
            },
        }

        is_valid = validate_config(config)

        assert is_valid is False

    def test_validate_config_invalid_display(self) -> None:
        """Test configuration validation with invalid display config."""
        config = {
            "mqtt": {
                "broker_host": "localhost",
                "broker_port": 1883,
                "client_id": "test-client",
            },
            "display": "not a dict",  # Should be dict
        }

        is_valid = validate_config(config)

        assert is_valid is False


class TestValidateMQTTConfig:
    """Test MQTT configuration validation functionality."""

    def test_validate_mqtt_config_valid(self) -> None:
        """Test MQTT configuration validation with valid config."""
        config = {
            "broker_host": "localhost",
            "broker_port": 1883,
            "client_id": "test-client",
        }

        is_valid = validate_mqtt_config(config)

        assert is_valid is True

    def test_validate_mqtt_config_with_optional_fields(self) -> None:
        """Test MQTT configuration validation with optional fields."""
        config = {
            "broker_host": "localhost",
            "broker_port": 1883,
            "client_id": "test-client",
            "username": "test-user",
            "password": "test-pass",
            "topics": {
                "command": "test/command",
                "status": "test/status",
            },
        }

        is_valid = validate_mqtt_config(config)

        assert is_valid is True

    def test_validate_mqtt_config_not_dict(self) -> None:
        """Test MQTT configuration validation with non-dict data."""
        config = "not a dict"

        is_valid = validate_mqtt_config(config)

        assert is_valid is False

    def test_validate_mqtt_config_missing_broker_host(self) -> None:
        """Test MQTT configuration validation with missing broker_host."""
        config = {
            "broker_port": 1883,
            "client_id": "test-client",
        }

        is_valid = validate_mqtt_config(config)

        assert is_valid is False

    def test_validate_mqtt_config_missing_broker_port(self) -> None:
        """Test MQTT configuration validation with missing broker_port."""
        config = {
            "broker_host": "localhost",
            "client_id": "test-client",
        }

        is_valid = validate_mqtt_config(config)

        assert is_valid is False

    def test_validate_mqtt_config_missing_client_id(self) -> None:
        """Test MQTT configuration validation with missing client_id."""
        config = {
            "broker_host": "localhost",
            "broker_port": 1883,
        }

        is_valid = validate_mqtt_config(config)

        assert is_valid is False

    def test_validate_mqtt_config_invalid_broker_host_type(self) -> None:
        """Test MQTT configuration validation with invalid broker_host type."""
        config = {
            "broker_host": 123,  # Should be string
            "broker_port": 1883,
            "client_id": "test-client",
        }

        is_valid = validate_mqtt_config(config)

        assert is_valid is False

    def test_validate_mqtt_config_empty_broker_host(self) -> None:
        """Test MQTT configuration validation with empty broker_host."""
        config = {
            "broker_host": "",  # Should not be empty
            "broker_port": 1883,
            "client_id": "test-client",
        }

        is_valid = validate_mqtt_config(config)

        assert is_valid is False

    def test_validate_mqtt_config_invalid_broker_port_type(self) -> None:
        """Test MQTT configuration validation with invalid broker_port type."""
        config = {
            "broker_host": "localhost",
            "broker_port": "not a number",  # Should be number
            "client_id": "test-client",
        }

        is_valid = validate_mqtt_config(config)

        assert is_valid is False

    def test_validate_mqtt_config_broker_port_below_minimum(self) -> None:
        """Test MQTT configuration validation with broker_port below minimum."""
        config = {
            "broker_host": "localhost",
            "broker_port": 0,  # Should be >= 1
            "client_id": "test-client",
        }

        is_valid = validate_mqtt_config(config)

        assert is_valid is False

    def test_validate_mqtt_config_broker_port_above_maximum(self) -> None:
        """Test MQTT configuration validation with broker_port above maximum."""
        config = {
            "broker_host": "localhost",
            "broker_port": MAX_PORT + 1,  # Should be <= MAX_PORT
            "client_id": "test-client",
        }

        is_valid = validate_mqtt_config(config)

        assert is_valid is False

    def test_validate_mqtt_config_invalid_client_id_type(self) -> None:
        """Test MQTT configuration validation with invalid client_id type."""
        config = {
            "broker_host": "localhost",
            "broker_port": 1883,
            "client_id": 123,  # Should be string
        }

        is_valid = validate_mqtt_config(config)

        assert is_valid is False

    def test_validate_mqtt_config_empty_client_id(self) -> None:
        """Test MQTT configuration validation with empty client_id."""
        config = {
            "broker_host": "localhost",
            "broker_port": 1883,
            "client_id": "",  # Should not be empty
        }

        is_valid = validate_mqtt_config(config)

        assert is_valid is False

    def test_validate_mqtt_config_invalid_username_type(self) -> None:
        """Test MQTT configuration validation with invalid username type."""
        config = {
            "broker_host": "localhost",
            "broker_port": 1883,
            "client_id": "test-client",
            "username": 123,  # Should be string
        }

        is_valid = validate_mqtt_config(config)

        assert is_valid is False

    def test_validate_mqtt_config_invalid_password_type(self) -> None:
        """Test MQTT configuration validation with invalid password type."""
        config = {
            "broker_host": "localhost",
            "broker_port": 1883,
            "client_id": "test-client",
            "password": 123,  # Should be string
        }

        is_valid = validate_mqtt_config(config)

        assert is_valid is False

    def test_validate_mqtt_config_none_username(self) -> None:
        """Test MQTT configuration validation with None username (should be valid)."""
        config = {
            "broker_host": "localhost",
            "broker_port": 1883,
            "client_id": "test-client",
            "username": None,  # Should be valid
        }

        is_valid = validate_mqtt_config(config)

        assert is_valid is True

    def test_validate_mqtt_config_none_password(self) -> None:
        """Test MQTT configuration validation with None password (should be valid)."""
        config = {
            "broker_host": "localhost",
            "broker_port": 1883,
            "client_id": "test-client",
            "password": None,  # Should be valid
        }

        is_valid = validate_mqtt_config(config)

        assert is_valid is True

    def test_validate_mqtt_config_invalid_topics_type(self) -> None:
        """Test MQTT configuration validation with invalid topics type."""
        config = {
            "broker_host": "localhost",
            "broker_port": 1883,
            "client_id": "test-client",
            "topics": "not a dict",  # Should be dict
        }

        is_valid = validate_mqtt_config(config)

        assert is_valid is False

    def test_validate_mqtt_config_invalid_topic_value_type(self) -> None:
        """Test MQTT configuration validation with invalid topic value type."""
        config = {
            "broker_host": "localhost",
            "broker_port": 1883,
            "client_id": "test-client",
            "topics": {
                "command": 123,  # Should be string
            },
        }

        is_valid = validate_mqtt_config(config)

        assert is_valid is False


class TestValidateDisplayConfig:
    """Test display configuration validation functionality."""

    def test_validate_display_config_valid(self) -> None:
        """Test display configuration validation with valid config."""
        config = {
            "default_duration": 30,
            "urls": [
                {"url": "http://example.com", "duration": 30},
            ],
        }

        is_valid = validate_display_config(config)

        assert is_valid is True

    def test_validate_display_config_empty(self) -> None:
        """Test display configuration validation with empty config."""
        config = {}

        is_valid = validate_display_config(config)

        assert is_valid is True

    def test_validate_display_config_not_dict(self) -> None:
        """Test display configuration validation with non-dict data."""
        config = "not a dict"

        is_valid = validate_display_config(config)

        assert is_valid is False

    def test_validate_display_config_invalid_default_duration(self) -> None:
        """Test display configuration validation with invalid default_duration."""
        config = {
            "default_duration": -1,  # Should be >= MIN_DURATION_SECONDS
        }

        is_valid = validate_display_config(config)

        assert is_valid is False

    def test_validate_display_config_invalid_urls_type(self) -> None:
        """Test display configuration validation with invalid urls type."""
        config = {
            "urls": "not a list",  # Should be list
        }

        is_valid = validate_display_config(config)

        assert is_valid is False

    def test_validate_display_config_invalid_url_config_type(self) -> None:
        """Test display configuration validation with invalid url config type."""
        config = {
            "urls": [
                "not a dict",  # Should be dict
            ],
        }

        is_valid = validate_display_config(config)

        assert is_valid is False

    def test_validate_display_config_missing_url(self) -> None:
        """Test display configuration validation with missing url field."""
        config = {
            "urls": [
                {"duration": 30},  # Missing 'url'
            ],
        }

        is_valid = validate_display_config(config)

        assert is_valid is False

    def test_validate_display_config_invalid_url(self) -> None:
        """Test display configuration validation with invalid url."""
        config = {
            "urls": [
                {"url": "not-a-valid-url", "duration": 30},
            ],
        }

        is_valid = validate_display_config(config)

        assert is_valid is False

    def test_validate_display_config_invalid_duration(self) -> None:
        """Test display configuration validation with invalid duration."""
        config = {
            "urls": [
                {
                    "url": "http://example.com",
                    "duration": -1,
                },  # Should be >= MIN_DURATION_SECONDS
            ],
        }

        is_valid = validate_display_config(config)

        assert is_valid is False

    def test_validate_display_config_valid_without_duration(self) -> None:
        """Test display configuration validation with valid config without duration."""
        config = {
            "urls": [
                {"url": "http://example.com"},  # Duration is optional
            ],
        }

        is_valid = validate_display_config(config)

        assert is_valid is True


class TestSanitizeString:
    """Test string sanitization functionality."""

    def test_sanitize_string_normal(self) -> None:
        """Test string sanitization with normal string."""
        value = "normal string"

        result = sanitize_string(value)

        assert result == "normal string"

    def test_sanitize_string_with_whitespace(self) -> None:
        """Test string sanitization with whitespace."""
        value = "  string with whitespace  "

        result = sanitize_string(value)

        assert result == "string with whitespace"

    def test_sanitize_string_with_null_chars(self) -> None:
        """Test string sanitization with null characters."""
        value = "string\0with\0nulls"

        result = sanitize_string(value)

        assert result == "stringwithnulls"

    def test_sanitize_string_empty(self) -> None:
        """Test string sanitization with empty string."""
        value = ""

        result = sanitize_string(value)

        assert result == ""

    def test_sanitize_string_whitespace_only(self) -> None:
        """Test string sanitization with whitespace-only string."""
        value = "   \t\n\r   "

        result = sanitize_string(value)

        assert result == ""

    def test_sanitize_string_none(self) -> None:
        """Test string sanitization with None."""
        value = None

        result = sanitize_string(value)

        assert result == ""

    def test_sanitize_string_not_string(self) -> None:
        """Test string sanitization with non-string value."""
        value = 123

        result = sanitize_string(value)

        assert result == ""

    def test_sanitize_string_with_mixed_chars(self) -> None:
        """Test string sanitization with mixed characters."""
        value = "  \0string\0with\0mixed\0chars\0  "

        result = sanitize_string(value)

        assert result == "stringwithmixedchars"


class TestValidateJSONPayload:
    """Test JSON payload validation functionality."""

    def test_validate_json_payload_valid(self) -> None:
        """Test JSON payload validation with valid payload."""
        data = {
            "command": "pause",
            "params": {"index": 1},
        }

        is_valid = validate_json_payload(data)

        assert is_valid is True

    def test_validate_json_payload_not_dict(self) -> None:
        """Test JSON payload validation with non-dict data."""
        data = "not a dict"

        is_valid = validate_json_payload(data)

        assert is_valid is False

    def test_validate_json_payload_missing_command(self) -> None:
        """Test JSON payload validation with missing command field."""
        data = {
            "params": {"index": 1},
        }

        is_valid = validate_json_payload(data)

        assert is_valid is False

    def test_validate_json_payload_invalid_command_type(self) -> None:
        """Test JSON payload validation with invalid command type."""
        data = {
            "command": 123,  # Should be string
        }

        is_valid = validate_json_payload(data)

        assert is_valid is False

    def test_validate_json_payload_empty_command(self) -> None:
        """Test JSON payload validation with empty command (should be valid)."""
        data = {
            "command": "",
        }

        is_valid = validate_json_payload(data)

        assert is_valid is True

    def test_validate_json_payload_with_additional_fields(self) -> None:
        """Test JSON payload validation with additional fields."""
        data = {
            "command": "pause",
            "params": {"index": 1},
            "timestamp": "2023-01-01T10:00:00Z",
            "device_id": "test-device",
        }

        is_valid = validate_json_payload(data)

        assert is_valid is True


class TestConstants:
    """Test validation constants."""

    def test_http_schemes(self) -> None:
        """Test HTTP_SCHEMES constant."""
        assert HTTP_SCHEMES == ["http", "https"]

    def test_http_error_threshold(self) -> None:
        """Test HTTP_ERROR_THRESHOLD constant."""
        assert HTTP_ERROR_THRESHOLD == 400

    def test_max_port(self) -> None:
        """Test MAX_PORT constant."""
        assert MAX_PORT == 65535

    def test_min_duration_seconds(self) -> None:
        """Test MIN_DURATION_SECONDS constant."""
        assert MIN_DURATION_SECONDS == 1

    def test_max_duration_seconds(self) -> None:
        """Test MAX_DURATION_SECONDS constant."""
        assert MAX_DURATION_SECONDS == 86400

    def test_max_topic_length(self) -> None:
        """Test MAX_TOPIC_LENGTH constant."""
        assert MAX_TOPIC_LENGTH == 65535
