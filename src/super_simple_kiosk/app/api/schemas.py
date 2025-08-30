"""API schemas and response utilities for Super Simple Kiosk."""

from __future__ import annotations

from typing import Any

# Type aliases for API responses
HealthResponse = dict[str, Any]
ConfigResponse = dict[str, Any]
StatusResponse = dict[str, Any]
URLResponse = dict[str, Any]
URLListResponse = dict[str, Any]


def create_error_response(message: str, status_code: int = 400) -> dict[str, Any]:
    """
    Create standardized error response.

    Args:
        message: Error message
        status_code: HTTP status code

    Returns:
        Error response dictionary
    """
    return {
        "status": "error",
        "message": message,
        "code": status_code,
    }


def create_success_response(
    data: dict[str, Any] | list[Any] | str,
    message: str = "Success",
) -> dict[str, Any]:
    """
    Create standardized success response.

    Args:
        data: Response data
        message: Success message

    Returns:
        Success response dictionary
    """
    return {
        "status": "success",
        "message": message,
        "data": data,
    }
