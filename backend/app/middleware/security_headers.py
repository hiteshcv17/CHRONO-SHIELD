from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    FastAPI HTTP middleware enforcing secure response headers for OWASP compliance:
    Clickjacking, XSS, MIME Sniffing, HSTS, and Referrer leakage prevention.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # 1. Prevent Clickjacking (X-Frame-Options)
        response.headers["X-Frame-Options"] = "SAMEORIGIN"

        # 2. Prevent MIME Sniffing (X-Content-Type-Options)
        response.headers["X-Content-Type-Options"] = "nosniff"

        # 3. Prevent XSS attacks in older browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # 4. Strict Transport Security (HSTS) - enforce HTTPS for 1 year
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

        # 5. Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # 6. Content Security Policy (CSP)
        # Allows self-domain resources, inline scripts/styles (required for React/Plotly dashboard),
        # image data URLs, and WebSockets (ws: / wss:) for live dashboard updates.
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "connect-src 'self' ws: wss: http://localhost:8000 http://127.0.0.1:8000 http://localhost:8001 http://127.0.0.1:8001; "
            "font-src 'self' data:;"
        )
        response.headers["Content-Security-Policy"] = csp

        return response
