"""
MQTT client service for Super Simple Kiosk.

This module provides the MQTT client service that handles connection to the MQTT broker,
subscribes to command topics, and publishes status updates.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import paho.mqtt.client as mqtt

if TYPE_CHECKING:
    from super_simple_kiosk.app.services.display_manager import DisplayManager

logger = logging.getLogger(__name__)


class MQTTClient:
    """MQTT client service for remote control and status reporting."""

    def __init__(
        self,
        config: dict[str, Any],
        display_manager: DisplayManager | None = None,
    ) -> None:
        """
        Initialize the MQTT client.

        Args:
            config: Configuration object containing MQTT settings
            display_manager: Display manager for command handling
        """
        self.config = config
        self.display_manager = display_manager

        # MQTT settings
        self.broker_host = config.get("mqtt", {}).get("broker_host", "localhost")
        self.broker_port = config.get("mqtt", {}).get("broker_port", 1883)
        self.client_id = config.get("mqtt", {}).get("client_id", "super-simple-kiosk")
        self.username = config.get("mqtt", {}).get("username")
        self.password = config.get("mqtt", {}).get("password")
        self.topic_prefix = config.get("mqtt", {}).get("topic_prefix", "kiosk")

        # Client state
        self.client: mqtt.Client | None = None
        self.is_connected = False
        self.reconnect_thread: threading.Thread | None = None
        self.running = False

        # Topic definitions
        self.status_topic = f"{self.topic_prefix}/status"
        self.command_topic = f"{self.topic_prefix}/command"
        self.response_topic = f"{self.topic_prefix}/response"

        # Initialize client
        self._setup_client()

    def _setup_client(self) -> None:
        """Set up the MQTT client with callbacks and configuration."""
        try:
            # Create client
            self.client = mqtt.Client(
                client_id=self.client_id,
                clean_session=True,
                protocol=mqtt.MQTTv311,
            )

            # Set callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            self.client.on_publish = self._on_publish

            # Set authentication if provided
            if self.username and self.password:
                self.client.username_pw_set(self.username, self.password)

            # Set last will and testament
            will_message = json.dumps(
                {
                    "status": "offline",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "client_id": self.client_id,
                },
            )
            self.client.will_set(self.status_topic, will_message, qos=1, retain=True)

            logger.info("MQTT client setup complete")
        except Exception:
            logger.exception("Failed to setup MQTT client")

    def connect(self) -> bool:
        """
        Connect to the MQTT broker.

        Returns:
            True if connection successful, False otherwise
        """
        if not self.client:
            logger.error("MQTT client not initialized")
            return False

        try:
            logger.info(
                "Connecting to MQTT broker: %s:%d",
                self.broker_host,
                self.broker_port,
            )
            self.client.connect(self.broker_host, self.broker_port, keepalive=60)
            self.client.loop_start()
        except Exception:
            logger.exception("Failed to connect to MQTT broker")
            return False
        else:
            return True

    def disconnect(self) -> None:
        """Disconnect from the MQTT broker."""
        if self.client:
            try:
                self.client.loop_stop()
                self.client.disconnect()
                logger.info("Disconnected from MQTT broker")
            except Exception:
                logger.exception("Error during MQTT disconnect")

    def _on_connect(
        self,
        client: mqtt.Client,
        _userdata: object,
        _flags: dict[str, Any],
        rc: int,
    ) -> None:
        """
        Handle MQTT connection events.

        Args:
            client: MQTT client instance
            _userdata: User data passed to client (unused)
            _flags: Connection flags (unused)
            rc: Return code (0 = success)
        """
        if rc == 0:
            self.is_connected = True
            logger.info("Connected to MQTT broker")

            # Subscribe to command topic
            client.subscribe(self.command_topic, qos=1)
            logger.info("Subscribed to command topic: %s", self.command_topic)

            # Publish online status
            self.publish_status()
        else:
            self.is_connected = False
            logger.error("Failed to connect to MQTT broker, return code: %d", rc)

    def _on_disconnect(self, _client: mqtt.Client, _userdata: object, rc: int) -> None:
        """
        Handle MQTT disconnection events.

        Args:
            _client: MQTT client instance (unused)
            _userdata: User data passed to client (unused)
            rc: Return code
        """
        self.is_connected = False
        if rc != 0:
            logger.warning("Unexpected MQTT disconnection, return code: %d", rc)
        else:
            logger.info("Disconnected from MQTT broker")

    def _on_message(
        self,
        _client: mqtt.Client,
        _userdata: object,
        msg: mqtt.MQTTMessage,
    ) -> None:
        """
        Handle incoming MQTT messages.

        Args:
            _client: MQTT client instance (unused)
            _userdata: User data passed to client (unused)
            msg: Received message
        """
        try:
            topic = msg.topic
            payload = msg.payload.decode("utf-8")
            logger.debug("Received message on topic %s: %s", topic, payload)

            if topic == self.command_topic:
                self._handle_command(payload)
            else:
                logger.warning("Unknown topic: %s", topic)

        except Exception:
            logger.exception("Error handling MQTT message")

    def _on_publish(self, _client: mqtt.Client, _userdata: object, mid: int) -> None:
        """
        Handle MQTT publish events.

        Args:
            _client: MQTT client instance (unused)
            _userdata: User data passed to client (unused)
            mid: Message ID
        """
        logger.debug("Message published with ID: %d", mid)

    def _handle_command(self, payload: str) -> None:
        """
        Handle incoming command messages.

        Args:
            payload: Command payload as JSON string
        """
        try:
            command_data = json.loads(payload)
            command = command_data.get("command")
            params = command_data.get("params", {})

            logger.info("Processing command: %s", command)

            if not self.display_manager:
                self._send_response("error", "Display manager not available")
                return

            # Handle different commands
            if command == "pause":
                success = self.display_manager.pause_rotation()
                self._send_response(
                    "pause",
                    "Rotation paused" if success else "Failed to pause",
                )
            elif command == "resume":
                success = self.display_manager.resume_rotation()
                self._send_response(
                    "resume",
                    "Rotation resumed" if success else "Failed to resume",
                )
            elif command == "next":
                success = self.display_manager.next_url()
                self._send_response(
                    "next",
                    "Next URL loaded" if success else "Failed to load next URL",
                )
            elif command == "jump":
                index = params.get("index")
                if index is not None:
                    success = self.display_manager.jump_to_url(index)
                    self._send_response(
                        "jump",
                        f"Jumped to URL {index}"
                        if success
                        else f"Failed to jump to URL {index}",
                    )
                else:
                    self._send_response("error", "Missing index parameter")
            elif command == "status":
                status = self.display_manager.get_status()
                self._send_response("status", status)
            elif command == "reload":
                success = self.display_manager.reload_config()
                self._send_response(
                    "reload",
                    "Configuration reloaded"
                    if success
                    else "Failed to reload configuration",
                )
            elif command == "add_url":
                url = command_data.get("url")
                duration = command_data.get("duration", 30)
                index = command_data.get("index")

                if url:
                    url_config = {"url": url, "duration": duration}
                    success = self.display_manager.add_url(url_config, index)
                    self._send_response(
                        "add_url",
                        "URL added successfully" if success else "Failed to add URL",
                    )
                else:
                    self._send_response("error", "Missing URL parameter")
            else:
                self._send_response("error", f"Unknown command: {command}")

        except json.JSONDecodeError:
            logger.exception("Invalid JSON in command payload: %s", payload)
            self._send_response("error", "Invalid JSON payload")
        except Exception:
            logger.exception("Error processing command")
            self._send_response("error", "Internal error processing command")

    def _send_response(self, command: str, message: str | dict[str, Any]) -> None:
        """
        Send a response message.

        Args:
            command: Command that was processed
            message: Response message or data
        """
        if not self.client or not self.is_connected:
            return

        try:
            response = {
                "command": command,
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "client_id": self.client_id,
            }

            payload = json.dumps(response)
            self.client.publish(self.response_topic, payload, qos=1)
            logger.debug("Sent response: %s", payload)

        except Exception:
            logger.exception("Failed to send response")

    def publish_status(self) -> None:
        """Publish current status to the status topic."""
        if not self.client or not self.is_connected:
            return

        try:
            # Get display status if available
            display_status = {}
            if self.display_manager:
                display_status = self.display_manager.get_status()

            status = {
                "status": "online",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "client_id": self.client_id,
                "display": display_status,
            }

            payload = json.dumps(status)
            self.client.publish(self.status_topic, payload, qos=1, retain=True)
            logger.debug("Published status: %s", payload)

        except Exception:
            logger.exception("Failed to publish status")

    def set_display_manager(self, display_manager: DisplayManager) -> None:
        """
        Set the display manager reference.

        Args:
            display_manager: Display manager instance
        """
        self.display_manager = display_manager

    def handle_command(self, command_data: dict[str, Any]) -> bool:
        """
        Handle a command (public method for testing).

        Args:
            command_data: Command data dictionary

        Returns:
            True if command was processed successfully, False otherwise
        """
        try:
            # Convert command data to JSON string for internal processing
            payload = json.dumps(command_data)
            self._handle_command(payload)
        except Exception:
            logger.exception("Error handling command")
            return False
        else:
            return True

    def start_reconnect_loop(self) -> None:
        """Start the automatic reconnection loop in a background thread."""
        if self.reconnect_thread and self.reconnect_thread.is_alive():
            logger.warning("Reconnect loop already running")
            return

        self.running = True
        self.reconnect_thread = threading.Thread(
            target=self._reconnect_loop,
            daemon=True,
        )
        self.reconnect_thread.start()
        logger.info("MQTT reconnect loop started")

    def _reconnect_loop(self) -> None:
        """Run the reconnection loop that attempts to reconnect when disconnected."""
        while self.running:
            if not self.is_connected and self.client:
                logger.info("Attempting to reconnect to MQTT broker...")
                try:
                    self.client.reconnect()
                    time.sleep(5)  # Wait before checking connection
                except Exception:
                    logger.exception("Reconnection attempt failed")
                    time.sleep(30)  # Wait longer before next attempt
            else:
                time.sleep(10)  # Check connection status every 10 seconds

    def stop_reconnect_loop(self) -> None:
        """Stop the automatic reconnection loop."""
        self.running = False
        if self.reconnect_thread and self.reconnect_thread.is_alive():
            self.reconnect_thread.join(timeout=5)
        logger.info("MQTT reconnect loop stopped")

    def shutdown(self) -> None:
        """Shutdown the MQTT client."""
        try:
            self.stop_reconnect_loop()
            self.disconnect()
            logger.info("MQTT client shutdown complete")
        except Exception:
            logger.exception("Error during MQTT client shutdown")
