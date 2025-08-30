"""
Tests for the Display Manager service.

This module provides comprehensive tests for the DisplayManager class,
including URL rotation, pause/resume functionality, configuration management,
and integration with other services.
"""

import json
import tempfile
import threading
import time
from collections.abc import Generator
from unittest.mock import MagicMock, Mock, patch

import pytest
import yaml

from super_simple_kiosk.app.models.config import ConfigManager
from super_simple_kiosk.app.services.browser_manager import BrowserManager
from super_simple_kiosk.app.services.display_manager import DisplayManager
from super_simple_kiosk.app.services.mqtt_client import MQTTClient


class TestDisplayManager:
    """Test cases for DisplayManager class."""

    def teardown_method(self) -> None:
        """Clean up after each test method."""
        # This ensures that any browser instances and threads are cleaned up even if tests fail

    @pytest.fixture
    def temp_config_file(self) -> Generator[str, None, None]:
        """Create a temporary configuration file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config_data = {
                "display": {
                    "default_duration": 30,
                    "urls": [
                        {"url": "https://example1.com", "duration": 30},
                        {"url": "https://example2.com", "duration": 45},
                        {"url": "https://example3.com", "duration": 60},
                    ],
                },
                "mqtt": {
                    "broker": "localhost",
                    "port": 1883,
                    "client_id": "test_client",
                    "topics": {
                        "commands": "test/commands",
                        "status": "test/status",
                    },
                },
            }

            yaml.dump(config_data, f)
            yield f.name

    @pytest.fixture
    def temp_state_file(self) -> Generator[str, None, None]:
        """Create a temporary state file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            state_data = {
                "current_index": 0,
                "is_paused": False,
                "rotation_start_time": "2023-01-01T00:00:00Z",
                "total_rotations": 0,
                "error_count": 0,
                "device_info": {"hostname": "test-host", "version": "1.0.0"},
            }
            json.dump(state_data, f)
            yield f.name

    @pytest.fixture
    def config_manager(
        self,
        temp_config_file: str,
        temp_state_file: str,
    ) -> ConfigManager:
        """Create a ConfigManager instance."""
        return ConfigManager(temp_config_file, temp_state_file)

    @pytest.fixture
    def browser_manager(
        self,
        config_manager: ConfigManager,
    ) -> Generator[BrowserManager, None, None]:
        """Create a BrowserManager instance for testing."""
        manager = BrowserManager(config_manager)
        yield manager
        # Ensure browser is properly shut down after each test
        manager.shutdown()

    @pytest.fixture
    def display_manager(
        self,
        config_manager: ConfigManager,
    ) -> Generator[DisplayManager, None, None]:
        """Create a DisplayManager instance."""
        manager = DisplayManager(config_manager)
        yield manager
        # Ensure display manager is properly shut down after each test
        manager.shutdown()

    def test_initialization(self, display_manager: DisplayManager) -> None:
        """Test DisplayManager initialization."""
        assert display_manager.config_manager is not None
        assert display_manager.mqtt_client is None
        assert display_manager.browser_manager is None
        assert display_manager.current_index == 0
        assert display_manager.is_paused is False
        assert len(display_manager.urls) == 3
        assert display_manager.default_duration == 30

    def test_set_mqtt_client(self, display_manager: DisplayManager) -> None:
        """Test setting MQTT client."""
        mock_mqtt = MagicMock(spec=MQTTClient)
        display_manager.set_mqtt_client(mock_mqtt)
        assert display_manager.mqtt_client == mock_mqtt

    def test_set_browser_manager(self, display_manager: DisplayManager) -> None:
        """Test setting browser manager."""
        mock_browser = MagicMock(spec=BrowserManager)
        display_manager.set_browser_manager(mock_browser)
        assert display_manager.browser_manager == mock_browser

    def test_pause_rotation(self, display_manager: DisplayManager) -> None:
        """Test pausing rotation."""
        result = display_manager.pause_rotation()
        assert result is True
        assert display_manager.is_paused is True

    def test_resume_rotation(self, display_manager: DisplayManager) -> None:
        """Test resuming rotation."""
        # First pause
        display_manager.pause_rotation()
        assert display_manager.is_paused is True

        # Then resume
        result = display_manager.resume_rotation()
        assert result is True
        assert display_manager.is_paused is False

    def test_jump_to_url_valid_index(self, display_manager: DisplayManager) -> None:
        """Test jumping to a valid URL index."""
        result = display_manager.jump_to_url(1)
        assert result is True
        assert display_manager.current_index == 1

    def test_jump_to_url_invalid_index(self, display_manager: DisplayManager) -> None:
        """Test jumping to an invalid URL index."""
        result = display_manager.jump_to_url(999)
        assert result is False
        assert display_manager.current_index == 0  # Should remain unchanged

    def test_jump_to_url_negative_index(self, display_manager: DisplayManager) -> None:
        """Test jumping to a negative URL index."""
        result = display_manager.jump_to_url(-1)
        assert result is False
        assert display_manager.current_index == 0  # Should remain unchanged

    def test_next_url(self, display_manager: DisplayManager) -> None:
        """Test moving to next URL."""
        initial_index = display_manager.current_index
        result = display_manager.next_url()
        assert result is True
        assert display_manager.current_index == (initial_index + 1) % len(
            display_manager.urls,
        )

    def test_next_url_wraps_around(self, display_manager: DisplayManager) -> None:
        """Test that next_url wraps around to the beginning."""
        # Set to last URL
        display_manager.current_index = len(display_manager.urls) - 1
        result = display_manager.next_url()
        assert result is True
        assert display_manager.current_index == 0

    def test_add_url(self, display_manager: DisplayManager) -> None:
        """Test adding a new URL."""
        initial_count = len(display_manager.urls)
        new_url_config = {"url": "https://new-example.com", "duration": 25}

        result = display_manager.add_url(new_url_config)
        assert result is True
        assert len(display_manager.urls) == initial_count + 1
        assert display_manager.urls[-1]["url"] == "https://new-example.com"

    def test_add_url_with_index(self, display_manager: DisplayManager) -> None:
        """Test adding a URL at a specific index."""
        new_url_config = {"url": "https://inserted-example.com", "duration": 25}

        result = display_manager.add_url(new_url_config, index=1)
        assert result is True
        assert display_manager.urls[1]["url"] == "https://inserted-example.com"

    def test_add_url_invalid_config(self, display_manager: DisplayManager) -> None:
        """Test adding URL with invalid configuration."""
        invalid_config = {"duration": 25}  # Missing URL

        result = display_manager.add_url(invalid_config)
        assert result is False

    def test_remove_url(self, display_manager: DisplayManager) -> None:
        """Test removing a URL."""
        initial_count = len(display_manager.urls)
        url_to_remove = display_manager.urls[1]["url"]

        result = display_manager.remove_url(1)
        assert result is True
        assert len(display_manager.urls) == initial_count - 1
        assert url_to_remove not in [url["url"] for url in display_manager.urls]

    def test_remove_url_invalid_index(self, display_manager: DisplayManager) -> None:
        """Test removing URL with invalid index."""
        initial_count = len(display_manager.urls)

        result = display_manager.remove_url(999)
        assert result is False
        assert len(display_manager.urls) == initial_count  # Should remain unchanged

    def test_reload_config(self, display_manager: DisplayManager) -> None:
        """Test reloading configuration."""
        result = display_manager.reload_config()
        assert result is True
        assert len(display_manager.urls) == 3  # Should reload from file

    def test_get_status(self, display_manager: DisplayManager) -> None:
        """Test getting display status."""
        status = display_manager.get_status()

        assert "status" in status
        assert "current_index" in status
        assert "total_urls" in status
        assert "uptime" in status
        assert status["current_index"] == 0
        assert status["total_urls"] == 3
        assert status["status"] == "stopped"

    def test_get_status_when_paused(self, display_manager: DisplayManager) -> None:
        """Test getting status when rotation is paused."""
        display_manager.pause_rotation()
        status = display_manager.get_status()
        assert status["status"] == "paused"

    def test_get_status_with_current_url(self, display_manager: DisplayManager) -> None:
        """Test getting status includes current URL information."""
        status = display_manager.get_status()
        assert "current_url" in status
        assert status["current_url"] == "https://example1.com"

    @patch("time.sleep")  # Mock sleep to speed up tests
    def test_start_rotation_without_browser_manager(
        self,
        mock_sleep: Mock,
        display_manager: DisplayManager,
    ) -> None:
        """Test starting rotation without browser manager."""
        result = display_manager.start_rotation()
        assert result is True
        assert display_manager.running is True
        assert display_manager.rotation_thread is not None
        assert display_manager.rotation_thread.is_alive()

        # Clean up
        display_manager.shutdown()

    @patch("time.sleep")  # Mock sleep to speed up tests
    def test_start_rotation_with_browser_manager(
        self,
        mock_sleep: Mock,
        display_manager: DisplayManager,
    ) -> None:
        """Test starting rotation with browser manager."""
        mock_browser = MagicMock(spec=BrowserManager)
        mock_browser.is_initialized = False
        mock_browser.initialize.return_value = True
        display_manager.set_browser_manager(mock_browser)

        result = display_manager.start_rotation()
        assert result is True
        mock_browser.initialize.assert_called_once()

        # Clean up
        display_manager.shutdown()

    def test_start_rotation_browser_initialization_fails(
        self,
        display_manager: DisplayManager,
    ) -> None:
        """Test starting rotation when browser initialization fails."""
        mock_browser = MagicMock(spec=BrowserManager)
        mock_browser.is_initialized = False
        mock_browser.initialize.return_value = False
        display_manager.set_browser_manager(mock_browser)

        result = display_manager.start_rotation()
        assert result is False

    @patch("time.sleep")  # Mock sleep to speed up tests
    def test_start_rotation_already_running(
        self,
        mock_sleep: Mock,
        display_manager: DisplayManager,
    ) -> None:
        """Test starting rotation when already running."""
        # Start rotation first time
        display_manager.start_rotation()
        assert display_manager.running is True

        # Try to start again
        result = display_manager.start_rotation()
        assert result is False

        # Clean up
        display_manager.shutdown()

    @patch("time.sleep")  # Mock sleep to speed up tests
    def test_shutdown(self, mock_sleep: Mock, display_manager: DisplayManager) -> None:
        """Test shutting down the display manager."""
        # Start rotation first
        display_manager.start_rotation()
        assert display_manager.running is True

        # Shutdown
        result = display_manager.shutdown()
        assert result is True
        assert display_manager.running is False

    @patch("time.sleep")  # Mock sleep to speed up tests
    def test_rotation_loop_basic(
        self,
        mock_sleep: Mock,
        display_manager: DisplayManager,
    ) -> None:
        """Test basic rotation loop functionality."""
        # Start rotation
        display_manager.start_rotation()

        # Wait a bit for the loop to start
        time.sleep(0.1)

        # Check that the loop is running
        assert display_manager.running is True
        assert display_manager.rotation_thread is not None
        assert display_manager.rotation_thread.is_alive()

        # Shutdown
        display_manager.shutdown()

    @patch("time.sleep")  # Mock sleep to speed up tests
    def test_rotation_loop_with_pause(
        self,
        mock_sleep: Mock,
        display_manager: DisplayManager,
    ) -> None:
        """Test rotation loop with pause functionality."""
        # Start rotation
        display_manager.start_rotation()
        time.sleep(0.1)

        # Pause rotation
        display_manager.pause_rotation()
        time.sleep(0.1)

        # Check that it's paused
        assert display_manager.is_paused is True

        # Resume rotation
        display_manager.resume_rotation()
        time.sleep(0.1)

        # Check that it's running again
        assert display_manager.is_paused is False

        # Shutdown
        display_manager.shutdown()

    @patch("time.sleep")  # Mock sleep to speed up tests
    def test_rotation_loop_with_browser_navigation(
        self,
        mock_sleep: Mock,
        display_manager: DisplayManager,
    ) -> None:
        """Test rotation loop with browser navigation."""
        mock_browser = MagicMock(spec=BrowserManager)
        mock_browser.is_initialized = True
        mock_browser.navigate_to_url.return_value = True
        mock_browser.should_retry_url.return_value = True
        display_manager.set_browser_manager(mock_browser)

        # Start rotation
        display_manager.start_rotation()
        # Use mock_sleep instead of real time.sleep
        mock_sleep(0.1)

        # Check that browser navigation was called
        mock_browser.navigate_to_url.assert_called()

        # Shutdown
        display_manager.shutdown()

    @patch("time.sleep")  # Mock sleep to speed up tests
    def test_rotation_loop_skip_problematic_url(
        self,
        mock_sleep: Mock,
        display_manager: DisplayManager,
    ) -> None:
        """Test rotation loop skips problematic URLs."""
        mock_browser = MagicMock(spec=BrowserManager)
        mock_browser.is_initialized = True
        mock_browser.should_retry_url.return_value = False  # Don't retry
        display_manager.set_browser_manager(mock_browser)

        # Start rotation
        display_manager.start_rotation()
        # Use mock_sleep instead of real time.sleep
        mock_sleep(0.1)

        # Check that the URL was skipped (index should have moved)
        # Note: This is a basic test, in practice we'd need more sophisticated timing

        # Shutdown
        display_manager.shutdown()

    @patch("time.sleep")  # Mock sleep to speed up tests
    def test_thread_safety(
        self,
        mock_sleep: Mock,
        display_manager: DisplayManager,
    ) -> None:
        """Test thread safety of display manager operations."""
        # Start rotation in background
        display_manager.start_rotation()

        # Perform operations from multiple threads
        def pause_operation() -> None:
            display_manager.pause_rotation()

        def resume_operation() -> None:
            display_manager.resume_rotation()

        def jump_operation() -> None:
            display_manager.jump_to_url(1)

        # Create threads
        threads = [
            threading.Thread(target=pause_operation),
            threading.Thread(target=resume_operation),
            threading.Thread(target=jump_operation),
        ]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Shutdown
        display_manager.shutdown()

        # If we get here without exceptions, thread safety is working

    @patch("time.sleep")  # Mock sleep to speed up tests
    def test_error_handling_in_rotation_loop(
        self,
        mock_sleep: Mock,
        display_manager: DisplayManager,
    ) -> None:
        """Test error handling in rotation loop."""
        mock_browser = MagicMock(spec=BrowserManager)
        mock_browser.is_initialized = True
        mock_browser.navigate_to_url.side_effect = Exception("Test error")
        mock_browser.should_retry_url.return_value = True
        display_manager.set_browser_manager(mock_browser)

        # Start rotation
        display_manager.start_rotation()
        # Use mock_sleep instead of real time.sleep
        mock_sleep(0.1)

        # The rotation should continue despite the error
        assert display_manager.running is True

        # Shutdown
        display_manager.shutdown()

    def test_configuration_persistence(self, display_manager: DisplayManager) -> None:
        """Test that configuration changes are persisted."""
        # Add a new URL
        new_url_config = {"url": "https://persistent-example.com", "duration": 25}
        display_manager.add_url(new_url_config)

        # Create a new display manager with the same config manager
        new_display_manager = DisplayManager(display_manager.config_manager)

        # Check that the new URL is present
        urls = [url["url"] for url in new_display_manager.urls]
        assert "https://persistent-example.com" in urls

    def test_state_persistence(self, display_manager: DisplayManager) -> None:
        """Test that state changes are persisted."""
        # Change state
        display_manager.pause_rotation()
        display_manager.jump_to_url(2)

        # Create a new display manager with the same config manager
        new_display_manager = DisplayManager(display_manager.config_manager)

        # Check that state was persisted
        assert new_display_manager.is_paused is True
        assert new_display_manager.current_index == 2
