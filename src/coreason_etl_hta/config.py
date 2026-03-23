# Copyright (c) 2026 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_etl_hta

"""Configuration management for the coreason_etl_hta package.

This module defines the Pydantic configuration models (InahtaConfig, ScrapingConfig)
which handle the INAHTA base URL, crawl delay, and retry limits.
"""

from pydantic import BaseModel, Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class ScrapingConfig(BaseModel):
    """Configuration specific to the web scraping client."""

    base_url: HttpUrl = Field(
        default="https://database.inahta.org/",  # type: ignore[assignment]
        description="The base URL of the INAHTA database search endpoint.",
    )
    crawl_delay: float = Field(
        default=1.0,
        ge=0.0,
        description="The delay in seconds between HTTP requests to respect the target server.",
    )
    retry_limit: int = Field(
        default=3,
        ge=0,
        description="The maximum number of retry attempts for failed HTTP requests (502/503/504).",
    )

    # AGENT INSTRUCTION: Ensure validation constraints are applied exactly as specified in TRD Section 3.


class InahtaConfig(BaseSettings):
    """Root configuration for the coreason_etl_hta pipeline."""

    model_config = SettingsConfigDict(
        env_prefix="INAHTA_",
        env_nested_delimiter="__",
        env_file=".env",
        extra="ignore",
    )

    scraping: ScrapingConfig = Field(default_factory=ScrapingConfig)
