"""
Main application entry point for Super Simple Kiosk.

This module provides the main application entry point that initializes
and integrates all services, ensuring proper startup and shutdown sequences.
"""

from __future__ import annotations

import os
import signal
import sys
from typing import TYPE_CHECKING

from super_simple_kiosk.app import create_app
from super_simple_kiosk.app.models.config import ConfigManager
from super_simple_kiosk.app.services.browser_manager import BrowserManager
from super_simple_kiosk.app.services.display_manager import DisplayManager
from super_simple_kiosk.app.services.mqtt_client import MQTTClient
from super_simple_kiosk.app.utils.logging import setup_logging

if TYPE_CHECKING:
    from flask import Flask


def initialize_services(app: Flask) -> None:
    """
    Initialize all application services.

    Args:
        app: Flask application instance
    """
    with app.app_context():
        app.logger.info("Initializing application services")

        # Create config manager
        config_file = app.config.get("CONFIG_FILE", "config/urls.yaml")
        state_file = app.config.get("STATE_FILE", "data/state.json")
        config_manager = ConfigManager(config_file, state_file)
        app.config["config_manager"] = config_manager

        # Load configuration
        config = config_manager.load_config()
        app.logger.info(
            "Configuration loaded with %d URLs",
            len(config.get("urls", [])),
        )

        # Create browser manager
        browser_manager = BrowserManager(config_manager)
        app.config["browser_manager"] = browser_manager

        # Create MQTT client
        mqtt_client = MQTTClient(config)
        app.config["mqtt_client"] = mqtt_client

        # Create display manager
        display_manager = DisplayManager(
            config_manager=config_manager,
            mqtt_client=mqtt_client,
            browser_manager=browser_manager,
        )
        app.config["display_manager"] = display_manager

        # Set circular references
        mqtt_client.set_display_manager(display_manager)

        # Initialize browser
        app.logger.info("Initializing browser")
        try:
            browser_manager.initialize()
        except Exception:
            app.logger.exception("Failed to initialize browser")
            # Continue without browser - services will handle gracefully

        # Connect to MQTT broker
        app.logger.info("Connecting to MQTT broker")
        try:
            mqtt_client.connect()
        except Exception:
            app.logger.exception("Failed to connect to MQTT broker")
            # Continue without MQTT - services will handle gracefully

        # Start display rotation
        app.logger.info("Starting display rotation")
        try:
            display_manager.start_rotation()
        except Exception:
            app.logger.exception("Failed to start display rotation")
            # Continue without rotation - API endpoints will handle gracefully

        app.logger.info("Application services initialized successfully")


def shutdown_services(app: Flask) -> None:
    """
    Gracefully shutdown all services.

    Args:
        app: Flask application instance
    """
    with app.app_context():
        app.logger.info("Shutting down application services")

        # Get service references
        display_manager = app.config.get("display_manager")
        mqtt_client = app.config.get("mqtt_client")
        browser_manager = app.config.get("browser_manager")

        # Shutdown display manager
        if display_manager:
            try:
                display_manager.shutdown()
            except Exception:
                app.logger.exception("Error shutting down display manager")

        # Shutdown MQTT client
        if mqtt_client:
            try:
                mqtt_client.shutdown()
            except Exception:
                app.logger.exception("Error shutting down MQTT client")

        # Shutdown browser manager
        if browser_manager:
            try:
                browser_manager.shutdown()
            except Exception:
                app.logger.exception("Error shutting down browser manager")

        app.logger.info("Application services shutdown complete")


def signal_handler(_sig: int, _frame: object | None) -> None:
    """
    Handle termination signals.

    Args:
        sig: Signal number
        _frame: Current stack frame (unused)
    """
    # Note: We can't access the app here, so we'll rely on the Flask teardown
    sys.exit(0)


def main() -> None:
    """Run the main application entry point."""
    # Setup logging
    setup_logging(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        log_file=os.environ.get("LOG_FILE"),
    )

    # Create Flask application
    app = create_app()

    # Initialize services
    initialize_services(app)

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Register shutdown handler with Flask
    @app.teardown_appcontext
    def teardown_services(exception: BaseException | None = None) -> None:
        """Teardown services when Flask context ends."""
        if exception:
            app.logger.error("Application error: %s", exception)
        shutdown_services(app)

    # Get configuration from environment
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"

    # Start the application
    app.logger.info("Starting Flask application on %s:%d", host, port)
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
