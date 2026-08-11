from fastapi import FastAPI

from app.routers import auth, events, registrations, waitlist

app = FastAPI(title="Event Booking API")

app.include_router(auth.router)
app.include_router(events.router)
app.include_router(registrations.router)
app.include_router(waitlist.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}