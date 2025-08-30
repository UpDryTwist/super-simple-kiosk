"""
Test browser manager service.

This module tests the BrowserManager class for Chromium control via Selenium.
"""

import os
import tempfile
from collections.abc import Generator
from unittest.mock import Mock, patch

import pytest
from selenium.common.exceptions import TimeoutException, WebDriverException

from super_simple_kiosk.app.models.config import ConfigManager
from super_simple_kiosk.app.services.browser_manager import BrowserManager


class TestBrowserManager:
    """Test BrowserManager functionality."""

    def teardown_method(self) -> None:
        """Clean up after each test method."""
        # This ensures that any browser instances are cleaned up even if tests fail

    @pytest.fixture
    def config_manager(self) -> Generator[ConfigManager, None, None]:
        """Create a ConfigManager instance for testing."""
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

        manager = ConfigManager(config_path, state_path)

        yield manager

        # Cleanup
        for path in [config_path, state_path]:
            if os.path.exists(path):
                os.unlink(path)

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
    def mock_driver(self) -> Mock:
        """Create a mock WebDriver instance."""
        driver = Mock()
        driver.capabilities = {"browserVersion": "120.0.6099.109"}
        driver.current_url = "https://example.com"
        driver.title = "Example Domain"
        return driver

    def test_init(self, browser_manager: BrowserManager) -> None:
        """Test BrowserManager initialization."""
        assert browser_manager.config_manager is not None
        assert browser_manager.driver is None
        assert browser_manager.get_current_url() is None
        assert browser_manager.is_initialized is False
        assert browser_manager.error_urls == {}

    @patch("super_simple_kiosk.app.services.browser_manager.webdriver.Chrome")
    def test_initialize_success(
        self,
        mock_chrome: Mock,
        browser_manager: BrowserManager,
        mock_driver: Mock,
    ) -> None:
        """Test successful browser initialization."""
        mock_chrome.return_value = mock_driver

        result = browser_manager.initialize()

        assert result is True
        assert browser_manager.is_initialized is True
        assert browser_manager.driver == mock_driver
        mock_chrome.assert_called_once()

    @patch("super_simple_kiosk.app.services.browser_manager.webdriver.Chrome")
    def test_initialize_failure(
        self,
        mock_chrome: Mock,
        browser_manager: BrowserManager,
    ) -> None:
        """Test browser initialization failure."""
        mock_chrome.side_effect = Exception("Chrome not found")

        result = browser_manager.initialize()

        assert result is False
        assert browser_manager.is_initialized is False
        assert browser_manager.driver is None

    @patch("super_simple_kiosk.app.services.browser_manager.webdriver.Chrome")
    def test_initialize_already_initialized(
        self,
        mock_chrome: Mock,
        browser_manager: BrowserManager,
        mock_driver: Mock,
    ) -> None:
        """Test initialization when already initialized."""
        mock_chrome.return_value = mock_driver
        browser_manager.initialize()

        # Second initialization should return True without creating new driver
        result = browser_manager.initialize()

        assert result is True
        mock_chrome.assert_called_once()  # Should only be called once

    @patch("super_simple_kiosk.app.services.browser_manager.webdriver.Chrome")
    def test_navigate_to_url_success(
        self,
        mock_chrome: Mock,
        browser_manager: BrowserManager,
        mock_driver: Mock,
    ) -> None:
        """Test successful URL navigation."""
        mock_chrome.return_value = mock_driver
        browser_manager.initialize()  # Initialize first
        url = "https://example.com"

        # Mock the WebDriverWait to return successfully
        with patch(
            "super_simple_kiosk.app.services.browser_manager.WebDriverWait",
        ) as mock_wait:
            mock_wait.return_value.until.return_value = True
            result = browser_manager.navigate_to_url(url)

        assert result is True
        # The BrowserManager doesn't store current_url, it gets it from driver
        mock_driver.get.assert_called_with(url)

    @patch("super_simple_kiosk.app.services.browser_manager.webdriver.Chrome")
    def test_navigate_to_url_timeout(
        self,
        mock_chrome: Mock,
        browser_manager: BrowserManager,
        mock_driver: Mock,
    ) -> None:
        """Test URL navigation with timeout."""
        mock_chrome.return_value = mock_driver
        browser_manager.initialize()  # Initialize first
        url = "https://slow-site.com"

        # Mock the driver.get to throw TimeoutException
        mock_driver.get.side_effect = TimeoutException("Page load timeout")
        result = browser_manager.navigate_to_url(url)

        assert result is False
        assert url in browser_manager.error_urls
        assert browser_manager.error_urls[url] == 1

    @patch("super_simple_kiosk.app.services.browser_manager.webdriver.Chrome")
    def test_navigate_to_url_webdriver_error(
        self,
        mock_chrome: Mock,
        browser_manager: BrowserManager,
        mock_driver: Mock,
    ) -> None:
        """Test URL navigation with WebDriver error."""
        mock_chrome.return_value = mock_driver
        url = "https://invalid-site.com"

        # First initialize the browser successfully
        browser_manager.initialize()

        # Now set up the error for navigation
        mock_driver.get.side_effect = WebDriverException("Connection failed")

        # Mock the WebDriverWait to return successfully (the error happens in driver.get)
        with patch(
            "super_simple_kiosk.app.services.browser_manager.WebDriverWait",
        ) as mock_wait:
            mock_wait.return_value.until.return_value = True
            result = browser_manager.navigate_to_url(url)

        assert result is False
        assert url in browser_manager.error_urls
        assert browser_manager.error_urls[url] == 1

    def test_should_retry_url_no_errors(self, browser_manager: BrowserManager) -> None:
        """Test retry logic for URL with no errors."""
        url = "https://example.com"

        result = browser_manager.should_retry_url(url)

        assert result is True

    def test_should_retry_url_with_errors(
        self,
        browser_manager: BrowserManager,
    ) -> None:
        """Test retry logic for URL with errors."""
        url = "https://problematic-site.com"
        browser_manager.error_urls[url] = 3

        result = browser_manager.should_retry_url(url)

        assert result is False  # 3 errors >= MAX_RETRY_ATTEMPTS (3)

    def test_should_retry_url_backoff(self, browser_manager: BrowserManager) -> None:
        """Test retry logic with exponential backoff."""
        url = "https://problematic-site.com"
        browser_manager.error_urls[url] = 2

        result = browser_manager.should_retry_url(url)

        assert result is True  # 2 errors < MAX_RETRY_ATTEMPTS (3)

    def test_should_retry_url_max_retries(
        self,
        browser_manager: BrowserManager,
    ) -> None:
        """Test retry logic with maximum retries exceeded."""
        url = "https://failing-site.com"
        browser_manager.error_urls[url] = 10  # Max retries

        result = browser_manager.should_retry_url(url)

        assert result is False  # Should not retry after max attempts

    @patch("super_simple_kiosk.app.services.browser_manager.webdriver.Chrome")
    def test_refresh_current_page_success(
        self,
        mock_chrome: Mock,
        browser_manager: BrowserManager,
        mock_driver: Mock,
    ) -> None:
        """Test successful page refresh."""
        mock_chrome.return_value = mock_driver
        browser_manager.initialize()

        result = browser_manager.refresh_current_page()

        assert result is True
        mock_driver.refresh.assert_called_once()

    @patch("super_simple_kiosk.app.services.browser_manager.webdriver.Chrome")
    def test_refresh_current_page_no_url(
        self,
        mock_chrome: Mock,
        browser_manager: BrowserManager,
        mock_driver: Mock,
    ) -> None:
        """Test page refresh when no URL is set."""
        mock_chrome.return_value = mock_driver
        browser_manager.initialize()
        # BrowserManager doesn't store current_url, it gets it from driver

        result = browser_manager.refresh_current_page()

        assert result is True  # Should succeed if driver is initialized

    @patch("super_simple_kiosk.app.services.browser_manager.webdriver.Chrome")
    def test_refresh_current_page_error(
        self,
        mock_chrome: Mock,
        browser_manager: BrowserManager,
        mock_driver: Mock,
    ) -> None:
        """Test page refresh with error."""
        mock_chrome.return_value = mock_driver
        browser_manager.initialize()
        mock_driver.refresh.side_effect = WebDriverException("Refresh failed")

        result = browser_manager.refresh_current_page()

        assert result is False

    @patch("super_simple_kiosk.app.services.browser_manager.webdriver.Chrome")
    def test_shutdown(
        self,
        mock_chrome: Mock,
        browser_manager: BrowserManager,
        mock_driver: Mock,
    ) -> None:
        """Test browser shutdown."""
        mock_chrome.return_value = mock_driver
        browser_manager.initialize()

        browser_manager.shutdown()

        assert browser_manager.driver is None
        assert browser_manager.is_initialized is False
        # get_current_url() returns None when driver is None
        assert browser_manager.get_current_url() is None
        mock_driver.quit.assert_called_once()

    @patch("super_simple_kiosk.app.services.browser_manager.webdriver.Chrome")
    def test_shutdown_error(
        self,
        mock_chrome: Mock,
        browser_manager: BrowserManager,
        mock_driver: Mock,
    ) -> None:
        """Test browser shutdown with error."""
        mock_chrome.return_value = mock_driver
        browser_manager.initialize()
        mock_driver.quit.side_effect = Exception("Quit failed")

        browser_manager.shutdown()

        # Should still clean up even if quit fails
        assert browser_manager.driver is None
        assert browser_manager.is_initialized is False

    @patch("super_simple_kiosk.app.services.browser_manager.webdriver.Chrome")
    def test_get_current_url(
        self,
        mock_chrome: Mock,
        browser_manager: BrowserManager,
        mock_driver: Mock,
    ) -> None:
        """Test getting current URL."""
        mock_chrome.return_value = mock_driver
        browser_manager.initialize()

        result = browser_manager.get_current_url()

        assert result == "https://example.com"

    def test_get_current_url_no_driver(self, browser_manager: BrowserManager) -> None:
        """Test getting current URL when no driver exists."""
        result = browser_manager.get_current_url()

        assert result is None

    @patch("super_simple_kiosk.app.services.browser_manager.webdriver.Chrome")
    def test_is_browser_running_true(
        self,
        mock_chrome: Mock,
        browser_manager: BrowserManager,
        mock_driver: Mock,
    ) -> None:
        """Test browser running status when running."""
        mock_chrome.return_value = mock_driver
        browser_manager.initialize()

        result = browser_manager.is_browser_running()

        assert result is True

    def test_is_browser_running_false(self, browser_manager: BrowserManager) -> None:
        """Test browser running status when not running."""
        result = browser_manager.is_browser_running()

        assert result is False

    @patch("super_simple_kiosk.app.services.browser_manager.webdriver.Chrome")
    def test_get_chrome_version(
        self,
        mock_chrome: Mock,
        browser_manager: BrowserManager,
        mock_driver: Mock,
    ) -> None:
        """Test getting Chrome version."""
        mock_chrome.return_value = mock_driver
        browser_manager.initialize()

        result = browser_manager.get_chrome_version()

        assert result == "120.0.6099.109"

    def test_get_chrome_version_no_driver(
        self,
        browser_manager: BrowserManager,
    ) -> None:
        """Test getting Chrome version when no driver exists."""
        result = browser_manager.get_chrome_version()

        assert result == ""

    @patch("super_simple_kiosk.app.services.browser_manager.webdriver.Chrome")
    def test_wait_for_page_load_success(
        self,
        mock_chrome: Mock,
        browser_manager: BrowserManager,
        mock_driver: Mock,
    ) -> None:
        """Test waiting for page load success."""
        mock_chrome.return_value = mock_driver
        mock_driver.execute_script.return_value = "complete"
        browser_manager.initialize()

        result = browser_manager.wait_for_page_load()

        assert result is True

    @patch("super_simple_kiosk.app.services.browser_manager.webdriver.Chrome")
    def test_wait_for_page_load_timeout(
        self,
        mock_chrome: Mock,
        browser_manager: BrowserManager,
        mock_driver: Mock,
    ) -> None:
        """Test waiting for page load timeout."""
        mock_chrome.return_value = mock_driver
        mock_driver.execute_script.side_effect = TimeoutException("Timeout")
        browser_manager.initialize()

        result = browser_manager.wait_for_page_load(timeout=1)

        assert result is False

    @patch("super_simple_kiosk.app.services.browser_manager.webdriver.Chrome")
    def test_execute_javascript_success(
        self,
        mock_chrome: Mock,
        browser_manager: BrowserManager,
        mock_driver: Mock,
    ) -> None:
        """Test JavaScript execution success."""
        mock_chrome.return_value = mock_driver
        mock_driver.execute_script.return_value = "Hello World"
        browser_manager.initialize()

        result = browser_manager.execute_javascript("return 'Hello World';")

        assert result == "Hello World"

    @patch("super_simple_kiosk.app.services.browser_manager.webdriver.Chrome")
    def test_execute_javascript_error(
        self,
        mock_chrome: Mock,
        browser_manager: BrowserManager,
        mock_driver: Mock,
    ) -> None:
        """Test JavaScript execution error."""
        mock_chrome.return_value = mock_driver
        mock_driver.execute_script.side_effect = Exception("JS Error")
        browser_manager.initialize()

        result = browser_manager.execute_javascript("invalid javascript;")

        assert result is None

    @patch("super_simple_kiosk.app.services.browser_manager.webdriver.Chrome")
    def test_take_screenshot_success(
        self,
        mock_chrome: Mock,
        browser_manager: BrowserManager,
        mock_driver: Mock,
    ) -> None:
        """Test taking screenshot success."""
        mock_chrome.return_value = mock_driver
        browser_manager.initialize()

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            screenshot_path = temp_file.name

        try:
            result = browser_manager.take_screenshot(screenshot_path)

            assert result is True
            mock_driver.save_screenshot.assert_called_with(screenshot_path)
        finally:
            if os.path.exists(screenshot_path):
                os.unlink(screenshot_path)

    @patch("super_simple_kiosk.app.services.browser_manager.webdriver.Chrome")
    def test_take_screenshot_error(
        self,
        mock_chrome: Mock,
        browser_manager: BrowserManager,
        mock_driver: Mock,
    ) -> None:
        """Test taking screenshot error."""
        mock_chrome.return_value = mock_driver
        mock_driver.save_screenshot.side_effect = Exception("Screenshot failed")
        browser_manager.initialize()

        result = browser_manager.take_screenshot("/invalid/path/screenshot.png")

        assert result is False

    @patch("super_simple_kiosk.app.services.browser_manager.webdriver.Chrome")
    def test_get_page_title(
        self,
        mock_chrome: Mock,
        browser_manager: BrowserManager,
        mock_driver: Mock,
    ) -> None:
        """Test getting page title."""
        mock_chrome.return_value = mock_driver
        browser_manager.initialize()

        result = browser_manager.get_page_title()

        assert result == "Example Domain"

    def test_get_page_title_no_driver(self, browser_manager: BrowserManager) -> None:
        """Test getting page title when no driver exists."""
        result = browser_manager.get_page_title()

        assert result == ""

    def test_clear_error_history_specific_url(
        self,
        browser_manager: BrowserManager,
    ) -> None:
        """Test clearing error history for specific URL."""
        url = "https://problematic-site.com"
        browser_manager.error_urls[url] = 5
        browser_manager.error_urls["https://another-site.com"] = 3

        browser_manager.clear_error_history(url)

        assert url not in browser_manager.error_urls
        assert "https://another-site.com" in browser_manager.error_urls

    def test_clear_error_history_all(self, browser_manager: BrowserManager) -> None:
        """Test clearing all error history."""
        browser_manager.error_urls["https://site1.com"] = 1
        browser_manager.error_urls["https://site2.com"] = 2

        browser_manager.clear_error_history()

        assert len(browser_manager.error_urls) == 0

    def test_get_error_stats(self, browser_manager: BrowserManager) -> None:
        """Test getting error statistics."""
        browser_manager.error_urls["https://site1.com"] = 3
        browser_manager.error_urls["https://site2.com"] = 7

        stats = browser_manager.get_error_stats()

        assert stats["https://site1.com"] == 3
        assert stats["https://site2.com"] == 7
        assert len(stats) == 2

    def test_handle_url_error(self, browser_manager: BrowserManager) -> None:
        """Test handling URL errors."""
        url = "https://failing-site.com"
        initial_error_count = browser_manager.config_manager.get_state()["error_count"]

        browser_manager._handle_url_error(url)

        assert url in browser_manager.error_urls
        assert browser_manager.error_urls[url] == 1
        # Verify error count was incremented
        assert browser_manager.error_urls[url] == 1

        # Check that global error count was incremented
        new_error_count = browser_manager.config_manager.get_state()["error_count"]
        assert new_error_count == initial_error_count + 1

    def test_handle_url_error_multiple(self, browser_manager: BrowserManager) -> None:
        """Test handling multiple URL errors."""
        url = "https://failing-site.com"
        browser_manager._handle_url_error(url)
        browser_manager._handle_url_error(url)

        assert browser_manager.error_urls[url] == 2
