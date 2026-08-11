from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.limiter import limiter
from app.middlewares.logging_middleware import RequestLoggingMiddleware
from app.middlewares.audit_middleware import AuditLogMiddleware
from app.routers import auth, events, registrations, waitlist, users

app = FastAPI(title="Event Booking API")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


app.add_middleware(SlowAPIMiddleware)
app.add_middleware(AuditLogMiddleware)
app.add_middleware(RequestLoggingMiddleware)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(events.router)
app.include_router(registrations.router)
app.include_router(waitlist.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}