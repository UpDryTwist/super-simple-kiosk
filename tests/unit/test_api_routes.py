"""Unit tests for API routes module."""

import json
from unittest.mock import Mock, patch

import pytest
from flask import Flask
from flask.testing import FlaskClient

from super_simple_kiosk.app.api.routes import (
    bp,
    get_browser_manager,
    get_config_manager,
    get_display_manager,
    get_mqtt_client,
    validate_config_data,
)


class TestAPIRoutes:
    """Test API routes functionality."""

    @pytest.fixture
    def app(self) -> Flask:
        """Create a test Flask app."""
        app = Flask(__name__)
        app.config.update(
            {
                "APPLICATION_ROOT": "/",
                "PREFERRED_URL_SCHEME": "http",
                "SERVER_NAME": "localhost",
                "SECRET_KEY": "test-secret-key",
                "PROPAGATE_EXCEPTIONS": True,
                "SESSION_COOKIE_NAME": "session",
                "SESSION_COOKIE_SECURE": False,
                "SESSION_COOKIE_HTTPONLY": True,
                "SESSION_COOKIE_SAMESITE": "Lax",
                "SESSION_COOKIE_DOMAIN": None,
                "SESSION_COOKIE_PATH": "/",
                "DEBUG": False,
                "TRAP_HTTP_EXCEPTIONS": False,
                "TRAP_BAD_REQUEST_ERRORS": False,
                "MAX_CONTENT_LENGTH": 16 * 1024 * 1024,  # 16MB
                "TESTING": True,
            },
        )
        app.register_blueprint(bp)
        return app

    @pytest.fixture
    def client(self, app: Flask) -> FlaskClient:
        """Create a test client."""
        return app.test_client()

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

    def test_health_check_endpoint(self, client: FlaskClient) -> None:
        """Test health check endpoint."""
        response = client.get("/api/health")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"
        assert "message" in data

    def test_get_config_endpoint_success(self, client: FlaskClient) -> None:
        """Test get config endpoint with success."""
        mock_config = {
            "mqtt": {"broker_host": "localhost"},
            "display": {"urls": ["http://example.com"]},
        }

        with patch(
            "super_simple_kiosk.app.api.routes.get_config_manager",
        ) as mock_get_manager:
            mock_manager = Mock()
            mock_manager.load_config.return_value = mock_config
            mock_get_manager.return_value = mock_manager

            response = client.get("/api/config")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"
        assert data["data"] == mock_config

    def test_get_config_endpoint_no_manager(self, client: FlaskClient) -> None:
        """Test get config endpoint when no config manager is available."""
        with patch(
            "super_simple_kiosk.app.api.routes.get_config_manager",
        ) as mock_get_manager:
            mock_get_manager.return_value = None

            response = client.get("/api/config")

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["status"] == "error"

    def test_get_config_endpoint_manager_error(self, client: FlaskClient) -> None:
        """Test get config endpoint when config manager raises an error."""
        with patch(
            "super_simple_kiosk.app.api.routes.get_config_manager",
        ) as mock_get_manager:
            mock_manager = Mock()
            mock_manager.load_config.side_effect = Exception("Config error")
            mock_get_manager.return_value = mock_manager

            response = client.get("/api/config")

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["status"] == "error"

    def test_update_config_endpoint_success(self, client: FlaskClient) -> None:
        """Test update config endpoint with success."""
        mock_config = {
            "mqtt": {"broker_host": "localhost"},
            "display": {"urls": ["http://example.com"]},
        }

        with patch(
            "super_simple_kiosk.app.api.routes.get_config_manager",
        ) as mock_get_manager:
            mock_manager = Mock()
            mock_manager.save_config.return_value = True
            mock_get_manager.return_value = mock_manager

            response = client.put(
                "/api/config",
                data=json.dumps(mock_config),
                content_type="application/json",
            )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"

    def test_update_config_endpoint_invalid_data(self, client: FlaskClient) -> None:
        """Test update config endpoint with invalid data."""
        invalid_data = "not valid json"

        with patch(
            "super_simple_kiosk.app.api.routes.get_config_manager",
        ) as mock_config_manager:
            mock_config = Mock()
            mock_config_manager.return_value = mock_config

            with patch(
                "super_simple_kiosk.app.api.routes.get_display_manager",
            ) as mock_display_manager:
                mock_display = Mock()
                mock_display_manager.return_value = mock_display

                response = client.put(
                    "/api/config",
                    data=invalid_data,
                    content_type="application/json",
                )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["status"] == "error"

    def test_update_config_endpoint_no_manager(self, client: FlaskClient) -> None:
        """Test update config endpoint when no config manager is available."""
        mock_config = {
            "mqtt": {"broker_host": "localhost"},
            "display": {"urls": ["http://example.com"]},
        }

        with patch(
            "super_simple_kiosk.app.api.routes.get_config_manager",
        ) as mock_get_manager:
            mock_get_manager.return_value = None

            response = client.put(
                "/api/config",
                data=json.dumps(mock_config),
                content_type="application/json",
            )

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["status"] == "error"

    def test_reload_config_endpoint_success(self, client: FlaskClient) -> None:
        """Test reload config endpoint with success."""
        with patch(
            "super_simple_kiosk.app.api.routes.get_config_manager",
        ) as mock_get_manager:
            mock_manager = Mock()
            mock_manager.load_config.return_value = {"urls": ["http://example.com"]}
            mock_get_manager.return_value = mock_manager

            response = client.post("/api/config/reload")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"

    def test_reload_config_endpoint_no_manager(self, client: FlaskClient) -> None:
        """Test reload config endpoint when no config manager is available."""
        with patch(
            "super_simple_kiosk.app.api.routes.get_config_manager",
        ) as mock_get_manager:
            mock_get_manager.return_value = None

            response = client.post("/api/config/reload")

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["status"] == "error"

    def test_get_status_endpoint_success(self, client: FlaskClient) -> None:
        """Test get status endpoint with success."""
        mock_status = {
            "is_running": True,
            "current_url": "http://example.com",
            "current_index": 0,
        }

        with patch(
            "super_simple_kiosk.app.api.routes.get_display_manager",
        ) as mock_get_manager:
            mock_manager = Mock()
            mock_manager.get_status.return_value = mock_status
            mock_get_manager.return_value = mock_manager

            response = client.get("/api/status")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"
        assert data["data"] == mock_status

    def test_get_status_endpoint_no_manager(self, client: FlaskClient) -> None:
        """Test get status endpoint when no display manager is available."""
        with patch(
            "super_simple_kiosk.app.api.routes.get_display_manager",
        ) as mock_get_manager:
            mock_get_manager.return_value = None

            response = client.get("/api/status")

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["status"] == "error"

    def test_pause_rotation_endpoint_success(self, client: FlaskClient) -> None:
        """Test pause rotation endpoint with success."""
        with patch(
            "super_simple_kiosk.app.api.routes.get_display_manager",
        ) as mock_get_manager:
            mock_manager = Mock()
            mock_manager.pause_rotation.return_value = True
            mock_get_manager.return_value = mock_manager

            response = client.post("/api/control/pause")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"

    def test_pause_rotation_endpoint_no_manager(self, client: FlaskClient) -> None:
        """Test pause rotation endpoint when no display manager is available."""
        with patch(
            "super_simple_kiosk.app.api.routes.get_display_manager",
        ) as mock_get_manager:
            mock_get_manager.return_value = None

            response = client.post("/api/control/pause")

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["status"] == "error"

    def test_resume_rotation_endpoint_success(self, client: FlaskClient) -> None:
        """Test resume rotation endpoint with success."""
        with patch(
            "super_simple_kiosk.app.api.routes.get_display_manager",
        ) as mock_get_manager:
            mock_manager = Mock()
            mock_manager.resume_rotation.return_value = True
            mock_get_manager.return_value = mock_manager

            response = client.post("/api/control/resume")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"

    def test_resume_rotation_endpoint_no_manager(self, client: FlaskClient) -> None:
        """Test resume rotation endpoint when no display manager is available."""
        with patch(
            "super_simple_kiosk.app.api.routes.get_display_manager",
        ) as mock_get_manager:
            mock_get_manager.return_value = None

            response = client.post("/api/control/resume")

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["status"] == "error"

    def test_jump_to_url_endpoint_success(self, client: FlaskClient) -> None:
        """Test jump to URL endpoint with success."""
        with patch(
            "super_simple_kiosk.app.api.routes.get_display_manager",
        ) as mock_get_manager:
            mock_manager = Mock()
            mock_manager.jump_to_url.return_value = True
            mock_get_manager.return_value = mock_manager

            response = client.post("/api/control/jump/0")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"

    def test_jump_to_url_endpoint_invalid_index(self, client: FlaskClient) -> None:
        """Test jump to URL endpoint with invalid index."""
        with patch(
            "super_simple_kiosk.app.api.routes.get_display_manager",
        ) as mock_get_manager:
            mock_manager = Mock()
            mock_manager.jump_to_url.return_value = False  # Invalid index
            mock_get_manager.return_value = mock_manager

            response = client.post("/api/control/jump/999")  # Use numeric index

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["status"] == "error"

    def test_jump_to_url_endpoint_no_manager(self, client: FlaskClient) -> None:
        """Test jump to URL endpoint when no display manager is available."""
        with patch(
            "super_simple_kiosk.app.api.routes.get_display_manager",
        ) as mock_get_manager:
            mock_get_manager.return_value = None

            response = client.post("/api/control/jump/0")

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["status"] == "error"

    def test_next_url_endpoint_success(self, client: FlaskClient) -> None:
        """Test next URL endpoint with success."""
        with patch(
            "super_simple_kiosk.app.api.routes.get_display_manager",
        ) as mock_get_manager:
            mock_manager = Mock()
            mock_manager.next_url.return_value = True
            mock_get_manager.return_value = mock_manager

            response = client.post("/api/control/next")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"

    def test_next_url_endpoint_no_manager(self, client: FlaskClient) -> None:
        """Test next URL endpoint when no display manager is available."""
        with patch(
            "super_simple_kiosk.app.api.routes.get_display_manager",
        ) as mock_get_manager:
            mock_get_manager.return_value = None

            response = client.post("/api/control/next")

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["status"] == "error"

    def test_get_urls_endpoint_success(self, client: FlaskClient) -> None:
        """Test get URLs endpoint with success."""
        mock_config = {"urls": ["http://example1.com", "http://example2.com"]}

        with patch(
            "super_simple_kiosk.app.api.routes.get_config_manager",
        ) as mock_get_manager:
            mock_manager = Mock()
            mock_manager.load_config.return_value = mock_config
            mock_get_manager.return_value = mock_manager

            response = client.get("/api/urls")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"
        assert data["data"]["urls"] == mock_config["urls"]

    def test_get_urls_endpoint_no_manager(self, client: FlaskClient) -> None:
        """Test get URLs endpoint when no config manager is available."""
        with patch(
            "super_simple_kiosk.app.api.routes.get_config_manager",
        ) as mock_get_manager:
            mock_get_manager.return_value = None

            response = client.get("/api/urls")

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["status"] == "error"

    def test_add_url_endpoint_success(self, client: FlaskClient) -> None:
        """Test add URL endpoint with success."""
        url_data = {"url": "http://example.com"}

        with patch(
            "super_simple_kiosk.app.api.routes.get_display_manager",
        ) as mock_get_manager:
            mock_manager = Mock()
            mock_manager.add_url.return_value = True
            mock_get_manager.return_value = mock_manager

            with patch(
                "super_simple_kiosk.app.api.routes.get_config_manager",
            ) as mock_config_manager:
                mock_config = Mock()
                mock_config.load_config.return_value = {"urls": ["http://existing.com"]}
                mock_config_manager.return_value = mock_config

                response = client.post(
                    "/api/urls",
                    data=json.dumps(url_data),
                    content_type="application/json",
                )

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["status"] == "success"

    def test_add_url_endpoint_invalid_data(self, client: FlaskClient) -> None:
        """Test add URL endpoint with invalid data."""
        invalid_data = "not valid json"

        with patch(
            "super_simple_kiosk.app.api.routes.get_display_manager",
        ) as mock_get_manager:
            mock_manager = Mock()
            mock_get_manager.return_value = mock_manager

            response = client.post(
                "/api/urls",
                data=invalid_data,
                content_type="application/json",
            )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["status"] == "error"

    def test_add_url_endpoint_no_manager(self, client: FlaskClient) -> None:
        """Test add URL endpoint when no config manager is available."""
        url_data = {"url": "http://example.com"}

        with patch(
            "super_simple_kiosk.app.api.routes.get_display_manager",
        ) as mock_get_manager:
            mock_get_manager.return_value = None

            response = client.post(
                "/api/urls",
                data=json.dumps(url_data),
                content_type="application/json",
            )

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["status"] == "error"

    def test_update_url_endpoint_success(self, client: FlaskClient) -> None:
        """Test update URL endpoint with success."""
        url_data = {"url": "http://updated.com"}

        with patch(
            "super_simple_kiosk.app.api.routes.get_config_manager",
        ) as mock_get_manager:
            mock_manager = Mock()
            mock_manager.load_config.return_value = {"urls": ["http://existing.com"]}
            mock_manager.save_config.return_value = True
            mock_get_manager.return_value = mock_manager

            with patch(
                "super_simple_kiosk.app.api.routes.get_display_manager",
            ) as mock_display_manager:
                mock_display = Mock()
                mock_display.reload_config.return_value = True
                mock_display_manager.return_value = mock_display

                response = client.put(
                    "/api/urls/0",
                    data=json.dumps(url_data),
                    content_type="application/json",
                )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"

    def test_update_url_endpoint_invalid_index(self, client: FlaskClient) -> None:
        """Test update URL endpoint with invalid index."""
        url_data = {"url": "http://updated.com"}

        with patch(
            "super_simple_kiosk.app.api.routes.get_config_manager",
        ) as mock_get_manager:
            mock_manager = Mock()
            mock_manager.load_config.return_value = {
                "urls": ["http://existing.com"],
            }  # Only 1 URL
            mock_get_manager.return_value = mock_manager

            with patch(
                "super_simple_kiosk.app.api.routes.get_display_manager",
            ) as mock_display_manager:
                mock_display = Mock()
                mock_display.reload_config.return_value = True
                mock_display_manager.return_value = mock_display

                response = client.put(
                    "/api/urls/999",  # Index out of bounds
                    data=json.dumps(url_data),
                    content_type="application/json",
                )

        assert response.status_code == 404
        data = json.loads(response.data)
        assert data["status"] == "error"

    def test_delete_url_endpoint_success(self, client: FlaskClient) -> None:
        """Test delete URL endpoint with success."""
        with patch(
            "super_simple_kiosk.app.api.routes.get_display_manager",
        ) as mock_get_manager:
            mock_manager = Mock()
            mock_manager.remove_url.return_value = True
            mock_get_manager.return_value = mock_manager

            response = client.delete("/api/urls/0")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"

    def test_delete_url_endpoint_invalid_index(self, client: FlaskClient) -> None:
        """Test delete URL endpoint with invalid index."""
        with patch(
            "super_simple_kiosk.app.api.routes.get_display_manager",
        ) as mock_get_manager:
            mock_manager = Mock()
            mock_manager.remove_url.return_value = False  # Invalid index
            mock_get_manager.return_value = mock_manager

            response = client.delete("/api/urls/999")  # Use numeric index

        assert response.status_code == 404
        data = json.loads(response.data)
        assert data["status"] == "error"

    def test_delete_url_endpoint_no_manager(self, client: FlaskClient) -> None:
        """Test delete URL endpoint when no config manager is available."""
        with patch(
            "super_simple_kiosk.app.api.routes.get_display_manager",
        ) as mock_get_manager:
            mock_get_manager.return_value = None

            response = client.delete("/api/urls/0")

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["status"] == "error"

    def test_restart_system_endpoint_success(self, client: FlaskClient) -> None:
        """Test restart system endpoint with success."""
        with patch(
            "super_simple_kiosk.app.api.routes.get_display_manager",
        ) as mock_get_manager:
            mock_manager = Mock()
            mock_manager.shutdown.return_value = None
            mock_manager.start_rotation.return_value = True
            mock_get_manager.return_value = mock_manager

            response = client.post("/api/system/restart")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"

    def test_restart_system_endpoint_no_manager(self, client: FlaskClient) -> None:
        """Test restart system endpoint when no display manager is available."""
        with patch(
            "super_simple_kiosk.app.api.routes.get_display_manager",
        ) as mock_get_manager:
            mock_get_manager.return_value = None

            response = client.post("/api/system/restart")

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["status"] == "error"
