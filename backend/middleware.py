"""Bound streamed request bodies and apply shared MongoDB abuse counters."""
import hashlib
import time
from datetime import datetime, timezone

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError, PyMongoError
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse
from .database import rate_limits_collection

MAX_REQUEST_BYTES = 24 * 1024 * 1024


def consume_limit(host: str, bucket: str, limit: int) -> bool:
    window = int(time.time()) // 60
    digest = hashlib.sha256(host.encode()).hexdigest()
    key = f"{bucket}:{digest}:{window}"
    query = {"_id": key}
    update = {"$inc": {"count": 1}, "$setOnInsert": {
        "expires_at": datetime.fromtimestamp((window + 2) * 60, timezone.utc)}}
    try:
        row = rate_limits_collection.find_one_and_update(query, update, upsert=True, return_document=ReturnDocument.AFTER)
    except DuplicateKeyError:
        row = rate_limits_collection.find_one_and_update(query, {"$inc": {"count": 1}}, return_document=ReturnDocument.AFTER)
    return bool(row and row["count"] <= limit)


class SecurityMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        path = scope["path"]

        async def secured_send(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend([(b"x-content-type-options", b"nosniff"),
                                (b"x-frame-options", b"DENY"),
                                (b"referrer-policy", b"same-origin")])
                if path.startswith(("/auth", "/cart", "/orders")):
                    headers.append((b"cache-control", b"no-store"))
                message["headers"] = headers
            await send(message)

        if scope["method"] in {"POST", "PUT", "PATCH", "DELETE"}:
            body = bytearray()
            while True:
                chunk = await receive()
                if chunk["type"] == "http.disconnect":
                    return
                body.extend(chunk.get("body", b""))
                if len(body) > MAX_REQUEST_BYTES:
                    return await JSONResponse({"detail": "Request exceeds 24 MiB"}, 413)(scope, receive, secured_send)
                if not chunk.get("more_body", False):
                    break
            consumed = False

            async def replay():
                nonlocal consumed
                if not consumed:
                    consumed = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await receive()

            host = (scope.get("client") or ("unknown",))[0]
            # Ignore caller-provided forwarding headers. Configure trusted proxies at the ASGI server.
            bucket, limit = ("chat", 20) if path == "/chat" else (("auth", 10) if path in {"/auth/login", "/auth/register", "/auth/google"} else ("writes", 120))
            try:
                allowed = await run_in_threadpool(consume_limit, host, bucket, limit)
            except PyMongoError:
                return await JSONResponse({"detail": "Service temporarily unavailable"}, 503)(scope, receive, secured_send)
            if not allowed:
                return await JSONResponse({"detail": "Too many requests; try again in one minute"}, 429, headers={"Retry-After": "60"})(scope, receive, secured_send)
            return await self.app(scope, replay, secured_send)
        return await self.app(scope, receive, secured_send)
