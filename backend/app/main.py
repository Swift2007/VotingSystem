from fastapi import FastAPI

from app.config import settings

app = FastAPI(title=settings.app_title)


@app.get("/test")
async def test_route() -> dict[str, str]:
    return {"message": "FastAPI test route is working"}
