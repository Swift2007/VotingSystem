import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_title: str = os.getenv("APP_TITLE", "Voting System API")


settings = Settings()
