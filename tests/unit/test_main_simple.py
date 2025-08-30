"""Simple unit tests for main module."""

import signal
from unittest.mock import Mock, patch

from super_simple_kiosk.app.main import signal_handler


class TestMainSimple:
    """Test main module functionality with simple tests."""

    def test_signal_handler(self) -> None:
        """Test signal handler function."""
        with patch("sys.exit") as mock_exit:
            signal_handler(signal.SIGINT, None)
            mock_exit.assert_called_once_with(0)

    def test_signal_handler_with_frame(self) -> None:
        """Test signal handler with frame parameter."""
        with patch("sys.exit") as mock_exit:
            mock_frame = Mock()
            signal_handler(signal.SIGTERM, mock_frame)
            mock_exit.assert_called_once_with(0)
