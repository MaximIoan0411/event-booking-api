from fastapi import FastAPI

from app.routers import auth

app = FastAPI(title="Event Booking API")

app.include_router(auth.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}