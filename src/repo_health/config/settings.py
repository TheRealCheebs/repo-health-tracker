# src/repo_health/config/settings.py
"""Settings and environment variables for the repo health analyzer."""

import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings."""

    github_token: str
    github_owner: str
    github_repo: str
    start_date: datetime  # This will be parsed from a string

    model_config = {"env_file": ".env"}

    @field_validator("start_date", mode="before")
    @classmethod
    def parse_start_date(cls, value: str) -> datetime:
        """Parse the start date string and make it timezone-aware (UTC)."""
        # First, parse the string into a naive datetime object
        naive_dt = datetime.strptime(value, "%Y-%m-%d")
        # Then, make it aware by assigning the UTC timezone
        aware_dt = naive_dt.replace(tzinfo=timezone.utc)
        return aware_dt


def get_settings() -> Settings:
    """Get the application settings."""
    # Pydantic will automatically handle loading from .env and validation
    return Settings()
