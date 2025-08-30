"""
Display manager service for Super Simple Kiosk.

This module provides the core display management service that handles URL rotation,
scheduling, and coordinates between the browser and MQTT components.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from super_simple_kiosk.app.models.config import ConfigManager
    from super_simple_kiosk.app.services.browser_manager import BrowserManager
    from super_simple_kiosk.app.services.mqtt_client import MQTTClient

logger = logging.getLogger(__name__)


class DisplayManager:
    """Core display manager service for URL rotation and scheduling."""

    def __init__(
        self,
        config_manager: ConfigManager,
        mqtt_client: MQTTClient | None = None,
        browser_manager: BrowserManager | None = None,
    ) -> None:
        """
        Initialize the display manager.

        Args:
            config_manager: Configuration manager for state persistence
            mqtt_client: MQTT client for status updates and commands
            browser_manager: Browser manager for web navigation
        """
        self.config_manager = config_manager
        self.mqtt_client = mqtt_client
        self.browser_manager = browser_manager

        # Load configuration
        self.config = config_manager.load_config()

        # Initialize state
        self.state = config_manager.get_state()
        self.current_index = self.state.get("current_index", 0)
        self.is_paused = self.state.get("is_paused", False)

        # Rotation control
        self.rotation_thread: threading.Thread | None = None
        self.running = False
        self.rotation_lock = threading.Lock()  # For thread-safe operations

        # URL tracking
        display_config = self.config.get("display", {})
        self.urls = display_config.get("urls", [])
        self.default_duration = display_config.get("default_duration", 30)
        self.current_url_start_time = time.time()

    def set_mqtt_client(self, mqtt_client: MQTTClient) -> None:
        """
        Set the MQTT client reference.

        Args:
            mqtt_client: MQTT client instance
        """
        self.mqtt_client = mqtt_client

    def set_browser_manager(self, browser_manager: BrowserManager) -> None:
        """
        Set the browser manager reference.

        Args:
            browser_manager: Browser manager instance
        """
        self.browser_manager = browser_manager

    def start_rotation(self) -> bool:
        """
        Start the URL rotation in a background thread.

        Returns:
            True if rotation started successfully, False otherwise
        """
        if self.rotation_thread and self.rotation_thread.is_alive():
            logger.warning("Rotation already running")
            return False

        # Initialize browser if not already done
        if (
            self.browser_manager
            and not self.browser_manager.is_initialized
            and not self.browser_manager.initialize()
        ):
            logger.error("Failed to initialize browser, cannot start rotation")
            return False

        # Start rotation thread
        self.running = True
        self.rotation_thread = threading.Thread(target=self._rotation_loop, daemon=True)
        self.rotation_thread.start()
        logger.info("URL rotation started")

        return True

    def _rotation_loop(self) -> None:
        """Run the main rotation loop that cycles through URLs."""
        while self.running:
            try:
                with self.rotation_lock:
                    if self.is_paused:
                        time.sleep(1)
                        continue

                    if not self.urls:
                        logger.warning("No URLs configured for rotation")
                        time.sleep(5)
                        continue

                    # Get current URL configuration
                    current_url_config = self.urls[self.current_index]
                    url = current_url_config.get("url", "")
                    duration = current_url_config.get("duration", self.default_duration)

                    # Navigate to URL if browser is available
                    if (
                        self.browser_manager
                        and self.browser_manager.is_initialized
                        and not self.browser_manager.navigate_to_url(url)
                    ):
                        logger.error("Failed to navigate to URL: %s", url)
                        # Try next URL on failure
                        self.current_index = (self.current_index + 1) % len(self.urls)
                        continue

                    # Update state
                    self.state["current_index"] = self.current_index
                    self.state["current_url"] = url
                    self.state["is_paused"] = False
                    self.current_url_start_time = time.time()
                    self.config_manager.update_state(self.state)

                    # Publish status update
                    if self.mqtt_client:
                        self.mqtt_client.publish_status()

                    logger.info(
                        "Displaying URL: %s (duration: %d seconds)",
                        url,
                        duration,
                    )

                # Wait for duration or until interrupted
                time.sleep(duration)

                # Move to next URL
                with self.rotation_lock:
                    self.current_index = (self.current_index + 1) % len(self.urls)

            except Exception:
                logger.exception("Error in rotation loop")
                time.sleep(5)  # Wait before retrying

    def pause_rotation(self) -> bool:
        """
        Pause the URL rotation.

        Returns:
            True if rotation paused successfully, False otherwise
        """
        with self.rotation_lock:
            self.is_paused = True
            self.state["is_paused"] = True
            self.config_manager.update_state(self.state)

        if self.mqtt_client:
            self.mqtt_client.publish_status()

        logger.info("URL rotation paused")
        return True

    def resume_rotation(self) -> bool:
        """
        Resume the URL rotation.

        Returns:
            True if rotation resumed successfully, False otherwise
        """
        with self.rotation_lock:
            self.is_paused = False
            self.state["is_paused"] = False
            self.config_manager.update_state(self.state)

        if self.mqtt_client:
            self.mqtt_client.publish_status()

        logger.info("URL rotation resumed")
        return True

    def jump_to_url(self, index: int) -> bool:
        """
        Jump to a specific URL by index.

        Args:
            index: URL index to jump to

        Returns:
            True if jump successful, False otherwise
        """
        if not self.urls:
            logger.error("No URLs configured")
            return False

        if index < 0 or index >= len(self.urls):
            logger.error("Invalid URL index: %d", index)
            return False

        with self.rotation_lock:
            self.current_index = index
            self.state["current_index"] = index
            self.config_manager.update_state(self.state)

            # Navigate to the URL immediately
            if self.browser_manager and self.browser_manager.is_initialized:
                url = self.urls[index].get("url", "")
                if not self.browser_manager.navigate_to_url(url):
                    logger.error("Failed to navigate to URL: %s", url)
                    return False

            # Update state
            self.state["current_url"] = self.urls[index].get("url", "")
            self.current_url_start_time = time.time()
            self.config_manager.update_state(self.state)

        if self.mqtt_client:
            self.mqtt_client.publish_status()

        logger.info("Jumped to URL index: %d", index)
        return True

    def next_url(self) -> bool:
        """
        Move to the next URL.

        Returns:
            True if move successful, False otherwise
        """
        if not self.urls:
            return False

        next_index = (self.current_index + 1) % len(self.urls)
        return self.jump_to_url(next_index)

    def add_url(self, url_config: dict[str, Any], index: int | None = None) -> bool:
        """
        Add a new URL to the rotation.

        Args:
            url_config: URL configuration dictionary
            index: Position to insert URL, or None for end

        Returns:
            True if URL added successfully, False otherwise
        """
        try:
            if index is None:
                self.urls.append(url_config)
            else:
                self.urls.insert(index, url_config)

            # Update configuration
            if "display" not in self.config:
                self.config["display"] = {}
            self.config["display"]["urls"] = self.urls
            self.config_manager.save_config(self.config)

            logger.info("Added URL: %s", url_config.get("url", ""))
        except Exception:
            logger.exception("Failed to add URL")
            return False
        else:
            return True

    def remove_url(self, index: int) -> bool:
        """
        Remove a URL from the rotation.

        Args:
            index: Index of URL to remove

        Returns:
            True if URL removed successfully, False otherwise
        """
        if index < 0 or index >= len(self.urls):
            logger.error("Invalid URL index: %d", index)
            return False

        try:
            removed_url = self.urls.pop(index)
            logger.info("Removed URL: %s", removed_url.get("url", ""))

            # Adjust current index if necessary
            if self.urls and self.current_index >= len(self.urls):
                self.current_index = 0

            # Update configuration and state
            if "display" not in self.config:
                self.config["display"] = {}
            self.config["display"]["urls"] = self.urls
            self.config_manager.save_config(self.config)
            self.state["current_index"] = self.current_index
            self.config_manager.update_state(self.state)
        except Exception:
            logger.exception("Failed to remove URL")
            return False
        else:
            return True

    def reload_config(self) -> bool:
        """
        Reload configuration from file.

        Returns:
            True if reload successful, False otherwise
        """
        try:
            # Use current config if it's already set, otherwise load from file
            if not hasattr(self, "config") or self.config is None:
                self.config = self.config_manager.load_config()

            display_config = self.config.get("display", {})
            self.urls = display_config.get("urls", [])
            self.default_duration = display_config.get("default_duration", 30)

            # Ensure current index is valid
            if self.urls and self.current_index >= len(self.urls):
                self.current_index = 0
                self.state["current_index"] = 0
                self.config_manager.update_state(self.state)

            logger.info("Configuration reloaded successfully")
        except Exception:
            logger.exception("Failed to reload configuration")
            return False
        else:
            return True

    def get_status(self) -> dict[str, Any]:
        """
        Get current display status.

        Returns:
            Dictionary containing current status information
        """
        # Calculate uptime
        uptime = 0
        if self.state.get("start_time"):
            try:
                start_time = datetime.fromisoformat(self.state["start_time"])
                uptime = int((datetime.now(timezone.utc) - start_time).total_seconds())
            except (ValueError, TypeError):
                uptime = 0

        status = {
            "status": "running"
            if self.running and not self.is_paused
            else "paused"
            if self.is_paused
            else "stopped",
            "is_running": self.running,
            "is_paused": self.is_paused,
            "current_index": self.current_index,
            "total_urls": len(self.urls),
            "urls": self.urls,
            "uptime": uptime,
        }

        # Add current URL information
        if self.urls and 0 <= self.current_index < len(self.urls):
            current_url_config = self.urls[self.current_index]
            status["current_url"] = current_url_config.get("url", "")
            status["current_duration"] = current_url_config.get(
                "duration",
                self.default_duration,
            )

            # Calculate time remaining
            elapsed_time = time.time() - self.current_url_start_time
            status["time_elapsed"] = int(elapsed_time)
            status["time_remaining"] = max(
                0,
                status["current_duration"] - status["time_elapsed"],
            )

        # Add browser information
        if self.browser_manager:
            status["browser_initialized"] = self.browser_manager.is_initialized
            status["browser_running"] = self.browser_manager.is_browser_running()
            if self.browser_manager.is_browser_running():
                status["browser_url"] = self.browser_manager.get_current_url()
                status["browser_title"] = self.browser_manager.get_page_title()

        # Add MQTT information
        if self.mqtt_client:
            status["mqtt_connected"] = self.mqtt_client.is_connected

        return status

    def shutdown(self) -> bool:
        """
        Shutdown the display manager.

        Returns:
            True if shutdown successful, False otherwise
        """
        try:
            # Stop rotation
            self.running = False
            if self.rotation_thread and self.rotation_thread.is_alive():
                self.rotation_thread.join(timeout=5)

            # Shutdown browser
            if self.browser_manager:
                self.browser_manager.shutdown()

            logger.info("Display manager shutdown complete")
        except Exception:
            logger.exception("Error during shutdown")
            return False
        else:
            return True
