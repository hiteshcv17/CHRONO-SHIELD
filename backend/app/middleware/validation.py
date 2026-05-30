from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.base import ApiResponse


class PayloadValidationMiddleware(BaseHTTPMiddleware):
    """
    HTTP middleware inspecting request sizes and content types.
    Mitigates DoS via memory exhaustion by rejecting payloads > 5MB.
    """

    async def dispatch(self, request: Request, call_next):
        # Only inspect mutative HTTP verbs
        if request.method in ("POST", "PUT", "PATCH"):
            # Check content-length header
            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    size = int(content_length)
                    # Limit to 5MB (5 * 1024 * 1024)
                    if size > 5 * 1024 * 1024:
                        err_envelope = ApiResponse.fail(
                            code="PAYLOAD_TOO_LARGE",
                            message="Request payload exceeds strict limit of 5MB.",
                        )
                        return JSONResponse(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            content=err_envelope.model_dump(),
                        )
                except ValueError:
                    pass

        return await call_next(request)
