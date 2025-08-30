#!/usr/bin/env python3
"""Test runner script for super-simple-kiosk."""

import sys
from pathlib import Path

import pytest


def main() -> int:
    """Run tests with appropriate configuration."""
    # Add src to path for imports
    src_path = Path(__file__).parent / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    # Default arguments
    args = [
        "--verbose",
        "--tb=short",
        "--cov=super_simple_kiosk",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "--cov-fail-under=80",
    ]

    # Add command line arguments
    args.extend(sys.argv[1:])

    # Run pytest
    return pytest.main(args)


if __name__ == "__main__":
    sys.exit(main())
