"""Integration tests for URL rotation functionality."""

import sys
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


@pytest.mark.integration
@pytest.mark.browser
class TestURLRotation:
    """Test URL rotation integration."""

    def test_rotation_start_stop(
        self,
        display_manager: Mock,
        mock_browser_manager: Mock,
        mock_mqtt_client: Mock,
    ) -> None:
        """Test starting and stopping URL rotation."""
        # Set up display manager
        display_manager.set_browser_manager(mock_browser_manager)
        display_manager.set_mqtt_client(mock_mqtt_client)

        # Start rotation
        result = display_manager.start_rotation()
        assert result is True
        assert display_manager.running is True

        # Stop rotation
        display_manager.shutdown()
        assert display_manager.running is False

    def test_url_navigation_cycle(
        self,
        display_manager: Mock,
        mock_browser_manager: Mock,
        sample_urls: list[dict[str, Any]],
    ) -> None:
        """Test complete URL navigation cycle."""
        # Set up display manager with sample URLs
        display_manager.set_browser_manager(mock_browser_manager)
        display_manager.urls = sample_urls

        # Test navigation to each URL
        for i, url_config in enumerate(sample_urls):
            result = display_manager.jump_to_url(i)
            assert result is True

            # Verify browser was called with correct URL
            mock_browser_manager.navigate_to_url.assert_called_with(url_config["url"])

            # Reset mock for next iteration
            mock_browser_manager.navigate_to_url.reset_mock()

    def test_pause_resume_rotation(
        self,
        display_manager: Mock,
        mock_browser_manager: Mock,
    ) -> None:
        """Test pausing and resuming rotation."""
        # Set up display manager
        display_manager.set_browser_manager(mock_browser_manager)

        # Start rotation
        display_manager.start_rotation()

        # Pause rotation
        result = display_manager.pause_rotation()
        assert result is True
        assert display_manager.is_paused is True

        # Resume rotation
        result = display_manager.resume_rotation()
        assert result is True
        assert display_manager.is_paused is False

    def test_next_url_functionality(
        self,
        display_manager: Mock,
        mock_browser_manager: Mock,
        sample_urls: list[dict[str, Any]],
    ) -> None:
        """Test next URL functionality."""
        # Set up display manager with sample URLs
        display_manager.set_browser_manager(mock_browser_manager)
        display_manager.urls = sample_urls
        display_manager.current_index = 0

        # Move to next URL
        result = display_manager.next_url()
        assert result is True
        assert display_manager.current_index == 1

        # Verify browser was called with correct URL
        mock_browser_manager.navigate_to_url.assert_called_with(sample_urls[1]["url"])

    def test_jump_to_specific_url(
        self,
        display_manager: Mock,
        mock_browser_manager: Mock,
        sample_urls: list[dict[str, Any]],
    ) -> None:
        """Test jumping to a specific URL."""
        # Set up display manager with sample URLs
        display_manager.set_browser_manager(mock_browser_manager)
        display_manager.urls = sample_urls

        # Jump to URL at index 2
        result = display_manager.jump_to_url(2)
        assert result is True
        assert display_manager.current_index == 2

        # Verify browser was called with correct URL
        mock_browser_manager.navigate_to_url.assert_called_with(sample_urls[2]["url"])

    def test_invalid_url_index(
        self,
        display_manager: Mock,
        mock_browser_manager: Mock,
        sample_urls: list[dict[str, Any]],
    ) -> None:
        """Test handling of invalid URL indices."""
        # Set up display manager with sample URLs
        display_manager.set_browser_manager(mock_browser_manager)
        display_manager.urls = sample_urls

        # Try to jump to invalid index
        result = display_manager.jump_to_url(999)
        assert result is False

        # Try to jump to negative index
        result = display_manager.jump_to_url(-1)
        assert result is False

    def test_add_url_functionality(
        self,
        display_manager: Mock,
        mock_browser_manager: Mock,
    ) -> None:
        """Test adding URLs to rotation."""
        # Set up display manager
        display_manager.set_browser_manager(mock_browser_manager)

        # Add new URL
        new_url = {"url": "https://new-example.com", "duration": 45}
        result = display_manager.add_url(new_url)
        assert result is True

        # Verify URL was added
        assert len(display_manager.urls) == 1
        assert display_manager.urls[0]["url"] == "https://new-example.com"

    def test_remove_url_functionality(
        self,
        display_manager: Mock,
        mock_browser_manager: Mock,
        sample_urls: list[dict[str, Any]],
    ) -> None:
        """Test removing URLs from rotation."""
        # Set up display manager with sample URLs
        display_manager.set_browser_manager(mock_browser_manager)
        display_manager.urls = sample_urls.copy()

        # Remove URL at index 1
        result = display_manager.remove_url(1)
        assert result is True

        # Verify URL was removed
        assert len(display_manager.urls) == 2
        assert display_manager.urls[0]["url"] == sample_urls[0]["url"]
        assert display_manager.urls[1]["url"] == sample_urls[2]["url"]

    def test_configuration_reload(
        self,
        display_manager: Mock,
        mock_browser_manager: Mock,
        sample_urls: list[dict[str, Any]],
    ) -> None:
        """Test configuration reload functionality."""
        # Set up display manager with initial URLs
        display_manager.set_browser_manager(mock_browser_manager)
        display_manager.urls = sample_urls

        # Mock config reload to return new URLs
        new_urls = [
            {"url": "https://reloaded1.com", "duration": 30},
            {"url": "https://reloaded2.com", "duration": 60},
        ]
        display_manager.config = {"display": {"urls": new_urls, "default_duration": 30}}

        # Reload configuration
        result = display_manager.reload_config()
        assert result is True

        # Verify URLs were updated
        assert display_manager.urls == new_urls

    def test_status_reporting(
        self,
        display_manager: Mock,
        mock_browser_manager: Mock,
        sample_urls: list[dict[str, Any]],
    ) -> None:
        """Test status reporting functionality."""
        # Set up display manager with sample URLs
        display_manager.set_browser_manager(mock_browser_manager)
        display_manager.urls = sample_urls
        display_manager.current_index = 1

        # Get status
        status = display_manager.get_status()

        # Verify status contains expected fields
        assert "status" in status
        assert "current_index" in status
        assert "total_urls" in status
        assert "current_url" in status
        assert status["current_index"] == 1
        assert status["total_urls"] == 3
        assert status["current_url"] == sample_urls[1]["url"]

    def test_error_handling_in_rotation(
        self,
        display_manager: Mock,
        mock_browser_manager: Mock,
        sample_urls: list[dict[str, Any]],
    ) -> None:
        """Test error handling during rotation."""
        # Set up display manager with sample URLs
        display_manager.set_browser_manager(mock_browser_manager)
        display_manager.urls = sample_urls

        # Mock browser to fail navigation
        mock_browser_manager.navigate_to_url.return_value = False

        # Try to navigate to URL
        result = display_manager.jump_to_url(0)
        assert result is False

        # Verify error handling was triggered
        mock_browser_manager.navigate_to_url.assert_called_once()

    def test_rotation_with_empty_url_list(
        self,
        display_manager: Mock,
        mock_browser_manager: Mock,
    ) -> None:
        """Test rotation behavior with empty URL list."""
        # Set up display manager with empty URLs
        display_manager.set_browser_manager(mock_browser_manager)
        display_manager.urls = []

        # Try to start rotation
        result = display_manager.start_rotation()
        assert result is True

        # Try to get next URL
        result = display_manager.next_url()
        assert result is False

        # Try to jump to URL
        result = display_manager.jump_to_url(0)
        assert result is False
