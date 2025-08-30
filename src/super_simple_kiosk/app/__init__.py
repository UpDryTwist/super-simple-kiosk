"""Flask application factory for Super Simple Kiosk."""

from __future__ import annotations

import logging
import os
from typing import Any

from flask import Flask

from super_simple_kiosk.app.api import routes
from super_simple_kiosk.app.models.config import ConfigManager
from super_simple_kiosk.app.services.browser_manager import BrowserManager
from super_simple_kiosk.app.services.display_manager import DisplayManager
from super_simple_kiosk.app.services.mqtt_client import MQTTClient
from super_simple_kiosk.app.utils.logging import setup_logging

# Global logger instance
logger = logging.getLogger(__name__)


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    """
    Create and configure the Flask application.

    Args:
        test_config: Optional test configuration

    Returns:
        Configured Flask application instance

    Raises:
        OSError: If required directories cannot be created
    """
    app = Flask(__name__, instance_relative_config=True)

    # Setup logging
    setup_logging(app=app)

    # Load default configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev"),
        CONFIG_FILE=os.environ.get("DISPLAY_CONFIG_FILE", "config/urls.yaml"),
        STATE_FILE=os.environ.get("DISPLAY_STATE_FILE", "data/state.json"),
        APPLICATION_ROOT="/",
    )

    # Override with test config if provided
    if test_config is not None:
        app.config.update(test_config)

    # Ensure instance folder exists
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        logger.exception("Failed to create instance directory")
        raise

    # Register blueprints
    app.register_blueprint(routes.bp)

    # Initialize managers
    try:
        # Initialize configuration manager
        config_manager = ConfigManager(
            config_file=app.config["CONFIG_FILE"],
            state_file=app.config["STATE_FILE"],
        )
        app.config["config_manager"] = config_manager

        # Load configuration (this will create default config if file doesn't exist)
        config_data = config_manager.load_config()

        # Initialize browser manager
        browser_manager = BrowserManager(config_manager)
        app.config["browser_manager"] = browser_manager

        # Initialize MQTT client
        mqtt_client = MQTTClient(config_data)
        app.config["mqtt_client"] = mqtt_client

        # Initialize display manager
        display_manager = DisplayManager(
            config_manager=config_manager,
            browser_manager=browser_manager,
            mqtt_client=mqtt_client,
        )
        app.config["display_manager"] = display_manager

        logger.info("All managers initialized successfully")

    except Exception:
        logger.exception("Failed to initialize managers")
        # Continue without managers for testing purposes

    return app
