"""Simple unit tests for API routes module."""

from unittest.mock import Mock, patch

from super_simple_kiosk.app.api.routes import (
    get_browser_manager,
    get_config_manager,
    get_display_manager,
    get_mqtt_client,
    validate_config_data,
)


class TestAPIRoutesSimple:
    """Test API routes functionality with simple tests."""

    def test_get_config_manager_with_manager(self) -> None:
        """Test get_config_manager when manager is available."""
        mock_manager = Mock()
        mock_app = Mock()
        mock_app.config = {"config_manager": mock_manager}

        with patch("super_simple_kiosk.app.api.routes.current_app", mock_app):
            result = get_config_manager()

        assert result == mock_manager

    def test_get_config_manager_without_manager(self) -> None:
        """Test get_config_manager when manager is not available."""
        mock_app = Mock()
        mock_app.config = {}

        with patch("super_simple_kiosk.app.api.routes.current_app", mock_app):
            result = get_config_manager()

        assert result is None

    def test_get_display_manager_with_manager(self) -> None:
        """Test get_display_manager when manager is available."""
        mock_manager = Mock()
        mock_app = Mock()
        mock_app.config = {"display_manager": mock_manager}

        with patch("super_simple_kiosk.app.api.routes.current_app", mock_app):
            result = get_display_manager()

        assert result == mock_manager

    def test_get_display_manager_without_manager(self) -> None:
        """Test get_display_manager when manager is not available."""
        mock_app = Mock()
        mock_app.config = {}

        with patch("super_simple_kiosk.app.api.routes.current_app", mock_app):
            result = get_display_manager()

        assert result is None

    def test_get_browser_manager_with_manager(self) -> None:
        """Test get_browser_manager when manager is available."""
        mock_manager = Mock()
        mock_app = Mock()
        mock_app.config = {"browser_manager": mock_manager}

        with patch("super_simple_kiosk.app.api.routes.current_app", mock_app):
            result = get_browser_manager()

        assert result == mock_manager

    def test_get_browser_manager_without_manager(self) -> None:
        """Test get_browser_manager when manager is not available."""
        mock_app = Mock()
        mock_app.config = {}

        with patch("super_simple_kiosk.app.api.routes.current_app", mock_app):
            result = get_browser_manager()

        assert result is None

    def test_get_mqtt_client_with_client(self) -> None:
        """Test get_mqtt_client when client is available."""
        mock_client = Mock()
        mock_app = Mock()
        mock_app.config = {"mqtt_client": mock_client}

        with patch("super_simple_kiosk.app.api.routes.current_app", mock_app):
            result = get_mqtt_client()

        assert result == mock_client

    def test_get_mqtt_client_without_client(self) -> None:
        """Test get_mqtt_client when client is not available."""
        mock_app = Mock()
        mock_app.config = {}

        with patch("super_simple_kiosk.app.api.routes.current_app", mock_app):
            result = get_mqtt_client()

        assert result is None

    def test_validate_config_data_valid(self) -> None:
        """Test validate_config_data with valid data."""
        valid_data = {
            "mqtt": {"broker_host": "localhost", "broker_port": 1883},
            "display": {"urls": ["http://example.com"], "rotation_interval": 30},
        }

        result = validate_config_data(valid_data)
        assert result is True

    def test_validate_config_data_not_dict(self) -> None:
        """Test validate_config_data with non-dict data."""
        invalid_data = "not a dict"

        result = validate_config_data(invalid_data)
        assert result is False

    def test_validate_config_data_missing_keys(self) -> None:
        """Test validate_config_data with missing required keys."""
        invalid_data = {
            "mqtt": {"broker_host": "localhost"},
            # missing 'display' key
        }

        result = validate_config_data(invalid_data)
        assert result is False

    def test_validate_config_data_mqtt_not_dict(self) -> None:
        """Test validate_config_data with mqtt not being a dict."""
        invalid_data = {"mqtt": "not a dict", "display": {"urls": []}}

        result = validate_config_data(invalid_data)
        assert result is False

    def test_validate_config_data_display_not_dict(self) -> None:
        """Test validate_config_data with display not being a dict."""
        invalid_data = {"mqtt": {"broker_host": "localhost"}, "display": "not a dict"}

        result = validate_config_data(invalid_data)
        assert result is False

    def test_validate_config_data_urls_not_list(self) -> None:
        """Test validate_config_data with urls not being a list."""
        invalid_data = {
            "mqtt": {"broker_host": "localhost"},
            "display": {"urls": "not a list", "rotation_interval": 30},
        }

        result = validate_config_data(invalid_data)
        assert result is False
