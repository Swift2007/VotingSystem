from fastapi import FastAPI

app = FastAPI(title="Voting System API")


@app.get("/test")
async def test_route() -> dict[str, str]:
    return {"message": "FastAPI test route is working"}