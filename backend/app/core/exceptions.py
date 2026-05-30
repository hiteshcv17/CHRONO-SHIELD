from enum import Enum
from fastapi import HTTPException, status
from typing import Any, Dict, Optional


class ErrorCode(str, Enum):
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"


class ChronoShieldError(Exception):
    """Base exception class for all ChronoShield operational errors."""
    pass


class AppHTTPException(HTTPException):
    """
    Subclass of FastAPI's HTTPException that carries a machine-readable ErrorCode
    and maps seamlessly to the ApiResponse error envelope.
    """
    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        headers: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(status_code=status_code, detail=message, headers=headers)
        self.error_code = error_code
        self.message = message
