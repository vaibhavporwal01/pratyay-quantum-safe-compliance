"""A basic CSRF guard for cookie sessions.

State-changing requests (POST, PUT, PATCH, DELETE) must send Content-Type: application/json.
A cross-site HTML form cannot send that type without a CORS preflight, which only
ALLOWED_ORIGIN passes. The one multipart endpoint, the PDF upload, instead must carry an Origin
header equal to ALLOWED_ORIGIN.
"""

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.config import settings

UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}
MULTIPART_PATHS = {"/api/v1/rules/sources"}


def _media_type(request: Request) -> str:
    return request.headers.get("content-type", "").split(";")[0].strip().lower()


def refusal(request: Request) -> str | None:
    """Why the request is refused, or None to let it through."""
    if request.method not in UNSAFE:
        return None
    media = _media_type(request)
    if request.url.path in MULTIPART_PATHS and media == "multipart/form-data":
        origin = request.headers.get("origin")
        if origin != settings.allowed_origin.rstrip("/"):
            return "This upload must come from the Pratyay site."
        return None
    if media != "application/json":
        return "Send the request as application/json."
    return None


async def csrf_middleware(request: Request, call_next):
    reason = refusal(request)
    if reason is not None:
        status = 403 if request.url.path in MULTIPART_PATHS else 415
        return JSONResponse({"detail": reason}, status_code=status)
    return await call_next(request)
