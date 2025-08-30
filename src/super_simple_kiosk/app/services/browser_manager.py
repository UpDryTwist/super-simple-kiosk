"""
Browser manager service for Super Simple Kiosk.

This module provides the browser manager service that controls Chromium via Selenium
WebDriver for fullscreen web content display.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait

if TYPE_CHECKING:
    from super_simple_kiosk.app.models.config import ConfigManager

logger = logging.getLogger(__name__)

# Constants
MAX_RETRY_ATTEMPTS = 3


class BrowserManager:
    """Manages the Chromium browser instance via Selenium WebDriver."""

    def __init__(self, config_manager: ConfigManager) -> None:
        """Initialize the browser manager."""
        self.config_manager = config_manager
        self.driver: webdriver.Chrome | None = None
        self.is_initialized = False
        self.error_urls: dict[str, int] = {}

    def initialize(self) -> bool:
        """
        Initialize the browser with Chrome options.

        Returns:
            True if initialization successful, False otherwise
        """
        if self.is_initialized and self.driver:
            return True  # Already initialized

        try:
            chrome_options = Options()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--disable-features=VizDisplayCompositor")
            chrome_options.add_argument("--kiosk")
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_experimental_option(
                "excludeSwitches",
                ["enable-automation"],
            )
            chrome_options.add_experimental_option(
                "useAutomationExtension",
                value=False,
            )

            # Set Chrome binary path if specified
            chrome_binary = os.environ.get("CHROME_BINARY_PATH")
            if chrome_binary:
                chrome_options.binary_location = chrome_binary

            # Set ChromeDriver path if specified
            chromedriver_path = os.environ.get("CHROMEDRIVER_PATH")
            if chromedriver_path:
                service = Service(executable_path=chromedriver_path)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                self.driver = webdriver.Chrome(options=chrome_options)

            # Set page load timeout
            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(10)

            # Execute script to remove webdriver property
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
            )

            self.is_initialized = True
            logger.info("Browser initialized successfully")
        except Exception:
            logger.exception("Failed to initialize browser")
            self.driver = None
            self.is_initialized = False
            return False
        else:
            return True

    def navigate_to_url(self, url: str) -> bool:
        """
        Navigate to a specific URL.

        Args:
            url: URL to navigate to

        Returns:
            True if navigation successful, False otherwise
        """
        if not self.driver:
            logger.error("Browser not initialized")
            return False

        try:
            self.driver.get(url)
            logger.info("Navigated to URL: %s", url)
            # Clear error count for successful navigation
            self.error_urls.pop(url, None)
        except TimeoutException:
            logger.exception("Timeout navigating to URL: %s", url)
            self._handle_url_error(url)
            return False
        except WebDriverException:
            logger.exception("Failed to navigate to URL %s", url)
            self._handle_url_error(url)
            return False
        else:
            return True

    def _handle_url_error(self, url: str) -> None:
        """Handle URL navigation errors by incrementing error count."""
        self.error_urls[url] = self.error_urls.get(url, 0) + 1
        logger.warning("Error count for %s: %d", url, self.error_urls[url])

        # Update global error count in config manager
        current_state = self.config_manager.get_state()
        current_state["error_count"] = current_state.get("error_count", 0) + 1
        self.config_manager.update_state(current_state)

    def should_retry_url(self, url: str) -> bool:
        """
        Check if a URL should be retried based on error count.

        Args:
            url: URL to check

        Returns:
            True if URL should be retried, False otherwise
        """
        error_count = self.error_urls.get(url, 0)
        return error_count < MAX_RETRY_ATTEMPTS

    def refresh_current_page(self) -> bool:
        """
        Refresh the current page.

        Returns:
            True if refresh successful, False otherwise
        """
        if not self.driver:
            logger.error("Browser not initialized")
            return False

        try:
            self.driver.refresh()
            logger.info("Page refreshed successfully")
        except WebDriverException:
            logger.exception("Failed to refresh page")
            return False
        else:
            return True

    def shutdown(self) -> None:
        """Shutdown the browser and clean up resources."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser shutdown successfully")
            except Exception:
                logger.exception("Error during browser shutdown")
            finally:
                self.driver = None
                self.is_initialized = False

    def get_current_url(self) -> str | None:
        """
        Get the current URL.

        Returns:
            Current URL or None if not available
        """
        if not self.driver:
            return None

        try:
            return self.driver.current_url
        except WebDriverException:
            return None

    def is_browser_running(self) -> bool:
        """
        Check if the browser is running.

        Returns:
            True if browser is running, False otherwise
        """
        return self.driver is not None and self.is_initialized

    def get_chrome_version(self) -> str:
        """
        Get the Chrome version.

        Returns:
            Chrome version string
        """
        if not self.driver:
            return ""

        try:
            return self.driver.capabilities.get("browserVersion", "")
        except Exception:
            logger.exception("Error getting Chrome version")
            return ""

    def wait_for_page_load(self, timeout: int = 10) -> bool:
        """
        Wait for the page to load completely.

        Args:
            timeout: Timeout in seconds

        Returns:
            True if page loaded successfully, False otherwise
        """
        if not self.driver:
            return False

        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete",
            )
        except TimeoutException:
            logger.warning("Page load timeout after %d seconds", timeout)
            return False
        except WebDriverException:
            logger.exception("Error waiting for page load")
            return False
        else:
            return True

    def execute_javascript(self, script: str) -> str | None:
        """
        Execute JavaScript code in the browser.

        Args:
            script: JavaScript code to execute

        Returns:
            Result of JavaScript execution or None if failed
        """
        if not self.driver:
            logger.error("Browser not initialized")
            return None

        try:
            result = self.driver.execute_script(script)
            logger.debug("JavaScript executed successfully: %s", script)
            return str(result) if result is not None else None
        except WebDriverException:
            logger.exception("Failed to execute JavaScript")
            return None

    def take_screenshot(self, filepath: str) -> bool:
        """
        Take a screenshot of the current page.

        Args:
            filepath: Path to save the screenshot

        Returns:
            True if screenshot taken successfully, False otherwise
        """
        if not self.driver:
            logger.error("Browser not initialized")
            return False

        try:
            self.driver.save_screenshot(filepath)
            logger.info("Screenshot saved to: %s", filepath)
        except Exception:
            logger.exception("Failed to take screenshot")
            return False
        else:
            return True

    def get_page_title(self) -> str:
        """
        Get the current page title.

        Returns:
            Page title or empty string if not available
        """
        if not self.driver:
            return ""

        try:
            return self.driver.title
        except WebDriverException:
            return ""

    def clear_error_history(self, url: str | None = None) -> None:
        """
        Clear error history for URLs.

        Args:
            url: Specific URL to clear, or None to clear all
        """
        if url:
            self.error_urls.pop(url, None)
            logger.info("Cleared error history for URL: %s", url)
        else:
            self.error_urls.clear()
            logger.info("Cleared all error history")

    def get_error_stats(self) -> dict[str, int]:
        """
        Get error statistics for URLs.

        Returns:
            Dictionary mapping URLs to error counts
        """
        return self.error_urls.copy()
