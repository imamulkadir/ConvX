from __future__ import annotations

import asyncio
import hmac
import json
import logging
import time
from uuid import uuid4

from starlette.responses import JSONResponse

from app.core.config import Settings
from app.core.errors import Problem

logger = logging.getLogger("convx.requests")


class RequestSafety:
    def __init__(self, app, settings: Settings):
        self.app, self.settings = app, settings

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        started = time.monotonic()
        request_id, status, response_started = str(uuid4()), 500, False
        scope.setdefault("state", {})["request_id"] = request_id

        async def safe_send(message):
            nonlocal status, response_started
            if message["type"] == "http.response.start":
                response_started, status = True, message["status"]
                message["headers"] = list(message.get("headers", [])) + [
                    (b"x-request-id", request_id.encode()),
                    (b"cache-control", b"no-store"),
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"no-referrer"),
                ]
            await send(message)

        received = 0

        async def limited_receive():
            nonlocal received
            remaining = self.settings.upload_timeout_seconds - (time.monotonic() - started)
            if remaining <= 0:
                raise Problem(408, "UPLOAD_TIMEOUT", "Upload deadline exceeded")
            try:
                message = await asyncio.wait_for(receive(), remaining)
            except TimeoutError as exc:
                raise Problem(408, "UPLOAD_TIMEOUT", "Upload deadline exceeded") from exc
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.settings.max_request_bytes:
                    raise Problem(413, "REQUEST_TOO_LARGE", "Request exceeds the configured limit")
            return message

        try:
            headers = {k.lower(): v for k, v in scope["headers"]}
            if scope["path"].startswith("/api/v1/conversions"):
                if self.settings.auth_mode == "local":
                    if not scope.get("client") or scope["client"][0] not in ("127.0.0.1", "::1"):
                        raise Problem(401, "AUTH_REQUIRED", "Loopback access required")
                    owner = "local"
                else:
                    authorization = headers.get(b"authorization", b"").decode("latin-1")
                    token = authorization[7:] if authorization.startswith("Bearer ") else ""
                    owner = None
                    for identifier, secret in self.settings.api_tokens.items():
                        if hmac.compare_digest(token.encode(), secret.get_secret_value().encode()):
                            owner = identifier
                    if not owner:
                        raise Problem(401, "AUTH_REQUIRED", "Valid bearer token required")
                scope["state"]["owner"] = owner
            if b"content-length" in headers:
                try:
                    content_length = int(headers[b"content-length"])
                except ValueError as exc:
                    raise Problem(400, "INVALID_CONTENT_LENGTH", "Invalid request length") from exc
                if content_length < 0:
                    raise Problem(400, "INVALID_CONTENT_LENGTH", "Invalid request length")
                if content_length > self.settings.max_request_bytes:
                    raise Problem(413, "REQUEST_TOO_LARGE", "Request exceeds the configured limit")
            await self.app(scope, limited_receive, safe_send)
        except Problem as exc:
            if not response_started:
                await JSONResponse(
                    {"error": {"code": exc.code, "message": exc.message, "request_id": request_id}},
                    status_code=exc.status,
                )(scope, receive, safe_send)
        except Exception:
            # Raw exception strings can contain SQL parameters, tokens and document data.
            logger.error(
                json.dumps({"event": "request_failed", "request_id": request_id, "code": "INTERNAL_ERROR"})
            )
            if not response_started:
                await JSONResponse(
                    {
                        "error": {
                            "code": "INTERNAL_ERROR",
                            "message": "Request could not be completed",
                            "request_id": request_id,
                        }
                    },
                    status_code=500,
                )(scope, receive, safe_send)
        finally:
            logger.info(
                json.dumps(
                    {
                        "event": "request",
                        "request_id": request_id,
                        "status": status,
                        "duration_ms": round((time.monotonic() - started) * 1000),
                    }
                )
            )
