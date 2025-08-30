"""
Configuration management model for Super Simple Kiosk.

This module provides the configuration data model and management functionality
for handling YAML configuration loading, validation, and state persistence.
"""

from __future__ import annotations

import json
import os
import platform
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import jsonschema
import yaml
from jsonschema import ValidationError


@dataclass
class MQTTConfig:
    """MQTT client configuration settings."""

    broker: str = "localhost"
    port: int = 1883
    username: str | None = None
    password: str | None = None
    client_id: str = "web_rotator_001"
    topics: dict[str, str] = field(
        default_factory=lambda: {
            "commands": "displays/commands",
            "status": "displays/status",
            "config": "displays/config",
        },
    )


@dataclass
class DisplayConfig:
    """Display rotation configuration settings."""

    rotation_interval: int = 30  # seconds
    urls: list[str] = field(default_factory=list)
    fullscreen: bool = True
    auto_start: bool = True


@dataclass
class Config:
    """Main application configuration model."""

    mqtt: MQTTConfig = field(default_factory=MQTTConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)

    @classmethod
    def from_file(cls, file_path: str) -> Config:
        """
        Load configuration from YAML file.

        Args:
            file_path: Path to the YAML configuration file

        Returns:
            Config instance loaded from file

        Raises:
            FileNotFoundError: If configuration file doesn't exist
            yaml.YAMLError: If YAML file is malformed
        """
        try:
            with open(file_path, encoding="utf-8") as file:
                data = yaml.safe_load(file)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Configuration file not found: {file_path}",
            ) from None
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Invalid YAML in configuration file: {e}") from e
        else:
            return cls.from_dict(data or {})

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Config:
        """
        Create Config instance from dictionary.

        Args:
            data: Configuration data dictionary

        Returns:
            Config instance
        """
        mqtt_data = data.get("mqtt", {})
        display_data = data.get("display", {})

        mqtt_config = MQTTConfig(**mqtt_data)
        display_config = DisplayConfig(**display_data)

        return cls(mqtt=mqtt_config, display=display_config)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            Dictionary representation of configuration
        """
        return {
            "mqtt": {
                "broker": self.mqtt.broker,
                "port": self.mqtt.port,
                "username": self.mqtt.username,
                "password": self.mqtt.password,
                "client_id": self.mqtt.client_id,
                "topics": self.mqtt.topics,
            },
            "display": {
                "rotation_interval": self.display.rotation_interval,
                "urls": self.display.urls,
                "fullscreen": self.display.fullscreen,
                "auto_start": self.display.auto_start,
            },
        }

    def save_to_file(self, file_path: str) -> None:
        """
        Save configuration to YAML file.

        Args:
            file_path: Path to save the configuration file

        Raises:
            OSError: If file cannot be written
        """
        try:
            with open(file_path, "w", encoding="utf-8") as file:
                yaml.dump(self.to_dict(), file, default_flow_style=False)
        except OSError as e:
            raise OSError(f"Failed to save configuration file: {e}") from e


class ConfigManager:
    """Configuration and state management with JSON schema validation."""

    def __init__(self, config_file: str, state_file: str) -> None:
        """
        Initialize the configuration manager.

        Args:
            config_file: Path to the configuration file
            state_file: Path to the state file
        """
        self.config_file = config_file
        self.state_file = state_file
        self.config: dict[str, Any] | None = None
        self.state: dict[str, Any] | None = None

        # Ensure directories exist
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        os.makedirs(os.path.dirname(state_file), exist_ok=True)

    def _get_hostname(self) -> str:
        """
        Get the system hostname.

        Returns:
            System hostname
        """
        try:
            return platform.node()
        except (OSError, AttributeError):
            # Fallback to environment variable
            return os.environ.get("COMPUTERNAME", "unknown")

    def load_config(self) -> dict[str, Any]:
        """
        Load configuration from file.

        Returns:
            Configuration dictionary

        Raises:
            ValueError: If configuration is invalid
        """
        try:
            with open(self.config_file, encoding="utf-8") as file:
                content = file.read().strip()
                if not content:
                    # Empty file, treat as missing
                    raise FileNotFoundError("Configuration file is empty")
                config_data = yaml.safe_load(content) or {}
                self.config = config_data

            # Validate configuration
            if self.config is None:
                raise ValueError("Configuration is None")
            self._validate_config(self.config)
        except (yaml.YAMLError, ValidationError) as e:
            raise ValueError(f"Invalid configuration: {e!s}") from e
        except FileNotFoundError:
            # Create default config if file doesn't exist or is empty
            config_data = self._create_default_config()
            self.config = config_data
            self.save_config(self.config)
        else:
            if self.config is None:
                raise ValueError("Configuration is None")
            return self.config

        if self.config is None:
            raise ValueError("Configuration is None")
        return self.config

    def _create_default_config(self) -> dict[str, Any]:
        """
        Create default configuration.

        Returns:
            Default configuration dictionary
        """
        hostname = self._get_hostname()
        return {
            "mqtt": {
                "broker_host": "localhost",
                "broker_port": 1883,
                "client_id": f"kiosk-{hostname}",
                "username": None,
                "password": None,
                "topic_prefix": "kiosk",
            },
            "display": {
                "default_duration": 30,
                "urls": [
                    {
                        "url": "https://example.com",
                        "duration": 30,
                        "title": "Example Page",
                    },
                ],
            },
            "browser": {
                "headless": True,
                "window_size": "1920x1080",
                "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            },
            "logging": {
                "level": "INFO",
                "format": "json",
                "file": None,
            },
        }

    def _validate_config(self, config: dict[str, Any]) -> None:
        """
        Validate configuration against schema.

        Args:
            config: Configuration to validate

        Raises:
            ValidationError: If validation fails
        """
        schema = {
            "type": "object",
            "properties": {
                "mqtt": {
                    "type": "object",
                    "properties": {
                        "broker_host": {"type": "string"},
                        "broker_port": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 65535,
                        },
                        "client_id": {"type": "string"},
                        "username": {"type": ["string", "null"]},
                        "password": {"type": ["string", "null"]},
                        "topic_prefix": {"type": "string"},
                    },
                    "required": ["client_id"],
                },
                "display": {
                    "type": "object",
                    "properties": {
                        "default_duration": {"type": "integer", "minimum": 1},
                        "urls": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "url": {"type": "string", "format": "uri"},
                                    "duration": {"type": "integer", "minimum": 1},
                                    "title": {"type": "string"},
                                },
                                "required": ["url"],
                            },
                        },
                    },
                    "required": ["default_duration", "urls"],
                },
                "browser": {
                    "type": "object",
                    "properties": {
                        "headless": {"type": "boolean"},
                        "window_size": {"type": "string"},
                        "user_agent": {"type": "string"},
                    },
                },
                "logging": {
                    "type": "object",
                    "properties": {
                        "level": {
                            "type": "string",
                            "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        },
                        "format": {"type": "string", "enum": ["text", "json"]},
                        "file": {"type": ["string", "null"]},
                    },
                },
            },
            "required": ["mqtt", "display"],
        }

        jsonschema.validate(instance=config, schema=schema)

    def save_config(self, config: dict[str, Any]) -> bool:
        """
        Save configuration to file.

        Args:
            config: Configuration to save

        Returns:
            True if save successful, False otherwise
        """
        # Validate before saving
        self._validate_config(config)

        with open(self.config_file, "w", encoding="utf-8") as file:
            yaml.dump(config, file, default_flow_style=False, indent=2)

        self.config = config
        return True

    def validate_config(self, config: dict[str, Any]) -> bool:
        """
        Validate configuration without saving.

        Args:
            config: Configuration to validate

        Returns:
            True if valid, False otherwise
        """
        self._validate_config(config)
        return True

    def get_state(self) -> dict[str, Any]:
        """
        Load state from file.

        Returns:
            State dictionary
        """
        if self.state is None:
            try:
                with open(self.state_file, encoding="utf-8") as file:
                    state_data = json.load(file)
                    self.state = state_data
            except (FileNotFoundError, json.JSONDecodeError):
                # Return default state if file doesn't exist or is invalid
                state_data = {
                    "current_index": 0,
                    "is_paused": False,
                    "current_url": "",
                    "last_rotation": None,
                    "start_time": None,
                    "total_rotations": 0,
                    "error_count": 0,
                    "last_error": None,
                }
                self.state = state_data
        if self.state is None:
            raise ValueError("State is None")
        return self.state

    def update_state(self, state_update: dict[str, Any]) -> bool:
        """
        Update state and save to file.

        Args:
            state_update: State updates to apply

        Returns:
            True if update successful, False otherwise
        """
        try:
            # Get current state (loads if None)
            current_state = self.get_state()

            # Merge updates with current state
            current_state.update(state_update)
            self.state = current_state

            # Add timestamp
            self.state["last_updated"] = datetime.now(timezone.utc).isoformat()

            return self._save_state()
        except (OSError, TypeError):
            return False

    def _save_state(self) -> bool:
        """
        Save current state to file.

        Returns:
            True if save successful, False otherwise
        """
        try:
            with open(self.state_file, "w", encoding="utf-8") as file:
                json.dump(self.state, file, indent=2, ensure_ascii=False)
        except (OSError, TypeError):
            return False
        else:
            return True
