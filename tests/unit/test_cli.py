"""Unit tests for CLI module."""

from unittest.mock import Mock, patch

import pytest

from super_simple_kiosk.cli import get_parser, main


class TestCLI:
    """Test CLI functionality."""

    def test_get_parser(self) -> None:
        """Test that get_parser returns a properly configured ArgumentParser."""
        parser = get_parser()

        assert parser.prog == "super-simple-kiosk"
        assert (
            parser.description is None
        )  # No description set in current implementation

    def test_get_parser_returns_argument_parser(self) -> None:
        """Test that get_parser returns an ArgumentParser instance."""
        parser = get_parser()

        assert hasattr(parser, "parse_args")
        assert hasattr(parser, "add_argument")

    @patch("super_simple_kiosk.cli.app_main")
    def test_main_success(self, mock_app_main: Mock) -> None:
        """Test main function runs successfully."""
        mock_app_main.return_value = None

        result = main([])

        assert result == 0
        mock_app_main.assert_called_once()

    @patch("super_simple_kiosk.cli.app_main")
    def test_main_with_args(self, mock_app_main: Mock) -> None:
        """Test main function with command line arguments."""
        mock_app_main.return_value = None
        args = ["--help"]

        # Should raise SystemExit when --help is passed
        with pytest.raises(SystemExit) as exc_info:
            main(args)

        assert exc_info.value.code == 0

    @patch("super_simple_kiosk.cli.app_main")
    def test_main_with_none_args(self, mock_app_main: Mock) -> None:
        """Test main function with None args (default behavior)."""
        mock_app_main.return_value = None

        # When None is passed, it uses sys.argv which includes test arguments
        # This should raise SystemExit due to unrecognized arguments
        with pytest.raises(SystemExit) as exc_info:
            main(None)

        assert exc_info.value.code == 2

    @patch("super_simple_kiosk.cli.app_main")
    def test_main_parser_integration(self, mock_app_main: Mock) -> None:
        """Test that main function properly integrates with argument parser."""
        mock_app_main.return_value = None

        # Test with empty args (should not raise any exceptions)
        result = main([])

        assert result == 0
        mock_app_main.assert_called_once()

    @patch("super_simple_kiosk.cli.app_main")
    def test_main_exception_handling(self, mock_app_main: Mock) -> None:
        """Test main function handles exceptions gracefully."""
        mock_app_main.side_effect = Exception("Test exception")

        # Should raise the exception as per current implementation
        with pytest.raises(Exception, match="Test exception"):
            main([])
