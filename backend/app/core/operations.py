"""Streaming-safe redacted request telemetry and bounded request envelopes."""

import json
import logging
import re
import time
import uuid
from starlette.responses import JSONResponse

log = logging.getLogger("dsbca.operations")
log.setLevel(logging.INFO)
if not log.handlers:
    log.addHandler(logging.StreamHandler())


class OperationsMiddleware:
    def __init__(self, app, max_body_bytes=3500000):
        self.app, self.max_body_bytes = app, max_body_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        started = time.monotonic()
        headers = dict(scope.get("headers", []))
        supplied = headers.get(b"x-request-id", b"").decode("ascii", "ignore")
        request_id = (
            supplied
            if re.fullmatch(r"[A-Za-z0-9_-]{16,64}", supplied)
            else uuid.uuid4().hex
        )
        scope.setdefault("state", {})["request_id"] = request_id
        status, sent, consumed = 500, False, 0

        async def output(message):
            nonlocal status, sent
            if message["type"] == "http.response.start":
                status, sent = message["status"], True
                message.setdefault("headers", []).extend(
                    [
                        (b"x-request-id", request_id.encode()),
                        (b"cache-control", b"no-store"),
                        (b"x-content-type-options", b"nosniff"),
                        (b"x-frame-options", b"DENY"),
                        (b"referrer-policy", b"no-referrer"),
                    ]
                )
            await send(message)

        async def bounded_receive():
            nonlocal consumed
            message = await receive()
            consumed += len(message.get("body", b""))
            if consumed > self.max_body_bytes:
                raise BodyTooLarge()
            return message

        try:
            try:
                declared = int(headers.get(b"content-length", b"0"))
            except ValueError:
                declared = self.max_body_bytes + 1
            if declared > self.max_body_bytes:
                raise BodyTooLarge()
            await self.app(scope, bounded_receive, output)
        except BodyTooLarge:
            if not sent:
                await JSONResponse(
                    {"detail": "Request body exceeds the supported API limit"},
                    status_code=413,
                )(scope, receive, output)
        except Exception as exc:
            # Never log exception messages: SQL/provider errors may contain secrets.
            log.error(
                json.dumps(
                    {
                        "event": "api_failure",
                        "request_id": request_id,
                        "error_type": type(exc).__name__,
                    }
                )
            )
            if not sent:
                await JSONResponse(
                    {"detail": "Unexpected server error", "request_id": request_id},
                    status_code=500,
                )(scope, receive, output)
        finally:
            route = getattr(scope.get("route"), "path", "unmatched")
            log.info(
                json.dumps(
                    {
                        "event": "request",
                        "request_id": request_id,
                        "method": scope.get("method"),
                        "route": route,
                        "status": status,
                        "duration_ms": round((time.monotonic() - started) * 1000, 2),
                    }
                )
            )


class BodyTooLarge(Exception):
    pass
