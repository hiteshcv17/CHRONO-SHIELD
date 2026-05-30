import logging
from fastapi import Request, status, FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.exceptions import AppHTTPException, ErrorCode

logger = logging.getLogger("middleware.error_handler")


class GlobalErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    HTTP Middleware catching all unhandled exceptions occurring inside routes.
    Prevents leaking microservice server trace data to clients, returning unified JSON.
    """

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except AppHTTPException as exc:
            correlation_id = getattr(request.state, "correlation_id", "SYS")
            logger.warning(
                f"Application exception caught: {exc.error_code} - {exc.message}. "
                f"Path: {request.method} {request.url.path}",
                extra={"correlation_id": correlation_id},
            )
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "success": False,
                    "data": None,
                    "error": {
                        "code": (
                            exc.error_code.value
                            if hasattr(exc.error_code, "value")
                            else str(exc.error_code)
                        ),
                        "message": exc.message,
                        "trace_id": correlation_id,
                    },
                },
            )
        except Exception as exc:
            # Retrieve correlation ID if present on request scope
            correlation_id = getattr(request.state, "correlation_id", "SYS")

            # Log trace details with correlation metadata
            logger.error(
                f"Unhandled core exception caught processing request: {request.method} {request.url.path}. "
                f"Reason: {exc}",
                exc_info=True,
                extra={"correlation_id": correlation_id},
            )

            # Standardized operational error payload
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "success": False,
                    "data": None,
                    "error": {
                        "code": ErrorCode.INTERNAL_SERVER_ERROR.value,
                        "message": "An unexpected error occurred while processing your request.",
                        "trace_id": correlation_id,
                    },
                },
            )


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register FastAPI-level exception handlers so that exceptions raised within
    FastAPI dependency injection or validation flow are caught and formatted
    into the standardized ApiResponse error envelope before Starlette middleware.
    """

    @app.exception_handler(AppHTTPException)
    async def app_http_exception_handler(request: Request, exc: AppHTTPException):
        correlation_id = getattr(request.state, "correlation_id", "SYS")
        logger.warning(
            f"AppHTTPException handled: {exc.error_code} - {exc.message}. "
            f"Path: {request.method} {request.url.path}",
            extra={"correlation_id": correlation_id},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": (
                        exc.error_code.value
                        if hasattr(exc.error_code, "value")
                        else str(exc.error_code)
                    ),
                    "message": exc.message,
                    "trace_id": correlation_id,
                },
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        correlation_id = getattr(request.state, "correlation_id", "SYS")
        logger.warning(
            f"Validation error handled: {exc.errors()}. "
            f"Path: {request.method} {request.url.path}",
            extra={"correlation_id": correlation_id},
        )

        # Build readable validation error messages
        error_details = []
        for error in exc.errors():
            loc = " -> ".join(str(x) for x in error.get("loc", []))
            msg = error.get("msg", "Invalid value")
            error_details.append(f"{loc}: {msg}")

        combined_message = (
            "; ".join(error_details) if error_details else "Request validation failed"
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": ErrorCode.VALIDATION_ERROR.value,
                    "message": combined_message,
                    "trace_id": correlation_id,
                },
            },
        )
