"""Response headers and the request body ceiling (AC-0001-42, -43).

Both are plain ASGI middleware rather than Starlette's `BaseHTTPMiddleware`,
so the body limit can refuse a request before any handler parses it.
"""

from __future__ import annotations

import json

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.correlation import current

MAX_BODY_BYTES = 64 * 1024

# The API serves JSON only: a policy that allows nothing costs nothing, and a
# response can never be rendered or framed as a page.
SECURITY_HEADERS = [
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'"),
]


class SecurityHeadersMiddleware:
    """Add the security headers to every HTTP response, errors included."""

    def __init__(self, app: ASGIApp) -> None:
        """Wrap the application."""
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Pass through, adding headers to the response start."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                names = {name.lower() for name, _ in message.get("headers", [])}
                extra = [(n, v) for n, v in SECURITY_HEADERS if n not in names]
                message["headers"] = [*message.get("headers", []), *extra]
            await send(message)

        await self.app(scope, receive, with_headers)


async def _refuse(send: Send) -> None:
    body = json.dumps(
        {
            "error": {
                "code": "PAYLOAD_TOO_LARGE",
                "message": "A requisição é grande demais.",
                "correlation_id": str(current()),
            }
        }
    ).encode()
    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


class BodyLimitMiddleware:
    """Refuse a request body over `MAX_BODY_BYTES` before it is parsed.

    A declared `Content-Length` is checked up front. A chunked body declares
    nothing, so it is read here, up to the ceiling, and replayed to the
    application: raising mid-read would not work, because FastAPI turns any
    error while reading a body into a 400.
    """

    def __init__(self, app: ASGIApp, max_bytes: int = MAX_BODY_BYTES) -> None:
        """Wrap the application."""
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Check the declared length, or read and count an undeclared one."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        declared = dict(scope.get("headers", [])).get(b"content-length")
        if declared is not None:
            if declared.isdigit() and int(declared) > self.max_bytes:
                await _refuse(send)
                return
            await self.app(scope, receive, send)
            return

        chunks: list[bytes] = []
        size = 0
        while True:
            message = await receive()
            if message["type"] != "http.request":
                break
            chunk = message.get("body", b"")
            size += len(chunk)
            if size > self.max_bytes:
                await _refuse(send)
                return
            chunks.append(chunk)
            if not message.get("more_body", False):
                break

        body = b"".join(chunks)
        replayed = False

        async def replay() -> Message:
            nonlocal replayed
            if replayed:
                return await receive()
            replayed = True
            return {"type": "http.request", "body": body, "more_body": False}

        await self.app(scope, replay, send)
