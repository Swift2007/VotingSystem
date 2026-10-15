from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.config import settings

app = FastAPI(title=settings.app_title)
app.include_router(auth_router)


@app.get("/test")
async def test_route() -> dict[str, str]:
    return {"message": "FastAPI test route is working"}
