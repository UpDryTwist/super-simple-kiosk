"""
Input validation utilities for Super Simple Kiosk.

This module provides validation functions for ensuring data integrity
and proper format of user inputs and configuration data.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

import jsonschema
import requests
from jsonschema import ValidationError

# Constants for validation
MAX_TOPIC_LENGTH = 65535
MAX_DURATION_SECONDS = 86400
MIN_DURATION_SECONDS = 1
HTTP_ERROR_THRESHOLD = 400
HTTP_SCHEMES = ["http", "https"]
MAX_PORT = 65535


def validate_json(
    data: dict[str, Any] | list[Any],
    schema: dict[str, Any],
) -> tuple[bool, str | None]:
    """Validate JSON data against a JSON schema."""
    try:
        jsonschema.validate(instance=data, schema=schema)
    except ValidationError as e:
        return False, str(e)
    else:
        return True, None


def validate_url(  # noqa: PLR0911
    url: object,
    *,
    check_reachable: bool = True,
) -> tuple[bool, str | None]:
    """
    Validate URL format and accessibility.

    Args:
        url: URL string to validate
        check_reachable: Whether to check if URL is reachable

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(url, str):
        return False, "URL must be a string"

    if not url:
        return False, "URL cannot be empty"

    # Check URL format
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False, "Invalid URL format"
        if parsed.scheme not in HTTP_SCHEMES:
            return False, f"Unsupported scheme: {parsed.scheme}"
    except (ValueError, AttributeError):
        return False, "Invalid URL format"

    # Check URL accessibility (optional)
    if check_reachable:
        try:
            response = requests.head(url, timeout=10, allow_redirects=True)
            if response.status_code >= HTTP_ERROR_THRESHOLD:
                return False, f"URL returned status code: {response.status_code}"
        except requests.RequestException as e:
            return False, f"URL not reachable: {e!s}"

    return True, None


def validate_duration(duration: object) -> tuple[bool, str | None]:
    """
    Validate duration value.

    Args:
        duration: Duration value to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(duration, (int, float)):
        return False, "Duration must be a number"

    if duration < MIN_DURATION_SECONDS:
        return False, f"Duration must be at least {MIN_DURATION_SECONDS} seconds"

    if duration > MAX_DURATION_SECONDS:
        return False, f"Duration cannot exceed {MAX_DURATION_SECONDS} seconds"

    return True, None


def validate_topic(topic: object) -> tuple[bool, str | None]:
    """
    Validate MQTT topic format.

    Args:
        topic: Topic string to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(topic, str):
        return False, "Topic must be a string"

    if not topic:
        return False, "Topic cannot be empty"

    if len(topic) > MAX_TOPIC_LENGTH:
        return False, f"Topic length cannot exceed {MAX_TOPIC_LENGTH} characters"

    # Check for invalid characters (spaces, newlines, etc.)
    if re.search(r"[\s\n\r\t]", topic):
        return False, "Topic contains invalid characters (spaces, newlines, tabs)"

    return True, None


def validate_config(data: object) -> bool:
    """
    Validate configuration data structure.

    Args:
        data: Configuration data to validate

    Returns:
        True if valid, False otherwise
    """
    if not isinstance(data, dict):
        return False

    # Validate MQTT configuration
    if "mqtt" in data and not validate_mqtt_config(data["mqtt"]):
        return False

    # Validate display configuration
    return not ("display" in data and not validate_display_config(data["display"]))


def validate_mqtt_config(config: object) -> bool:  # noqa: PLR0911
    """
    Validate MQTT configuration data.

    Args:
        config: MQTT configuration to validate

    Returns:
        True if valid, False otherwise
    """
    if not isinstance(config, dict):
        return False

    # Check required fields
    required_fields = ["broker_host", "broker_port", "client_id"]
    for field in required_fields:
        if field not in config:
            return False

    # Validate broker host
    broker_host = config["broker_host"]
    if not isinstance(broker_host, str) or not broker_host:
        return False

    # Validate broker port
    try:
        port = int(config["broker_port"])
        if port < 1 or port > MAX_PORT:
            return False
    except (ValueError, TypeError):
        return False

    # Validate client ID
    client_id = config["client_id"]
    if not isinstance(client_id, str) or not client_id:
        return False

    # Validate optional fields
    if (
        "username" in config
        and config["username"] is not None
        and not isinstance(config["username"], str)
    ):
        return False

    if (
        "password" in config
        and config["password"] is not None
        and not isinstance(config["password"], str)
    ):
        return False

    # Validate topics if present
    if "topics" in config:
        topics = config["topics"]
        if not isinstance(topics, dict):
            return False

        for topic_value in topics.values():
            if not isinstance(topic_value, str):
                return False

    return True


def validate_display_config(config: object) -> bool:  # noqa: PLR0911
    """
    Validate display configuration data.

    Args:
        config: Display configuration to validate

    Returns:
        True if valid, False otherwise
    """
    if not isinstance(config, dict):
        return False

    # Validate default duration
    if "default_duration" in config:
        default_duration = config["default_duration"]
        is_valid, _ = validate_duration(default_duration)
        if not is_valid:
            return False

    # Validate URLs
    if "urls" in config:
        urls = config["urls"]
        if not isinstance(urls, list):
            return False

        for url_config in urls:
            if not isinstance(url_config, dict):
                return False

            # Validate URL
            if "url" not in url_config:
                return False

            url = url_config["url"]
            is_valid, _ = validate_url(url)
            if not is_valid:
                return False

            # Validate duration if present
            if "duration" in url_config:
                duration = url_config["duration"]
                is_valid, _ = validate_duration(duration)
                if not is_valid:
                    return False

    return True


def sanitize_string(value: object) -> str:
    """
    Sanitize string input.

    Args:
        value: String to sanitize

    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        return ""

    # Remove null characters and other potentially dangerous characters
    return value.replace("\0", "").strip()


def validate_json_payload(data: object) -> bool:
    """
    Validate JSON payload structure.

    Args:
        data: JSON payload to validate

    Returns:
        True if valid, False otherwise
    """
    if not isinstance(data, dict):
        return False

    # Check for required command field
    if "command" not in data:
        return False

    command = data["command"]
    return isinstance(command, str)
