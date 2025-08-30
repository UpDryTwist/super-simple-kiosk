"""Unit tests for MQTT client service."""

from unittest.mock import Mock, patch

import paho.mqtt.client as mqtt
import pytest

from super_simple_kiosk.app.services.mqtt_client import MQTTClient


class TestMQTTClient:
    """Test MQTT client functionality."""

    @pytest.fixture
    def mock_config(self) -> dict:
        """Create a mock configuration for testing."""
        return {
            "mqtt": {
                "broker_host": "test-broker.com",
                "broker_port": 1883,
                "client_id": "test-client",
                "username": "test-user",
                "password": "test-password",
                "topic_prefix": "test-prefix",
            },
        }

    @pytest.fixture
    def mock_display_manager(self) -> Mock:
        """Create a mock display manager for testing."""
        return Mock()

    @pytest.fixture
    def mqtt_client(self, mock_config: dict, mock_display_manager: Mock) -> MQTTClient:
        """Create an MQTT client instance for testing."""
        with patch("super_simple_kiosk.app.services.mqtt_client.mqtt.Client"):
            return MQTTClient(mock_config, mock_display_manager)

    def test_init_with_config(self, mock_config: dict) -> None:
        """Test MQTT client initialization with configuration."""
        with patch(
            "super_simple_kiosk.app.services.mqtt_client.mqtt.Client",
        ) as _mock_mqtt:
            client = MQTTClient(mock_config)

            assert client.broker_host == "test-broker.com"
            assert client.broker_port == 1883
            assert client.client_id == "test-client"
            assert client.username == "test-user"
            assert client.password == "test-password"  # noqa: S105
            assert client.topic_prefix == "test-prefix"
            assert client.status_topic == "test-prefix/status"
            assert client.command_topic == "test-prefix/command"
            assert client.response_topic == "test-prefix/response"
            assert client.is_connected is False
            assert client.running is False

    def test_init_with_defaults(self) -> None:
        """Test MQTT client initialization with default values."""
        config = {"mqtt": {}}
        with patch(
            "super_simple_kiosk.app.services.mqtt_client.mqtt.Client",
        ) as _mock_mqtt:
            client = MQTTClient(config)

            assert client.broker_host == "localhost"
            assert client.broker_port == 1883
            assert client.client_id == "super-simple-kiosk"
            assert client.username is None
            assert client.password is None
            assert client.topic_prefix == "kiosk"

    def test_setup_client_success(self, mock_config: dict) -> None:
        """Test successful client setup."""
        with patch(
            "super_simple_kiosk.app.services.mqtt_client.mqtt.Client",
        ) as _mock_mqtt:
            mock_client_instance = Mock()
            _mock_mqtt.return_value = mock_client_instance

            client = MQTTClient(mock_config)

            # Verify client was created with correct parameters
            _mock_mqtt.assert_called_once_with(
                client_id="test-client",
                clean_session=True,
                protocol=mqtt.MQTTv311,
            )

            # Verify callbacks were set
            mock_client_instance.on_connect = client._on_connect
            mock_client_instance.on_disconnect = client._on_disconnect
            mock_client_instance.on_message = client._on_message
            mock_client_instance.on_publish = client._on_publish

            # Verify authentication was set
            mock_client_instance.username_pw_set.assert_called_once_with(
                "test-user",
                "test-password",
            )

            # Verify will message was set
            mock_client_instance.will_set.assert_called_once()

    def test_setup_client_without_auth(self) -> None:
        """Test client setup without authentication."""
        config = {"mqtt": {"broker_host": "localhost"}}
        with patch(
            "super_simple_kiosk.app.services.mqtt_client.mqtt.Client",
        ) as _mock_mqtt:
            mock_client_instance = Mock()
            _mock_mqtt.return_value = mock_client_instance

            _client = MQTTClient(config)

            # Verify authentication was not set
            mock_client_instance.username_pw_set.assert_not_called()

    def test_setup_client_exception(self, mock_config: dict) -> None:
        """Test client setup with exception."""
        with patch(
            "super_simple_kiosk.app.services.mqtt_client.mqtt.Client",
        ) as _mock_mqtt:
            _mock_mqtt.side_effect = Exception("Setup failed")

            # Should not raise exception
            client = MQTTClient(mock_config)
            assert client.client is None

    def test_connect_success(self, mqtt_client: MQTTClient) -> None:
        """Test successful connection to MQTT broker."""
        mqtt_client.client = Mock()

        result = mqtt_client.connect()

        assert result is True
        mqtt_client.client.connect.assert_called_once_with(
            "test-broker.com",
            1883,
            keepalive=60,
        )
        mqtt_client.client.loop_start.assert_called_once()

    def test_connect_no_client(self, mqtt_client: MQTTClient) -> None:
        """Test connection attempt when client is not initialized."""
        mqtt_client.client = None

        result = mqtt_client.connect()

        assert result is False

    def test_connect_exception(self, mqtt_client: MQTTClient) -> None:
        """Test connection with exception."""
        mqtt_client.client = Mock()
        mqtt_client.client.connect.side_effect = Exception("Connection failed")

        result = mqtt_client.connect()

        assert result is False

    def test_disconnect_success(self, mqtt_client: MQTTClient) -> None:
        """Test successful disconnection."""
        mqtt_client.client = Mock()

        mqtt_client.disconnect()

        mqtt_client.client.loop_stop.assert_called_once()
        mqtt_client.client.disconnect.assert_called_once()

    def test_disconnect_exception(self, mqtt_client: MQTTClient) -> None:
        """Test disconnection with exception."""
        mqtt_client.client = Mock()
        mqtt_client.client.disconnect.side_effect = Exception("Disconnect failed")

        # Should not raise exception
        mqtt_client.disconnect()

    def test_on_connect_success(self, mqtt_client: MQTTClient) -> None:
        """Test successful connection callback."""
        mock_client = Mock()
        mock_client.subscribe = Mock()

        mqtt_client._on_connect(mock_client, None, {}, 0)

        assert mqtt_client.is_connected is True
        mock_client.subscribe.assert_called_once_with("test-prefix/command", qos=1)

    def test_on_connect_failure(self, mqtt_client: MQTTClient) -> None:
        """Test failed connection callback."""
        mock_client = Mock()

        mqtt_client._on_connect(mock_client, None, {}, 1)

        assert mqtt_client.is_connected is False

    def test_on_disconnect_normal(self, mqtt_client: MQTTClient) -> None:
        """Test normal disconnection callback."""
        mqtt_client.is_connected = True

        mqtt_client._on_disconnect(Mock(), None, 0)

        assert mqtt_client.is_connected is False

    def test_on_disconnect_unexpected(self, mqtt_client: MQTTClient) -> None:
        """Test unexpected disconnection callback."""
        mqtt_client.is_connected = True

        mqtt_client._on_disconnect(Mock(), None, 1)

        assert mqtt_client.is_connected is False

    def test_on_message_command_topic(self, mqtt_client: MQTTClient) -> None:
        """Test message handling for command topic."""
        mock_msg = Mock()
        mock_msg.topic = "test-prefix/command"
        mock_msg.payload = b'{"command": "pause"}'

        with patch.object(mqtt_client, "_handle_command") as mock_handle:
            mqtt_client._on_message(Mock(), None, mock_msg)

            mock_handle.assert_called_once_with('{"command": "pause"}')

    def test_on_message_unknown_topic(self, mqtt_client: MQTTClient) -> None:
        """Test message handling for unknown topic."""
        mock_msg = Mock()
        mock_msg.topic = "unknown/topic"
        mock_msg.payload = b"test"

        with patch.object(mqtt_client, "_handle_command") as mock_handle:
            mqtt_client._on_message(Mock(), None, mock_msg)

            mock_handle.assert_not_called()

    def test_on_message_exception(self, mqtt_client: MQTTClient) -> None:
        """Test message handling with exception."""
        mock_msg = Mock()
        mock_msg.topic = "test-prefix/command"
        mock_msg.payload = b"invalid"

        # Should not raise exception
        mqtt_client._on_message(Mock(), None, mock_msg)

    def test_on_publish(self, mqtt_client: MQTTClient) -> None:
        """Test publish callback."""
        # Should not raise exception
        mqtt_client._on_publish(Mock(), None, 123)

    def test_handle_command_pause(
        self,
        mqtt_client: MQTTClient,
        mock_display_manager: Mock,
    ) -> None:
        """Test pause command handling."""
        mock_display_manager.pause_rotation.return_value = True

        with patch.object(mqtt_client, "_send_response") as mock_send:
            mqtt_client._handle_command('{"command": "pause"}')

            mock_display_manager.pause_rotation.assert_called_once()
            mock_send.assert_called_once_with("pause", "Rotation paused")

    def test_handle_command_resume(
        self,
        mqtt_client: MQTTClient,
        mock_display_manager: Mock,
    ) -> None:
        """Test resume command handling."""
        mock_display_manager.resume_rotation.return_value = True

        with patch.object(mqtt_client, "_send_response") as mock_send:
            mqtt_client._handle_command('{"command": "resume"}')

            mock_display_manager.resume_rotation.assert_called_once()
            mock_send.assert_called_once_with("resume", "Rotation resumed")

    def test_handle_command_next(
        self,
        mqtt_client: MQTTClient,
        mock_display_manager: Mock,
    ) -> None:
        """Test next command handling."""
        mock_display_manager.next_url.return_value = True

        with patch.object(mqtt_client, "_send_response") as mock_send:
            mqtt_client._handle_command('{"command": "next"}')

            mock_display_manager.next_url.assert_called_once()
            mock_send.assert_called_once_with("next", "Next URL loaded")

    def test_handle_command_jump_with_index(
        self,
        mqtt_client: MQTTClient,
        mock_display_manager: Mock,
    ) -> None:
        """Test jump command handling with index."""
        mock_display_manager.jump_to_url.return_value = True

        with patch.object(mqtt_client, "_send_response") as mock_send:
            mqtt_client._handle_command('{"command": "jump", "params": {"index": 2}}')

            mock_display_manager.jump_to_url.assert_called_once_with(2)
            mock_send.assert_called_once_with("jump", "Jumped to URL 2")

    def test_handle_command_jump_missing_index(self, mqtt_client: MQTTClient) -> None:
        """Test jump command handling without index."""
        with patch.object(mqtt_client, "_send_response") as mock_send:
            mqtt_client._handle_command('{"command": "jump"}')

            mock_send.assert_called_once_with("error", "Missing index parameter")

    def test_handle_command_status(
        self,
        mqtt_client: MQTTClient,
        mock_display_manager: Mock,
    ) -> None:
        """Test status command handling."""
        status_data = {"is_running": True, "current_index": 0}
        mock_display_manager.get_status.return_value = status_data

        with patch.object(mqtt_client, "_send_response") as mock_send:
            mqtt_client._handle_command('{"command": "status"}')

            mock_display_manager.get_status.assert_called_once()
            mock_send.assert_called_once_with("status", status_data)

    def test_handle_command_reload(
        self,
        mqtt_client: MQTTClient,
        mock_display_manager: Mock,
    ) -> None:
        """Test reload command handling."""
        mock_display_manager.reload_config.return_value = True

        with patch.object(mqtt_client, "_send_response") as mock_send:
            mqtt_client._handle_command('{"command": "reload"}')

            mock_display_manager.reload_config.assert_called_once()
            mock_send.assert_called_once_with("reload", "Configuration reloaded")

    def test_handle_command_add_url(
        self,
        mqtt_client: MQTTClient,
        mock_display_manager: Mock,
    ) -> None:
        """Test add_url command handling."""
        mock_display_manager.add_url.return_value = True

        with patch.object(mqtt_client, "_send_response") as mock_send:
            mqtt_client._handle_command(
                '{"command": "add_url", "url": "https://example.com", "duration": 30}',
            )

            mock_display_manager.add_url.assert_called_once_with(
                {"url": "https://example.com", "duration": 30},
                None,
            )
            mock_send.assert_called_once_with("add_url", "URL added successfully")

    def test_handle_command_add_url_missing_url(self, mqtt_client: MQTTClient) -> None:
        """Test add_url command handling without URL."""
        with patch.object(mqtt_client, "_send_response") as mock_send:
            mqtt_client._handle_command('{"command": "add_url"}')

            mock_send.assert_called_once_with("error", "Missing URL parameter")

    def test_handle_command_unknown(self, mqtt_client: MQTTClient) -> None:
        """Test unknown command handling."""
        with patch.object(mqtt_client, "_send_response") as mock_send:
            mqtt_client._handle_command('{"command": "unknown_command"}')

            mock_send.assert_called_once_with(
                "error",
                "Unknown command: unknown_command",
            )

    def test_handle_command_no_display_manager(self, mqtt_client: MQTTClient) -> None:
        """Test command handling without display manager."""
        mqtt_client.display_manager = None

        with patch.object(mqtt_client, "_send_response") as mock_send:
            mqtt_client._handle_command('{"command": "pause"}')

            mock_send.assert_called_once_with("error", "Display manager not available")

    def test_handle_command_invalid_json(self, mqtt_client: MQTTClient) -> None:
        """Test command handling with invalid JSON."""
        with patch.object(mqtt_client, "_send_response") as mock_send:
            mqtt_client._handle_command("invalid json")

            mock_send.assert_called_once_with("error", "Invalid JSON payload")

    def test_handle_command_exception(
        self,
        mqtt_client: MQTTClient,
        mock_display_manager: Mock,
    ) -> None:
        """Test command handling with exception."""
        mock_display_manager.pause_rotation.side_effect = Exception("Test error")

        with patch.object(mqtt_client, "_send_response") as mock_send:
            mqtt_client._handle_command('{"command": "pause"}')

            mock_send.assert_called_once_with(
                "error",
                "Internal error processing command",
            )

    def test_send_response_success(self, mqtt_client: MQTTClient) -> None:
        """Test successful response sending."""
        mqtt_client.client = Mock()
        mqtt_client.is_connected = True

        mqtt_client._send_response("test_command", "test_message")

        mqtt_client.client.publish.assert_called_once()
        call_args = mqtt_client.client.publish.call_args
        assert call_args[0][0] == "test-prefix/response"
        assert call_args[0][1] is not None  # JSON payload
        assert call_args[1]["qos"] == 1

    def test_send_response_not_connected(self, mqtt_client: MQTTClient) -> None:
        """Test response sending when not connected."""
        mqtt_client.client = Mock()
        mqtt_client.is_connected = False

        mqtt_client._send_response("test_command", "test_message")

        mqtt_client.client.publish.assert_not_called()

    def test_send_response_no_client(self, mqtt_client: MQTTClient) -> None:
        """Test response sending without client."""
        mqtt_client.client = None
        mqtt_client.is_connected = True

        mqtt_client._send_response("test_command", "test_message")

        # Should not raise exception

    def test_send_response_exception(self, mqtt_client: MQTTClient) -> None:
        """Test response sending with exception."""
        mqtt_client.client = Mock()
        mqtt_client.is_connected = True
        mqtt_client.client.publish.side_effect = Exception("Publish failed")

        # Should not raise exception
        mqtt_client._send_response("test_command", "test_message")

    def test_publish_status_success(
        self,
        mqtt_client: MQTTClient,
        mock_display_manager: Mock,
    ) -> None:
        """Test successful status publishing."""
        mqtt_client.client = Mock()
        mqtt_client.is_connected = True
        status_data = {"is_running": True}
        mock_display_manager.get_status.return_value = status_data

        mqtt_client.publish_status()

        mqtt_client.client.publish.assert_called_once()
        call_args = mqtt_client.client.publish.call_args
        assert call_args[0][0] == "test-prefix/status"
        assert call_args[0][1] is not None  # JSON payload
        assert call_args[1]["qos"] == 1
        assert call_args[1]["retain"] is True

    def test_publish_status_not_connected(self, mqtt_client: MQTTClient) -> None:
        """Test status publishing when not connected."""
        mqtt_client.client = Mock()
        mqtt_client.is_connected = False

        mqtt_client.publish_status()

        mqtt_client.client.publish.assert_not_called()

    def test_publish_status_no_display_manager(self, mqtt_client: MQTTClient) -> None:
        """Test status publishing without display manager."""
        mqtt_client.client = Mock()
        mqtt_client.is_connected = True
        mqtt_client.display_manager = None

        mqtt_client.publish_status()

        mqtt_client.client.publish.assert_called_once()

    def test_publish_status_exception(self, mqtt_client: MQTTClient) -> None:
        """Test status publishing with exception."""
        mqtt_client.client = Mock()
        mqtt_client.is_connected = True
        mqtt_client.client.publish.side_effect = Exception("Publish failed")

        # Should not raise exception
        mqtt_client.publish_status()

    def test_set_display_manager(
        self,
        mqtt_client: MQTTClient,
        mock_display_manager: Mock,
    ) -> None:
        """Test setting display manager."""
        new_manager = Mock()
        mqtt_client.set_display_manager(new_manager)

        assert mqtt_client.display_manager == new_manager

    def test_handle_command_public_method(self, mqtt_client: MQTTClient) -> None:
        """Test public handle_command method."""
        command_data = {"command": "pause"}

        with patch.object(mqtt_client, "_handle_command") as mock_handle:
            result = mqtt_client.handle_command(command_data)

            assert result is True
            mock_handle.assert_called_once()

    def test_handle_command_public_method_exception(
        self,
        mqtt_client: MQTTClient,
    ) -> None:
        """Test public handle_command method with exception."""
        command_data = {"command": "pause"}

        with patch.object(mqtt_client, "_handle_command") as mock_handle:
            mock_handle.side_effect = Exception("Test error")
            result = mqtt_client.handle_command(command_data)

            assert result is False

    def test_start_reconnect_loop(self, mqtt_client: MQTTClient) -> None:
        """Test starting reconnect loop."""
        with patch("threading.Thread") as mock_thread:
            mock_thread_instance = Mock()
            mock_thread.return_value = mock_thread_instance

            mqtt_client.start_reconnect_loop()

            assert mqtt_client.running is True
            mock_thread.assert_called_once()
            mock_thread_instance.start.assert_called_once()

    def test_start_reconnect_loop_already_running(
        self,
        mqtt_client: MQTTClient,
    ) -> None:
        """Test starting reconnect loop when already running."""
        mqtt_client.running = True
        mqtt_client.reconnect_thread = Mock()
        mqtt_client.reconnect_thread.is_alive.return_value = True

        with patch("threading.Thread") as mock_thread:
            mqtt_client.start_reconnect_loop()

            mock_thread.assert_not_called()

    def test_stop_reconnect_loop(self, mqtt_client: MQTTClient) -> None:
        """Test stopping reconnect loop."""
        mqtt_client.running = True
        mqtt_client.reconnect_thread = Mock()
        mqtt_client.reconnect_thread.is_alive.return_value = True

        mqtt_client.stop_reconnect_loop()

        assert mqtt_client.running is False
        mqtt_client.reconnect_thread.join.assert_called_once_with(timeout=5)

    def test_stop_reconnect_loop_no_thread(self, mqtt_client: MQTTClient) -> None:
        """Test stopping reconnect loop without thread."""
        mqtt_client.running = True
        mqtt_client.reconnect_thread = None

        # Should not raise exception
        mqtt_client.stop_reconnect_loop()

    def test_shutdown(self, mqtt_client: MQTTClient) -> None:
        """Test client shutdown."""
        with (
            patch.object(mqtt_client, "stop_reconnect_loop") as mock_stop,
            patch.object(mqtt_client, "disconnect") as mock_disconnect,
        ):
            mqtt_client.shutdown()

            mock_stop.assert_called_once()
            mock_disconnect.assert_called_once()

    def test_shutdown_exception(self, mqtt_client: MQTTClient) -> None:
        """Test client shutdown with exception."""
        with patch.object(mqtt_client, "stop_reconnect_loop") as mock_stop:
            mock_stop.side_effect = Exception("Shutdown failed")

            # Should not raise exception
            mqtt_client.shutdown()

    @patch("time.sleep")
    def test_reconnect_loop_attempts_reconnect(
        self,
        mock_sleep: Mock,
        mqtt_client: MQTTClient,
    ) -> None:
        """Test reconnect loop attempts reconnection when disconnected."""
        mqtt_client.running = True
        mqtt_client.is_connected = False
        mqtt_client.client = Mock()

        # Simulate one iteration of the loop
        def stop_after_one(*args: object) -> None:
            mqtt_client.running = False

        mock_sleep.side_effect = stop_after_one

        mqtt_client._reconnect_loop()

        mqtt_client.client.reconnect.assert_called_once()
        mock_sleep.assert_called()

    @patch("time.sleep")
    def test_reconnect_loop_when_connected(
        self,
        mock_sleep: Mock,
        mqtt_client: MQTTClient,
    ) -> None:
        """Test reconnect loop when already connected."""
        mqtt_client.running = True
        mqtt_client.is_connected = True

        # Simulate one iteration of the loop
        def stop_after_one(*args: object) -> None:
            mqtt_client.running = False

        mock_sleep.side_effect = stop_after_one

        mqtt_client._reconnect_loop()

        # Should not attempt reconnection
        mock_sleep.assert_called_with(10)

    @patch("time.sleep")
    def test_reconnect_loop_exception(
        self,
        mock_sleep: Mock,
        mqtt_client: MQTTClient,
    ) -> None:
        """Test reconnect loop with exception."""
        mqtt_client.running = True
        mqtt_client.is_connected = False
        mqtt_client.client = Mock()
        mqtt_client.client.reconnect.side_effect = Exception("Reconnect failed")

        # Simulate one iteration of the loop
        def stop_after_one(*args: object) -> None:
            mqtt_client.running = False

        mock_sleep.side_effect = stop_after_one

        mqtt_client._reconnect_loop()

        # Should handle exception gracefully
        mock_sleep.assert_called()
