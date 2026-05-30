"""
app/core/base — Standardized API response primitives.

Provides platform-wide response envelopes, pagination wrappers, and
error models. Every public API endpoint should use these types.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


# ==============================================================================
# Error detail (embedded in ApiResponse on failure)
# ==============================================================================
class ErrorDetail(BaseModel):
    """Structured error payload embedded in failed ApiResponse envelopes."""

    code: str = Field(
        ..., description="Machine-readable error code (e.g. VALIDATION_ERROR)"
    )
    message: str = Field(..., description="Human-readable description of the error")
    trace_id: Optional[str] = Field(None, description="Distributed tracing identifier")
    field: Optional[str] = Field(
        None, description="Specific field that triggered the error (if applicable)"
    )


# ==============================================================================
# Generic response envelope
# ==============================================================================
class ApiResponse(BaseModel, Generic[T]):
    """
    Standardised API response envelope wrapping any data payload.

    Successful response:
        { "success": true, "data": {...}, "error": null, ... }

    Error response:
        { "success": false, "data": null, "error": {"code": ..., "message": ...}, ... }
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    success: bool = Field(
        ..., description="True if the request was processed successfully"
    )
    data: Optional[T] = Field(None, description="Response payload (null on error)")
    error: Optional[ErrorDetail] = Field(
        None, description="Error detail (null on success)"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC ISO-8601 response timestamp",
    )
    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique request trace identifier",
    )

    @classmethod
    def ok(cls, data: T) -> "ApiResponse[T]":
        """Create a successful response wrapping the given data."""
        return cls(success=True, data=data)

    @classmethod
    def fail(
        cls, code: str, message: str, trace_id: Optional[str] = None
    ) -> "ApiResponse[None]":
        """Create an error response with the given code and message."""
        return cls(
            success=False,
            error=ErrorDetail(code=code, message=message, trace_id=trace_id),
        )


# ==============================================================================
# Pagination wrapper
# ==============================================================================
class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated list response, compatible with any item type.

    Usage:
        return PaginatedResponse[AnomalyResponse](
            items=page_items,
            total=total_count,
            page=page,
            page_size=page_size,
        )
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    items: List[T] = Field(..., description="Items for the current page")
    total: int = Field(..., description="Total item count across all pages")
    page: int = Field(..., ge=1, description="Current page number (1-indexed)")
    page_size: int = Field(..., ge=1, description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")

    @classmethod
    def build(
        cls,
        items: List[T],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse[T]":
        """Construct a paginated response, computing total_pages automatically."""
        total_pages = max(1, (total + page_size - 1) // page_size)
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


# ==============================================================================
# Health check response
# ==============================================================================
class ServiceHealth(BaseModel):
    """Health status for a single backing service (DB, Redis, etc.)."""

    name: str
    status: str  # "healthy" | "degraded" | "unavailable"
    latency_ms: Optional[float] = None
    detail: Optional[str] = None


class PlatformHealthResponse(BaseModel):
    """
    Liveness / readiness probe response for the ChronoShield AI platform.
    Returned by GET /api/v1/platform/health.
    """

    status: str  # "healthy" | "degraded" | "unavailable"
    version: str
    uptime_seconds: Optional[float] = None
    services: List[ServiceHealth] = Field(default_factory=list)
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
