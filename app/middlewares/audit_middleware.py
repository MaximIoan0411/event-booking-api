import uuid
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.database import AsyncSessionLocal
from app.models.audit_log import AuditLog
from app.security import decode_token

logger = logging.getLogger("app.audit")

AUDITED_METHODS = {"POST", "PATCH", "DELETE"}


class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        if request.method in AUDITED_METHODS and response.status_code < 400:
            user_id = self._extract_user_id(request)
            if user_id is not None:
                try:
                    await self._write_log(request, user_id, response.status_code)
                except Exception:
                    logger.exception("Nu s-a putut scrie audit log")

        return response

    def _extract_user_id(self, request: Request) -> uuid.UUID | None:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        token = auth_header.removeprefix("Bearer ")
        try:
            payload = decode_token(token)
            if payload.get("type") != "access":
                return None
            return uuid.UUID(payload["sub"])
        except Exception:
            return None

    async def _write_log(self, request: Request, user_id: uuid.UUID, status_code: int) -> None:
        path_parts = [p for p in request.url.path.split("/") if p]
        entity_type = path_parts[0] if path_parts else "unknown"

        entity_id = None
        for part in path_parts[1:]:
            try:
                entity_id = uuid.UUID(part)
                break
            except ValueError:
                continue
            
        async with AsyncSessionLocal() as session:
            session.add(AuditLog(
                user_id=user_id,
                action=f"{request.method} {request.url.path}",
                entity_type=entity_type,
                entity_id=entity_id,
                extra_data={"status_code": status_code},
            ))
            await session.commit()