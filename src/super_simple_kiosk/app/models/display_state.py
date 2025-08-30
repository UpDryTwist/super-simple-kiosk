"""
Display state management model for Super Simple Kiosk.

This module provides the display state data model and persistence functionality
for managing the current state of the web display rotator.
"""

from __future__ import annotations

import json
import socket
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from super_simple_kiosk.app.models.config import ConfigManager


@dataclass
class DisplayState:
    """Display state management model."""

    current_url_index: int = 0
    is_paused: bool = False
    is_running: bool = False
    last_rotation: datetime | None = None
    start_time: datetime | None = None
    total_rotations: int = 0
    error_count: int = 0
    last_error: str | None = None

    @classmethod
    def from_file(cls, file_path: str) -> DisplayState:
        """
        Load display state from JSON file.

        Args:
            file_path: Path to the JSON state file

        Returns:
            DisplayState instance loaded from file

        Raises:
            FileNotFoundError: If state file doesn't exist
            json.JSONDecodeError: If JSON file is malformed
        """
        try:
            with open(file_path, encoding="utf-8") as file:
                data = json.load(file)
        except FileNotFoundError:
            # Return default state if file doesn't exist
            return cls()
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Invalid JSON in state file: {e}",
                e.doc,
                e.pos,
            ) from e
        else:
            return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DisplayState:
        """
        Create DisplayState instance from dictionary.

        Args:
            data: State data dictionary

        Returns:
            DisplayState instance
        """
        # Parse datetime strings back to datetime objects
        last_rotation_str = data.get("last_rotation")
        start_time_str = data.get("start_time")

        last_rotation = None
        if last_rotation_str:
            with suppress(ValueError):
                last_rotation = datetime.fromisoformat(last_rotation_str)

        start_time = None
        if start_time_str:
            with suppress(ValueError):
                start_time = datetime.fromisoformat(start_time_str)

        return cls(
            current_url_index=data.get("current_url_index", 0),
            is_paused=data.get("is_paused", False),
            is_running=data.get("is_running", False),
            last_rotation=last_rotation,
            start_time=start_time,
            total_rotations=data.get("total_rotations", 0),
            error_count=data.get("error_count", 0),
            last_error=data.get("last_error"),
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert display state to dictionary.

        Returns:
            Display state as dictionary
        """
        return {
            "current_url_index": self.current_url_index,
            "is_paused": self.is_paused,
            "is_running": self.is_running,
            "last_rotation": self.last_rotation.isoformat()
            if self.last_rotation
            else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "total_rotations": self.total_rotations,
            "error_count": self.error_count,
            "last_error": self.last_error,
        }

    def save_to_file(self, file_path: str) -> None:
        """
        Save display state to JSON file.

        Args:
            file_path: Path to save the state file

        Raises:
            OSError: If file cannot be written
        """
        try:
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(self.to_dict(), file, indent=2, ensure_ascii=False)
        except OSError as e:
            raise OSError(f"Failed to save state file: {e}") from e

    def start(self) -> None:
        """Start the display rotation."""
        self.is_running = True
        self.is_paused = False
        self.start_time = datetime.now(timezone.utc)
        self.last_rotation = datetime.now(timezone.utc)

    def stop(self) -> None:
        """Stop the display rotation."""
        self.is_running = False
        self.is_paused = False

    def pause(self) -> None:
        """Pause the display rotation."""
        self.is_paused = True

    def resume(self) -> None:
        """Resume the display rotation."""
        self.is_paused = False
        self.last_rotation = datetime.now(timezone.utc)

    def next_url(self) -> None:
        """Move to the next URL in rotation."""
        self.current_url_index += 1
        self.last_rotation = datetime.now(timezone.utc)
        self.total_rotations += 1

    def jump_to_url(self, index: int) -> None:
        """
        Jump to a specific URL index.

        Args:
            index: URL index to jump to
        """
        self.current_url_index = index
        self.last_rotation = datetime.now(timezone.utc)

    def record_error(self, error_message: str) -> None:
        """
        Record an error occurrence.

        Args:
            error_message: Description of the error
        """
        self.error_count += 1
        self.last_error = error_message

    def clear_errors(self) -> None:
        """Clear error count and last error."""
        self.error_count = 0
        self.last_error = None

    def get_uptime(self) -> float:
        """
        Get the uptime in seconds.

        Returns:
            Uptime in seconds, or 0 if not started
        """
        if self.start_time:
            return (datetime.now(timezone.utc) - self.start_time).total_seconds()
        return 0.0

    def get_time_since_last_rotation(self) -> float:
        """
        Get time since last rotation in seconds.

        Returns:
            Time since last rotation in seconds, or 0 if no rotation
        """
        if self.last_rotation:
            return (datetime.now(timezone.utc) - self.last_rotation).total_seconds()
        return 0.0

    def reset(self) -> None:
        """Reset the display state to initial values."""
        self.current_url_index = 0
        self.is_paused = False
        self.is_running = False
        self.last_rotation = None
        self.start_time = None
        self.total_rotations = 0
        self.error_count = 0
        self.last_error = None


class ManagedDisplayState:
    """Model representing the current display state with ConfigManager integration."""

    def __init__(self, config_manager: ConfigManager) -> None:
        """
        Initialize the managed display state.

        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self._state = self.config_manager.get_state()

    @property
    def current_index(self) -> int:
        """Get current URL index."""
        return self._state.get("current_index", 0)

    @current_index.setter
    def current_index(self, value: int) -> None:
        """Set current URL index."""
        self._state["current_index"] = value
        self.config_manager.update_state({"current_index": value})

    @property
    def is_paused(self) -> bool:
        """Get pause status."""
        return self._state.get("is_paused", False)

    @is_paused.setter
    def is_paused(self, value: bool) -> None:
        """Set pause status."""
        self._state["is_paused"] = value
        self.config_manager.update_state({"is_paused": value})

    @property
    def total_rotations(self) -> int:
        """Get total rotation count."""
        return self._state.get("total_rotations", 0)

    @total_rotations.setter
    def total_rotations(self, value: int) -> None:
        """Set total rotation count."""
        self._state["total_rotations"] = value
        self.config_manager.update_state({"total_rotations": value})

    def increment_rotations(self) -> None:
        """Increment rotation count."""
        self.total_rotations += 1

    @property
    def error_count(self) -> int:
        """Get error count."""
        return self._state.get("error_count", 0)

    @error_count.setter
    def error_count(self, value: int) -> None:
        """Set error count."""
        self._state["error_count"] = value
        self.config_manager.update_state({"error_count": value})

    def increment_errors(self) -> None:
        """Increment error count."""
        self.error_count += 1

    @property
    def rotation_start_time(self) -> str:
        """Get rotation start time as ISO string."""
        start_time = self._state.get("start_time")
        if start_time:
            return start_time
        return datetime.now(timezone.utc).isoformat()

    @property
    def last_config_update(self) -> str:
        """Get last config update time as ISO string."""
        last_update = self._state.get("last_updated")
        if last_update:
            return last_update
        return datetime.now(timezone.utc).isoformat()

    @property
    def device_info(self) -> dict[str, Any]:
        """Get device information."""
        device_info = self._state.get("device_info", {})
        if not device_info:
            device_info = {
                "hostname": socket.gethostname(),
                "platform": "linux",
                "version": "1.0.0",
                "chromium_version": "",
            }
        return device_info

    def get_full_state(self) -> dict[str, Any]:
        """
        Get the complete state dictionary.

        Returns:
            Complete state dictionary
        """
        full_state = self._state.copy()
        full_state["device_info"] = self.device_info
        full_state["rotation_start_time"] = self.rotation_start_time
        return full_state

    def update_state(self, state_update: dict[str, Any]) -> None:
        """
        Update state with new values.

        Args:
            state_update: Dictionary of state updates
        """
        self._state.update(state_update)
        self.config_manager.update_state(state_update)

    def refresh(self) -> None:
        """Refresh state from configuration manager."""
        self._state = self.config_manager.get_state()
