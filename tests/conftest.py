"""Pytest configuration and fixtures for super-simple-kiosk tests."""

import json
import os
import sys
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest
import yaml
from flask import Flask
from flask.testing import FlaskClient
from pytest_mock import MockerFixture

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from super_simple_kiosk.app import create_app  # noqa: E402
from super_simple_kiosk.app.models.config import ConfigManager  # noqa: E402
from super_simple_kiosk.app.services.browser_manager import BrowserManager  # noqa: E402
from super_simple_kiosk.app.services.display_manager import DisplayManager  # noqa: E402
from super_simple_kiosk.app.services.mqtt_client import MQTTClient  # noqa: E402


@pytest.fixture
def temp_files() -> Generator[tuple[str, str], None, None]:
    """Create temporary config and state files for testing."""
    with (
        tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".yaml",
            delete=False,
        ) as config_file,
        tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
        ) as state_file,
    ):
        config_path = config_file.name
        state_path = state_file.name

    yield config_path, state_path

    # Cleanup
    for path in [config_path, state_path]:
        if os.path.exists(path):
            os.unlink(path)


@pytest.fixture
def valid_config() -> dict[str, Any]:
    """Return valid configuration data for testing."""
    return {
        "display": {
            "default_duration": 30,
            "urls": [
                {"url": "https://example.com", "duration": 30},
                {"url": "https://google.com", "duration": 60},
            ],
        },
        "mqtt": {
            "broker_host": "localhost",
            "broker_port": 1883,
            "username": None,
            "password": None,
            "client_id": "test_client",
            "topic_prefix": "test",
        },
    }


@pytest.fixture
def flask_app(temp_files: tuple[str, str], valid_config: dict[str, Any]) -> Flask:
    """Create and configure a Flask app for testing."""
    config_path, state_path = temp_files

    # Write valid config to file
    with open(config_path, "w") as f:
        yaml.dump(valid_config, f)

    # Write initial state to file
    initial_state = {
        "current_index": 0,
        "is_paused": False,
        "rotation_start_time": "2023-01-01T00:00:00Z",
        "total_rotations": 0,
        "error_count": 0,
        "last_config_update": "2023-01-01T00:00:00Z",
        "device_info": {
            "hostname": "test-host",
            "version": "1.0.0",
            "chromium_version": "test-version",
        },
    }
    with open(state_path, "w") as f:
        json.dump(initial_state, f)

    # Create Flask app with test config
    return create_app(
        {
            "TESTING": True,
            "CONFIG_FILE": config_path,
            "STATE_FILE": state_path,
        },
    )


@pytest.fixture
def test_client(flask_app: Flask) -> Generator[FlaskClient, None, None]:
    """Create a test client for the Flask app."""
    with flask_app.test_client() as client, flask_app.app_context():
        yield client


@pytest.fixture
def config_manager(temp_files: tuple[str, str]) -> ConfigManager:
    """Create a ConfigManager instance for testing."""
    config_path, state_path = temp_files
    return ConfigManager(config_path, state_path)


@pytest.fixture
def mock_browser_manager(mocker: Mock, config_manager: ConfigManager) -> Mock:
    """Create a mocked BrowserManager for testing."""
    browser_manager = mocker.MagicMock(spec=BrowserManager)
    browser_manager.is_initialized = True
    browser_manager.navigate_to_url.return_value = True
    browser_manager.should_retry_url.return_value = True
    browser_manager.current_url = "https://example.com"
    return browser_manager


@pytest.fixture
def mock_mqtt_client(mocker: Mock, config_manager: ConfigManager) -> Mock:
    """Create a mocked MQTTClient for testing."""
    mqtt_client = mocker.MagicMock(spec=MQTTClient)
    mqtt_client.is_connected = True
    mqtt_client.connect.return_value = True
    mqtt_client.publish_status.return_value = True
    mqtt_client.set_display_manager = mocker.MagicMock()
    mqtt_client.subscribe_to_commands = mocker.MagicMock(return_value=True)

    # Add mock client for tests that need it
    mock_client = mocker.MagicMock()
    mock_client.publish = mocker.MagicMock()
    mock_client.connect = mocker.MagicMock()
    mock_client.loop_start = mocker.MagicMock()
    mock_client.subscribe = mocker.MagicMock()
    mqtt_client.client = mock_client

    # Create a mock display manager for the MQTT client
    mock_display_manager = mocker.MagicMock()
    mock_display_manager.pause_rotation = mocker.MagicMock(return_value=True)
    mock_display_manager.resume_rotation = mocker.MagicMock(return_value=True)
    mock_display_manager.jump_to_url = mocker.MagicMock(return_value=True)
    mock_display_manager.next_url = mocker.MagicMock(return_value=True)
    mock_display_manager.add_url = mocker.MagicMock(return_value=True)
    mqtt_client.display_manager = mock_display_manager

    # Create a real handle_command method that calls display manager
    def handle_command(command_data: dict[str, Any]) -> bool:  # noqa: PLR0911
        if (
            not hasattr(mqtt_client, "display_manager")
            or not mqtt_client.display_manager
        ):
            return False

        command = command_data.get("command")
        if command == "pause":
            return mqtt_client.display_manager.pause_rotation()
        if command == "resume":
            return mqtt_client.display_manager.resume_rotation()
        if command == "next":
            return mqtt_client.display_manager.next_url()
        if command == "jump":
            index = command_data.get("index")
            if index is not None:
                return mqtt_client.display_manager.jump_to_url(index)
            return False
        if command == "add_url":
            url = command_data.get("url")
            duration = command_data.get("duration", 30)
            index = command_data.get("index")

            if url:
                url_config = {"url": url, "duration": duration}
                return mqtt_client.display_manager.add_url(url_config, index)
            return False
        return False

    # Create a real publish_status method that calls client.publish
    def publish_status() -> bool:
        if hasattr(mqtt_client, "client") and mqtt_client.client:
            mqtt_client.client.publish("test/status", "test_payload")
            return True
        return False

    mqtt_client.handle_command = handle_command
    mqtt_client.publish_status = publish_status

    # Create a real connect method that calls the client
    def connect() -> bool:
        mqtt_client.client.connect()
        mqtt_client.client.loop_start()
        return True

    mqtt_client.connect = connect

    # Create a real subscribe_to_commands method that calls the client
    def subscribe_to_commands() -> bool:
        mqtt_client.client.subscribe()
        return True

    mqtt_client.subscribe_to_commands = subscribe_to_commands
    return mqtt_client


@pytest.fixture
def display_manager(
    mocker: MockerFixture,
    config_manager: ConfigManager,
    mock_browser_manager: Mock,
    mock_mqtt_client: Mock,
) -> DisplayManager:
    """Create a DisplayManager instance for testing."""
    display_manager = DisplayManager(
        config_manager,
        mock_mqtt_client,
        mock_browser_manager,
    )

    # Clear URLs for testing
    display_manager.urls = []

    return display_manager


@pytest.fixture
def sample_urls() -> list[dict[str, Any]]:
    """Sample URLs for testing."""
    return [
        {"url": "https://example.com", "duration": 30},
        {"url": "https://google.com", "duration": 60},
        {"url": "https://github.com", "duration": 45},
    ]


@pytest.fixture
def sample_mqtt_command() -> dict[str, Any]:
    """Sample MQTT command for testing."""
    return {
        "command": "pause",
        "timestamp": "2023-01-01T10:30:00Z",
        "device_id": "test_device",
    }


@pytest.fixture
def sample_mqtt_status() -> dict[str, Any]:
    """Sample MQTT status for testing."""
    return {
        "device_id": "test_device",
        "status": "running",
        "current_url": "https://example.com",
        "current_index": 0,
        "total_urls": 3,
        "remaining_time": 25,
        "last_error": None,
        "uptime": 3600,
        "timestamp": "2023-01-01T10:35:00Z",
    }
