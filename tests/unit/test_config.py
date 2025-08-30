"""
Test configuration management system.

This module tests the ConfigManager and ManagedDisplayState classes
for configuration loading, validation, and state persistence.
"""

import json
import os
import sys
import tempfile
from collections.abc import Generator
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
import yaml

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from super_simple_kiosk.app.models.config import ConfigManager  # noqa: E402
from super_simple_kiosk.app.models.display_state import (  # noqa: E402
    ManagedDisplayState,
)


@pytest.mark.unit
class TestConfigManager:
    """Test ConfigManager functionality."""

    @pytest.fixture
    def temp_files(self) -> Generator[tuple[str, str], None, None]:
        """Create temporary config and state files."""
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

        yield config_path, state_path

        # Cleanup
        for path in [config_path, state_path]:
            if os.path.exists(path):
                os.unlink(path)

    @pytest.fixture
    def valid_config(self) -> dict[str, Any]:
        """Return valid configuration data."""
        return {
            "mqtt": {
                "broker_host": "localhost",
                "broker_port": 1883,
                "username": None,
                "password": None,
                "client_id": "web_rotator_001",
                "topic_prefix": "kiosk",
            },
            "display": {
                "default_duration": 30,
                "urls": [
                    {"url": "https://example.com", "duration": 30, "title": "Example"},
                    {"url": "https://google.com", "duration": 60, "title": "Google"},
                ],
            },
        }

    def test_init(self, temp_files: tuple[str, str]) -> None:
        """Test ConfigManager initialization."""
        config_path, state_path = temp_files
        manager = ConfigManager(config_path, state_path)

        assert manager.config_file == config_path
        assert manager.state_file == state_path
        assert manager.config is None
        assert manager.state is None

    def test_load_config_valid(
        self,
        temp_files: tuple[str, str],
        valid_config: dict[str, Any],
    ) -> None:
        """Test loading valid configuration."""
        config_path, state_path = temp_files

        # Write valid config to file

        with open(config_path, "w") as f:
            yaml.dump(valid_config, f)

        manager = ConfigManager(config_path, state_path)
        loaded_config = manager.load_config()

        assert loaded_config == valid_config
        assert manager.config == valid_config

    def test_load_config_invalid_schema(self, temp_files: tuple[str, str]) -> None:
        """Test loading configuration with invalid schema."""
        config_path, state_path = temp_files

        # Write invalid config (missing required fields)
        invalid_config = {
            "urls": [],
            "mqtt": {
                "broker": "localhost",
                # Missing required fields
            },
        }

        with open(config_path, "w") as f:
            yaml.dump(invalid_config, f)

        manager = ConfigManager(config_path, state_path)

        with pytest.raises(ValueError, match="Invalid configuration"):
            manager.load_config()

    def test_load_config_file_not_found(self, temp_files: tuple[str, str]) -> None:
        """Test loading configuration when file doesn't exist."""
        config_path, state_path = temp_files

        # Remove the config file
        if os.path.exists(config_path):
            os.unlink(config_path)

        manager = ConfigManager(config_path, state_path)
        config = manager.load_config()

        # Should create default config
        assert "display" in config
        assert "default_duration" in config["display"]
        assert "urls" in config["display"]
        assert "mqtt" in config
        assert config["display"]["default_duration"] == 30
        assert len(config["display"]["urls"]) == 1
        assert config["display"]["urls"][0]["url"] == "https://example.com"

    def test_save_config(
        self,
        temp_files: tuple[str, str],
        valid_config: dict[str, Any],
    ) -> None:
        """Test saving configuration."""
        config_path, state_path = temp_files
        manager = ConfigManager(config_path, state_path)

        result = manager.save_config(valid_config)

        assert result is True
        assert manager.config == valid_config

        # Verify file was written
        assert os.path.exists(config_path)

        # Verify content

        with open(config_path) as f:
            saved_config = yaml.safe_load(f)

        assert saved_config == valid_config

    def test_save_config_invalid(self, temp_files: tuple[str, str]) -> None:
        """Test saving invalid configuration."""
        config_path, state_path = temp_files
        manager = ConfigManager(config_path, state_path)

        invalid_config = {
            "mqtt": {
                "broker_host": "localhost",
                # Missing required fields
            },
        }

        with pytest.raises(Exception, match=".*display.*required.*"):
            manager.save_config(invalid_config)

    def test_validate_config_valid(
        self,
        temp_files: tuple[str, str],
        valid_config: dict[str, Any],
    ) -> None:
        """Test validation of valid configuration."""
        config_path, state_path = temp_files
        manager = ConfigManager(config_path, state_path)

        result = manager.validate_config(valid_config)

        assert result is True

    def test_validate_config_invalid(self, temp_files: tuple[str, str]) -> None:
        """Test validation of invalid configuration."""
        config_path, state_path = temp_files
        manager = ConfigManager(config_path, state_path)

        invalid_config = {
            "display": {
                "default_duration": "not_an_integer",  # Should be integer
                "urls": [],
            },
            "mqtt": {
                "broker_host": "localhost",
                "broker_port": 1883,
                "client_id": "test",
            },
        }

        with pytest.raises(Exception, match=".*not_an_integer.*not of type.*integer.*"):
            manager.validate_config(invalid_config)

    def test_get_state_new(self, temp_files: tuple[str, str]) -> None:
        """Test getting state when no state file exists."""
        config_path, state_path = temp_files

        # Remove state file if it exists
        if os.path.exists(state_path):
            os.unlink(state_path)

        manager = ConfigManager(config_path, state_path)
        state = manager.get_state()

        assert "current_index" in state
        assert "is_paused" in state
        assert "total_rotations" in state
        assert "error_count" in state
        assert "current_url" in state
        assert state["current_index"] == 0
        assert state["is_paused"] is False

    def test_get_state_existing(self, temp_files: tuple[str, str]) -> None:
        """Test getting state from existing file."""
        config_path, state_path = temp_files

        # Create existing state file
        existing_state = {
            "current_index": 5,
            "is_paused": True,
            "total_rotations": 100,
            "error_count": 2,
            "device_info": {"hostname": "test-host"},
        }

        with open(state_path, "w") as f:
            json.dump(existing_state, f)

        manager = ConfigManager(config_path, state_path)
        state = manager.get_state()

        assert state["current_index"] == 5
        assert state["is_paused"] is True
        assert state["total_rotations"] == 100
        assert state["error_count"] == 2

    def test_update_state(self, temp_files: tuple[str, str]) -> None:
        """Test updating state."""
        config_path, state_path = temp_files
        manager = ConfigManager(config_path, state_path)

        # Get initial state
        initial_state = manager.get_state()

        # Update state
        update = {"current_index": 10, "is_paused": True, "total_rotations": 50}

        result = manager.update_state(update)

        assert result is True

        # Verify state was updated
        updated_state = manager.get_state()
        assert updated_state["current_index"] == 10
        assert updated_state["is_paused"] is True
        assert updated_state["total_rotations"] == 50

        # Verify other fields remain unchanged
        assert updated_state["error_count"] == initial_state["error_count"]
        assert "current_url" in updated_state


@pytest.mark.unit
class TestManagedDisplayState:
    """Test ManagedDisplayState functionality."""

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
    def display_state(self, config_manager: ConfigManager) -> ManagedDisplayState:
        """Create a ManagedDisplayState instance for testing."""
        return ManagedDisplayState(config_manager)

    def test_init(self, config_manager: ConfigManager) -> None:
        """Test ManagedDisplayState initialization."""
        state = ManagedDisplayState(config_manager)

        assert state.config_manager == config_manager
        assert state._state is not None

    def test_current_index_property(self, display_state: ManagedDisplayState) -> None:
        """Test current_index property."""
        # Test getter
        assert display_state.current_index == 0

        # Test setter
        display_state.current_index = 5
        assert display_state.current_index == 5

        # Verify it was saved to config manager
        state_data = display_state.config_manager.get_state()
        assert state_data["current_index"] == 5

    def test_is_paused_property(self, display_state: ManagedDisplayState) -> None:
        """Test is_paused property."""
        # Test getter
        assert display_state.is_paused is False

        # Test setter
        display_state.is_paused = True
        assert display_state.is_paused is True

        # Verify it was saved to config manager
        state_data = display_state.config_manager.get_state()
        assert state_data["is_paused"] is True

    def test_total_rotations_property(self, display_state: ManagedDisplayState) -> None:
        """Test total_rotations property."""
        # Test getter
        assert display_state.total_rotations == 0

        # Test setter
        display_state.total_rotations = 25
        assert display_state.total_rotations == 25

        # Verify it was saved to config manager
        state_data = display_state.config_manager.get_state()
        assert state_data["total_rotations"] == 25

    def test_increment_rotations(self, display_state: ManagedDisplayState) -> None:
        """Test increment_rotations method."""
        initial_rotations = display_state.total_rotations

        display_state.increment_rotations()

        assert display_state.total_rotations == initial_rotations + 1

        # Verify it was saved to config manager
        state_data = display_state.config_manager.get_state()
        assert state_data["total_rotations"] == initial_rotations + 1

    def test_error_count_property(self, display_state: ManagedDisplayState) -> None:
        """Test error_count property."""
        # Test getter
        assert display_state.error_count == 0

        # Test setter
        display_state.error_count = 3
        assert display_state.error_count == 3

        # Verify it was saved to config manager
        state_data = display_state.config_manager.get_state()
        assert state_data["error_count"] == 3

    def test_increment_errors(self, display_state: ManagedDisplayState) -> None:
        """Test increment_errors method."""
        initial_errors = display_state.error_count

        display_state.increment_errors()

        assert display_state.error_count == initial_errors + 1

        # Verify it was saved to config manager
        state_data = display_state.config_manager.get_state()
        assert state_data["error_count"] == initial_errors + 1

    def test_rotation_start_time_property(
        self,
        display_state: ManagedDisplayState,
    ) -> None:
        """Test rotation_start_time property."""
        start_time = display_state.rotation_start_time

        assert isinstance(start_time, str)
        assert start_time != ""

        # Should be ISO format datetime string
        try:
            datetime.fromisoformat(start_time)
        except ValueError:
            pytest.fail(
                "rotation_start_time should be valid ISO format datetime string",
            )

    def test_last_config_update_property(
        self,
        display_state: ManagedDisplayState,
    ) -> None:
        """Test last_config_update property."""
        last_update = display_state.last_config_update

        assert isinstance(last_update, str)
        assert last_update != ""

        # Should be ISO format datetime string
        try:
            datetime.fromisoformat(last_update)
        except ValueError:
            pytest.fail("last_config_update should be valid ISO format datetime string")

    def test_device_info_property(self, display_state: ManagedDisplayState) -> None:
        """Test device_info property."""
        device_info = display_state.device_info

        assert isinstance(device_info, dict)
        assert "hostname" in device_info
        assert "version" in device_info
        assert "chromium_version" in device_info
        assert device_info["version"] == "1.0.0"
        assert device_info["chromium_version"] == ""

    def test_get_full_state(self, display_state: ManagedDisplayState) -> None:
        """Test get_full_state method."""
        # Modify state through config manager
        display_state.config_manager.update_state(
            {"current_index": 15, "is_paused": True, "total_rotations": 100},
        )

        full_state = display_state.get_full_state()

        assert isinstance(full_state, dict)
        assert full_state["current_index"] == 15
        assert full_state["is_paused"] is True
        assert full_state["total_rotations"] == 100
        assert "device_info" in full_state
        assert "rotation_start_time" in full_state

    def test_update_state(self, display_state: ManagedDisplayState) -> None:
        """Test update_state method."""
        # Update multiple properties at once
        update = {
            "current_index": 20,
            "is_paused": False,
            "total_rotations": 75,
            "error_count": 5,
        }

        display_state.update_state(update)

        # Verify all properties were updated
        assert display_state.current_index == 20
        assert display_state.is_paused is False
        assert display_state.total_rotations == 75
        assert display_state.error_count == 5

        # Verify it was saved to config manager
        state_data = display_state.config_manager.get_state()
        assert state_data["current_index"] == 20
        assert state_data["is_paused"] is False
        assert state_data["total_rotations"] == 75
        assert state_data["error_count"] == 5
