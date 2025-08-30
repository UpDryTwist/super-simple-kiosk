"""API routes for Super Simple Kiosk."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from flask import Blueprint, Response, current_app, jsonify, make_response, request
from werkzeug.exceptions import BadRequest

from super_simple_kiosk.app.api.schemas import (
    create_error_response,
    create_success_response,
)
from super_simple_kiosk.app.utils.validators import validate_url

if TYPE_CHECKING:
    from super_simple_kiosk.app.models.config import ConfigManager
    from super_simple_kiosk.app.services.browser_manager import BrowserManager
    from super_simple_kiosk.app.services.display_manager import DisplayManager
    from super_simple_kiosk.app.services.mqtt_client import MQTTClient

# Create blueprint for API routes
bp = Blueprint("api", __name__, url_prefix="/api")

# Get logger
logger = logging.getLogger(__name__)


def get_config_manager() -> ConfigManager | None:
    """
    Get the configuration manager instance from the Flask app context.

    Returns:
        Configuration manager instance or None if not available
    """
    return current_app.config.get("config_manager")


def get_display_manager() -> DisplayManager | None:
    """
    Get the display manager instance from the Flask app context.

    Returns:
        Display manager instance or None if not available
    """
    return current_app.config.get("display_manager")


def get_browser_manager() -> BrowserManager | None:
    """
    Get the browser manager instance from the Flask app context.

    Returns:
        Browser manager instance or None if not available
    """
    return current_app.config.get("browser_manager")


def get_mqtt_client() -> MQTTClient | None:
    """
    Get the MQTT client instance from the Flask app context.

    Returns:
        MQTT client instance or None if not available
    """
    return current_app.config.get("mqtt_client")


def validate_config_data(data: object) -> bool:
    """
    Validate configuration data structure.

    Args:
        data: Configuration data to validate

    Returns:
        True if data is valid, False otherwise
    """
    required_keys = ["mqtt", "display"]

    if not isinstance(data, dict):
        return False

    if not all(key in data for key in required_keys):
        return False

    # Validate MQTT configuration
    mqtt_config = data.get("mqtt", {})
    if not isinstance(mqtt_config, dict):
        return False

    # Validate display configuration
    display_config = data.get("display", {})
    if not isinstance(display_config, dict):
        return False

    # Validate URLs if present
    urls = display_config.get("urls", [])
    if not isinstance(urls, list):
        return False

    return all(isinstance(url, str) and validate_url(url) for url in urls)


def _handle_config_update_error(message: str, status_code: int) -> Response:
    """Handle configuration update errors."""
    return make_response(
        jsonify(create_error_response(message, status_code)),
        status_code,
    )


@bp.route("/health", methods=["GET"])
def health_check() -> Response:
    """
    Health check endpoint.

    Returns:
        Health status response with service information and component status
    """
    config_manager = get_config_manager()
    display_manager = get_display_manager()
    browser_manager = get_browser_manager()
    mqtt_client = get_mqtt_client()

    health_data = {
        "service": "super-simple-kiosk",
        "version": "0.0.1-dev0",
        "components": {
            "config_manager": config_manager is not None,
            "display_manager": display_manager is not None,
            "browser_manager": browser_manager is not None,
            "mqtt_client": mqtt_client is not None,
        },
    }

    # Add detailed status if display manager is available
    if display_manager:
        try:
            status = display_manager.get_status()
            health_data["display_status"] = status
        except Exception as e:
            logger.exception("Error getting display status")
            health_data["display_status"] = {"error": str(e)}

    # Add MQTT connection status if available
    if mqtt_client:
        health_data["mqtt_connected"] = mqtt_client.is_connected

    return jsonify(
        create_success_response(health_data, "Health check completed successfully"),
    )


@bp.route("/config", methods=["GET"])
def get_config() -> Response:
    """
    Get current configuration.

    Returns:
        Current configuration response
    """
    config_manager = get_config_manager()
    if not config_manager:
        return make_response(
            jsonify(create_error_response("Configuration manager not available", 500)),
            500,
        )

    try:
        config = config_manager.load_config()
        return jsonify(
            create_success_response(config, "Configuration retrieved successfully"),
        )
    except Exception as e:
        logger.exception("Error retrieving configuration")
        return make_response(
            jsonify(
                create_error_response(f"Failed to retrieve configuration: {e!s}", 500),
            ),
            500,
        )


@bp.route("/config", methods=["PUT"])
def update_config() -> Response:
    """
    Update configuration.

    Returns:
        Updated configuration response
    """
    config_manager = get_config_manager()
    display_manager = get_display_manager()
    result = None

    # Check for required managers
    if not config_manager:
        result = _handle_config_update_error("Configuration manager not available", 500)
    elif not request.is_json:
        result = _handle_config_update_error("Request must be JSON", 400)
    else:
        try:
            new_config = request.get_json()

            # Validate configuration data
            if not validate_config_data(new_config):
                result = _handle_config_update_error("Invalid configuration data", 400)
            else:
                # Save new configuration
                success = config_manager.save_config(new_config)
                if not success:
                    result = _handle_config_update_error(
                        "Failed to save configuration",
                        500,
                    )
                else:
                    # Reload display manager if available
                    if display_manager:
                        if display_manager.reload_config():
                            logger.info("Display manager configuration reloaded")
                        else:
                            logger.warning("Failed to reload display manager config")

                    result = jsonify(
                        create_success_response(
                            new_config,
                            "Configuration updated successfully",
                        ),
                    )
        except BadRequest:
            # Handle invalid JSON
            result = _handle_config_update_error("Invalid JSON format", 400)
        except Exception as e:
            logger.exception("Error updating configuration")
            result = _handle_config_update_error(
                f"Failed to update configuration: {e!s}",
                500,
            )

    return result


@bp.route("/config/reload", methods=["POST"])
def reload_config() -> Response:
    """
    Reload configuration from file.

    Returns:
        Reload status response
    """
    config_manager = get_config_manager()
    display_manager = get_display_manager()

    if not config_manager:
        return make_response(
            jsonify(create_error_response("Configuration manager not available", 500)),
            500,
        )

    try:
        # Reload configuration
        config = config_manager.load_config()

        # Reload display manager if available
        if display_manager:
            if display_manager.reload_config():
                logger.info("Display manager configuration reloaded")
            else:
                logger.warning("Failed to reload display manager config")

        return jsonify(
            create_success_response(config, "Configuration reloaded successfully"),
        )
    except Exception as e:
        logger.exception("Error reloading configuration")
        return make_response(
            jsonify(
                create_error_response(f"Failed to reload configuration: {e!s}", 500),
            ),
            500,
        )


@bp.route("/status", methods=["GET"])
def get_status() -> Response:
    """
    Get current display status.

    Returns:
        Current status response
    """
    display_manager = get_display_manager()

    if not display_manager:
        return make_response(
            jsonify(create_error_response("Display manager not available", 500)),
            500,
        )

    try:
        status = display_manager.get_status()
        return jsonify(create_success_response(status, "Status retrieved successfully"))
    except Exception as e:
        logger.exception("Error retrieving status")
        return make_response(
            jsonify(create_error_response(f"Failed to retrieve status: {e!s}", 500)),
            500,
        )


@bp.route("/control/pause", methods=["POST"])
def pause_rotation() -> Response:
    """
    Pause display rotation.

    Returns:
        Pause status response
    """
    display_manager = get_display_manager()

    if not display_manager:
        return make_response(
            jsonify(create_error_response("Display manager not available", 500)),
            500,
        )

    try:
        success = display_manager.pause_rotation()
        if success:
            return jsonify(create_success_response({}, "Display rotation paused"))
        return make_response(
            jsonify(create_error_response("Failed to pause rotation", 500)),
            500,
        )
    except Exception as e:
        logger.exception("Error pausing rotation")
        return make_response(
            jsonify(create_error_response(f"Failed to pause rotation: {e!s}", 500)),
            500,
        )


@bp.route("/control/resume", methods=["POST"])
def resume_rotation() -> Response:
    """
    Resume display rotation.

    Returns:
        Resume status response
    """
    display_manager = get_display_manager()

    if not display_manager:
        return make_response(
            jsonify(create_error_response("Display manager not available", 500)),
            500,
        )

    try:
        success = display_manager.resume_rotation()
        if success:
            return jsonify(create_success_response({}, "Display rotation resumed"))
        return make_response(
            jsonify(create_error_response("Failed to resume rotation", 500)),
            500,
        )
    except Exception as e:
        logger.exception("Error resuming rotation")
        return make_response(
            jsonify(create_error_response(f"Failed to resume rotation: {e!s}", 500)),
            500,
        )


@bp.route("/control/jump/<int:index>", methods=["POST"])
def jump_to_url(index: int) -> Response:
    """
    Jump to URL at specific index.

    Args:
        index: URL index to jump to

    Returns:
        Jump status response
    """
    display_manager = get_display_manager()

    if not display_manager:
        return make_response(
            jsonify(create_error_response("Display manager not available", 500)),
            500,
        )

    if index < 0:
        return make_response(
            jsonify(create_error_response("Index must be non-negative", 400)),
            400,
        )

    try:
        success = display_manager.jump_to_url(index)
        if success:
            return jsonify(
                create_success_response(
                    {"index": index},
                    f"Jumped to URL at index {index}",
                ),
            )
        return make_response(
            jsonify(
                create_error_response(f"Failed to jump to URL at index {index}", 400),
            ),
            400,
        )
    except Exception as e:
        logger.exception("Error jumping to URL at index %d", index)
        return make_response(
            jsonify(create_error_response(f"Failed to jump to URL: {e!s}", 500)),
            500,
        )


@bp.route("/control/next", methods=["POST"])
def next_url() -> Response:
    """
    Skip to next URL.

    Returns:
        Next URL status response
    """
    display_manager = get_display_manager()

    if not display_manager:
        return make_response(
            jsonify(create_error_response("Display manager not available", 500)),
            500,
        )

    try:
        success = display_manager.next_url()
        if success:
            return jsonify(create_success_response({}, "Skipped to next URL"))
        return make_response(
            jsonify(create_error_response("Failed to skip to next URL", 500)),
            500,
        )
    except Exception as e:
        logger.exception("Error skipping to next URL")
        return make_response(
            jsonify(create_error_response(f"Failed to skip to next URL: {e!s}", 500)),
            500,
        )


@bp.route("/urls", methods=["GET"])
def get_urls() -> Response:
    """
    Get list of all URLs.

    Returns:
        URL list response
    """
    config_manager = get_config_manager()

    if not config_manager:
        return make_response(
            jsonify(create_error_response("Configuration manager not available", 500)),
            500,
        )

    try:
        config = config_manager.load_config()
        urls = config.get("urls", [])
        return jsonify(
            create_success_response(
                {"urls": urls, "count": len(urls)},
                "URLs retrieved successfully",
            ),
        )
    except Exception as e:
        logger.exception("Error retrieving URLs")
        return make_response(
            jsonify(create_error_response(f"Failed to retrieve URLs: {e!s}", 500)),
            500,
        )


@bp.route("/urls", methods=["POST"])
def add_url() -> Response:  # noqa: PLR0911
    """
    Add new URL.

    Returns:
        Added URL response
    """
    display_manager = get_display_manager()

    if not display_manager:
        return make_response(
            jsonify(create_error_response("Display manager not available", 500)),
            500,
        )

    if not request.is_json:
        return make_response(
            jsonify(create_error_response("Request must be JSON", 400)),
            400,
        )

    try:
        data = request.get_json()
        url = data.get("url", "")
        duration = data.get("duration", None)

        # Validate URL
        if not url or not validate_url(url):
            return make_response(
                jsonify(create_error_response("Invalid URL format", 400)),
                400,
            )

        # Create URL configuration
        url_config = {"url": url}
        if duration is not None:
            if not isinstance(duration, int) or duration < 1:
                return make_response(
                    jsonify(
                        create_error_response(
                            "Duration must be a positive integer",
                            400,
                        ),
                    ),
                    400,
                )
            url_config["duration"] = duration

        # Get optional index parameter
        index = request.args.get("index", None)
        if index is not None:
            try:
                index = int(index)
                if index < 0:
                    return make_response(
                        jsonify(
                            create_error_response("Index must be non-negative", 400),
                        ),
                        400,
                    )
            except ValueError:
                return make_response(
                    jsonify(create_error_response("Index must be an integer", 400)),
                    400,
                )

        # Add URL
        success = display_manager.add_url(url_config, index)
        if not success:
            return make_response(
                jsonify(create_error_response("Failed to add URL", 500)),
                500,
            )

        # Get updated URL list to return the new index
        config_manager = get_config_manager()
        if config_manager:
            config = config_manager.load_config()
            urls = config.get("urls", [])
            new_index = len(urls) - 1 if index is None else index
            return make_response(
                jsonify(
                    create_success_response(
                        {"url": url, "index": new_index},
                        "URL added successfully",
                    ),
                ),
                201,
            )

        return make_response(
            jsonify(create_success_response({"url": url}, "URL added successfully")),
            201,
        )
    except BadRequest:
        # Handle invalid JSON
        return make_response(
            jsonify(create_error_response("Invalid JSON format", 400)),
            400,
        )
    except Exception as e:
        logger.exception("Error adding URL")
        return make_response(
            jsonify(create_error_response(f"Failed to add URL: {e!s}", 500)),
            500,
        )


@bp.route("/urls/<int:index>", methods=["PUT"])
def update_url(index: int) -> Response:  # noqa: PLR0911
    """
    Update URL at specific index.

    Args:
        index: URL index to update

    Returns:
        Updated URL response
    """
    config_manager = get_config_manager()
    display_manager = get_display_manager()

    if not config_manager:
        return make_response(
            jsonify(create_error_response("Configuration manager not available", 500)),
            500,
        )

    if not display_manager:
        return make_response(
            jsonify(create_error_response("Display manager not available", 500)),
            500,
        )

    if not request.is_json:
        return make_response(
            jsonify(create_error_response("Request must be JSON", 400)),
            400,
        )

    if index < 0:
        return make_response(
            jsonify(create_error_response("Index must be non-negative", 400)),
            400,
        )

    try:
        # Get current configuration
        config = config_manager.load_config()
        urls = config.get("urls", [])

        # Validate index
        if index >= len(urls):
            return make_response(
                jsonify(create_error_response(f"Invalid URL index: {index}", 404)),
                404,
            )

        # Get update data
        data = request.get_json()
        url = data.get("url", "")
        duration = data.get("duration", None)

        # Validate URL
        if not url or not validate_url(url):
            return make_response(
                jsonify(create_error_response("Invalid URL format", 400)),
                400,
            )

        # Update URL configuration
        url_config = {"url": url}
        if duration is not None:
            if not isinstance(duration, int) or duration < 1:
                return make_response(
                    jsonify(
                        create_error_response(
                            "Duration must be a positive integer",
                            400,
                        ),
                    ),
                    400,
                )
            url_config["duration"] = duration

        # Update URL in configuration
        urls[index] = url_config
        config["urls"] = urls

        # Save updated configuration
        success = config_manager.save_config(config)
        if not success:
            return make_response(
                jsonify(create_error_response("Failed to save configuration", 500)),
                500,
            )

        # Reload display manager
        if not display_manager.reload_config():
            logger.warning("Failed to reload display manager config")

        return jsonify(
            create_success_response(
                {"url": url, "index": index},
                f"URL at index {index} updated successfully",
            ),
        )
    except BadRequest:
        # Handle invalid JSON
        return make_response(
            jsonify(create_error_response("Invalid JSON format", 400)),
            400,
        )
    except Exception as e:
        logger.exception("Error updating URL at index %d", index)
        return make_response(
            jsonify(create_error_response(f"Failed to update URL: {e!s}", 500)),
            500,
        )


@bp.route("/urls/<int:index>", methods=["DELETE"])
def delete_url(index: int) -> Response:
    """
    Remove URL at specific index.

    Args:
        index: URL index to remove

    Returns:
        Delete status response
    """
    display_manager = get_display_manager()

    if not display_manager:
        return make_response(
            jsonify(create_error_response("Display manager not available", 500)),
            500,
        )

    if index < 0:
        return make_response(
            jsonify(create_error_response("Index must be non-negative", 400)),
            400,
        )

    try:
        success = display_manager.remove_url(index)
        if success:
            return jsonify(
                create_success_response(
                    {},
                    f"URL at index {index} removed successfully",
                ),
            )
        return make_response(
            jsonify(
                create_error_response(f"Failed to remove URL at index {index}", 404),
            ),
            404,
        )
    except Exception as e:
        logger.exception("Error removing URL at index %d", index)
        return make_response(
            jsonify(create_error_response(f"Failed to remove URL: {e!s}", 500)),
            500,
        )


@bp.route("/system/restart", methods=["POST"])
def restart_system() -> Response:
    """
    Restart display system.

    Returns:
        Restart status response
    """
    display_manager = get_display_manager()
    browser_manager = get_browser_manager()

    if not display_manager:
        return make_response(
            jsonify(create_error_response("Display manager not available", 500)),
            500,
        )

    try:
        # Shutdown current display manager
        display_manager.shutdown()

        # Shutdown and reinitialize browser if available
        if browser_manager:
            browser_manager.shutdown()
            if browser_manager.initialize():
                logger.info("Browser manager restarted")
            else:
                logger.warning("Failed to restart browser manager")

        # Restart display manager
        success = display_manager.start_rotation()
        if success:
            return jsonify(
                create_success_response({}, "Display system restarted successfully"),
            )
        return make_response(
            jsonify(create_error_response("Failed to restart display system", 500)),
            500,
        )
    except Exception as e:
        logger.exception("Error restarting system")
        return make_response(
            jsonify(create_error_response(f"Failed to restart system: {e!s}", 500)),
            500,
        )
