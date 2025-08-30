"""Integration tests for MQTT command handling."""

import sys
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


@pytest.mark.integration
@pytest.mark.mqtt
class TestMQTTCommands:
    """Test MQTT command handling integration."""

    def test_pause_command(
        self,
        display_manager: Mock,
        mock_mqtt_client: Mock,
        sample_mqtt_command: dict[str, Any],
    ) -> None:
        """Test pause command handling."""
        # Simulate pause command
        command = sample_mqtt_command.copy()
        command["command"] = "pause"

        # Handle command
        result = mock_mqtt_client.handle_command(command)

        # Verify pause was called
        mock_mqtt_client.display_manager.pause_rotation.assert_called_once()
        assert result is True

    def test_resume_command(
        self,
        display_manager: Mock,
        mock_mqtt_client: Mock,
        sample_mqtt_command: dict[str, Any],
    ) -> None:
        """Test resume command handling."""
        # Simulate resume command
        command = sample_mqtt_command.copy()
        command["command"] = "resume"

        # Handle command
        result = mock_mqtt_client.handle_command(command)

        # Verify resume was called
        mock_mqtt_client.display_manager.resume_rotation.assert_called_once()
        assert result is True

    def test_jump_command(
        self,
        display_manager: Mock,
        mock_mqtt_client: Mock,
        sample_mqtt_command: dict[str, Any],
    ) -> None:
        """Test jump command handling."""
        # Simulate jump command
        command = sample_mqtt_command.copy()
        command["command"] = "jump"
        command["index"] = 1

        # Handle command
        result = mock_mqtt_client.handle_command(command)

        # Verify jump was called with correct index
        mock_mqtt_client.display_manager.jump_to_url.assert_called_once_with(1)
        assert result is True

    def test_next_command(
        self,
        display_manager: Mock,
        mock_mqtt_client: Mock,
        sample_mqtt_command: dict[str, Any],
    ) -> None:
        """Test next command handling."""
        # Simulate next command
        command = sample_mqtt_command.copy()
        command["command"] = "next"

        # Handle command
        result = mock_mqtt_client.handle_command(command)

        # Verify next was called
        mock_mqtt_client.display_manager.next_url.assert_called_once()
        assert result is True

    def test_add_url_command(
        self,
        display_manager: Mock,
        mock_mqtt_client: Mock,
        sample_mqtt_command: dict[str, Any],
    ) -> None:
        """Test add_url command handling."""
        # Simulate add_url command
        command = sample_mqtt_command.copy()
        command["command"] = "add_url"
        command["url"] = "https://new-example.com"
        command["duration"] = 45

        # Handle command
        result = mock_mqtt_client.handle_command(command)

        # Verify add_url was called with correct parameters
        mock_mqtt_client.display_manager.add_url.assert_called_once_with(
            {"url": "https://new-example.com", "duration": 45},
            None,
        )
        assert result is True

    def test_invalid_command(
        self,
        mock_mqtt_client: Mock,
        sample_mqtt_command: dict[str, Any],
    ) -> None:
        """Test handling of invalid commands."""
        # Simulate invalid command
        command = sample_mqtt_command.copy()
        command["command"] = "invalid_command"

        # Handle command
        result = mock_mqtt_client.handle_command(command)

        # Verify command was rejected
        assert result is False

    def test_missing_command_field(
        self,
        mock_mqtt_client: Mock,
    ) -> None:
        """Test handling of commands missing the command field."""
        # Simulate command without command field
        command = {
            "timestamp": "2023-01-01T10:30:00Z",
            "device_id": "test_device",
        }

        # Handle command
        result = mock_mqtt_client.handle_command(command)

        # Verify command was rejected
        assert result is False

    def test_status_publishing(
        self,
        display_manager: Mock,
        mock_mqtt_client: Mock,
        sample_mqtt_status: dict[str, Any],
    ) -> None:
        """Test status publishing functionality."""
        # Publish status
        result = mock_mqtt_client.publish_status()

        # Verify status was published
        assert result is True
        mock_mqtt_client.client.publish.assert_called_once()

    def test_mqtt_connection_handling(
        self,
        mock_mqtt_client: Mock,
    ) -> None:
        """Test MQTT connection handling."""
        # Test connection
        result = mock_mqtt_client.connect()

        # Verify connection was attempted
        assert result is True
        mock_mqtt_client.client.connect.assert_called_once()
        mock_mqtt_client.client.loop_start.assert_called_once()

    def test_mqtt_subscription(
        self,
        mock_mqtt_client: Mock,
    ) -> None:
        """Test MQTT topic subscription."""
        # Subscribe to commands
        result = mock_mqtt_client.subscribe_to_commands()

        # Verify subscription was attempted
        assert result is True
        mock_mqtt_client.client.subscribe.assert_called()
