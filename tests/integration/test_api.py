"""
Test Flask application structure and basic functionality.

This module tests the Flask application factory and basic endpoint functionality.
"""

import pytest
from flask import Flask

from super_simple_kiosk.app import create_app


@pytest.mark.integration
class TestFlaskApp:
    """Test Flask application functionality."""

    def test_create_app(self) -> None:
        """Test that the Flask app factory creates a valid application."""
        app = create_app()

        assert isinstance(app, Flask)
        assert app.name == "super_simple_kiosk.app"

    def test_create_app_with_test_config(self) -> None:
        """Test that the Flask app factory accepts test configuration."""
        test_config = {
            "TESTING": True,
            "SECRET_KEY": "test-key",
            "CONFIG_FILE": "test_config.yaml",
            "STATE_FILE": "test_state.json",
        }

        app = create_app(test_config)

        assert app.config["TESTING"] is True
        assert app.config["SECRET_KEY"] == "test-key"  # noqa: S105
        assert app.config["CONFIG_FILE"] == "test_config.yaml"
        assert app.config["STATE_FILE"] == "test_state.json"

    def test_blueprint_registration(self) -> None:
        """Test that the API blueprint is registered."""
        app = create_app()

        # Check that the API blueprint is registered
        assert "api" in app.blueprints
        assert app.blueprints["api"].url_prefix == "/api"

    def test_health_endpoint(self) -> None:
        """Test the health check endpoint."""
        app = create_app()

        with app.test_client() as client:
            response = client.get("/api/health")

            assert response.status_code == 200
            data = response.get_json()
            assert data["status"] == "success"
            assert data["message"] == "Health check completed successfully"
            assert "data" in data
            # Check health data structure
            health_data = data["data"]
            assert "service" in health_data
            assert health_data["service"] == "super-simple-kiosk"
            assert "version" in health_data
            assert "components" in health_data

    def test_config_endpoint(self) -> None:
        """Test the configuration endpoint."""
        app = create_app()

        with app.test_client() as client:
            response = client.get("/api/config")

            assert response.status_code == 200
            data = response.get_json()
            # Check standardized response format
            assert data["status"] == "success"
            assert "message" in data
            assert "data" in data
            # Check configuration data structure
            config_data = data["data"]
            assert "mqtt" in config_data
            assert "display" in config_data
            display_config = config_data["display"]
            assert "urls" in display_config
            assert "default_duration" in display_config

    def test_status_endpoint(self) -> None:
        """Test the status endpoint."""
        app = create_app()

        with app.test_client() as client:
            response = client.get("/api/status")

            # Status endpoint may return 503 if display manager is not available
            # This is expected behavior when services fail to initialize
            if response.status_code == 503:
                data = response.get_json()
                assert data["status"] == "error"
                assert "Display manager not available" in data["message"]
            else:
                assert response.status_code == 200
                data = response.get_json()
                assert data["status"] == "success"
                assert "message" in data
                assert "data" in data
                # Check status data structure
                status_data = data["data"]
                assert "is_running" in status_data
                assert "is_paused" in status_data
                assert "current_index" in status_data
