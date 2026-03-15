# Copyright (c) 2026 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_etl_hta

"""Tests for the configuration models."""

import os
from unittest import mock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from coreason_etl_hta.config import InahtaConfig, ScrapingConfig


def test_scraping_config_defaults() -> None:
    """Test that ScrapingConfig initializes with the correct default values."""
    config = ScrapingConfig()
    assert str(config.base_url) == "https://database.inahta.org/"
    assert config.crawl_delay == 1.0
    assert config.retry_limit == 3


def test_scraping_config_custom_values() -> None:
    """Test that ScrapingConfig initializes correctly with custom values."""
    config = ScrapingConfig(
        base_url="https://test.example.com/",
        crawl_delay=2.5,
        retry_limit=5,
    )
    assert str(config.base_url) == "https://test.example.com/"
    assert config.crawl_delay == 2.5
    assert config.retry_limit == 5


def test_scraping_config_invalid_base_url() -> None:
    """Test that ScrapingConfig raises ValidationError on invalid URL."""
    with pytest.raises(ValidationError):
        ScrapingConfig(base_url="not-a-url")


def test_scraping_config_negative_crawl_delay() -> None:
    """Test that ScrapingConfig raises ValidationError on negative crawl delay."""
    with pytest.raises(ValidationError):
        ScrapingConfig(crawl_delay=-1.0)


def test_scraping_config_negative_retry_limit() -> None:
    """Test that ScrapingConfig raises ValidationError on negative retry limit."""
    with pytest.raises(ValidationError):
        ScrapingConfig(retry_limit=-1)


def test_inahta_config_defaults() -> None:
    """Test that InahtaConfig initializes with default ScrapingConfig."""
    config = InahtaConfig()
    assert isinstance(config.scraping, ScrapingConfig)
    assert str(config.scraping.base_url) == "https://database.inahta.org/"
    assert config.scraping.crawl_delay == 1.0


@mock.patch.dict(os.environ, {"INAHTA_SCRAPING__CRAWL_DELAY": "5.5", "INAHTA_SCRAPING__RETRY_LIMIT": "10"})
def test_inahta_config_env_vars() -> None:
    """Test that InahtaConfig overrides defaults using environment variables."""
    config = InahtaConfig()
    assert config.scraping.crawl_delay == 5.5
    assert config.scraping.retry_limit == 10
    assert str(config.scraping.base_url) == "https://database.inahta.org/"


@settings(max_examples=50)  # type: ignore[misc]
@given(  # type: ignore[misc]
    crawl_delay=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    retry_limit=st.integers(min_value=0, max_value=100),
)
def test_scraping_config_valid_properties(crawl_delay: float, retry_limit: int) -> None:
    """Test that ScrapingConfig accepts valid generated properties."""
    config = ScrapingConfig(crawl_delay=crawl_delay, retry_limit=retry_limit)
    assert config.crawl_delay == crawl_delay
    assert config.retry_limit == retry_limit


@settings(max_examples=50)  # type: ignore[misc]
@given(  # type: ignore[misc]
    crawl_delay=st.floats(max_value=-0.0001, allow_nan=False, allow_infinity=False),
)
def test_scraping_config_invalid_crawl_delay(crawl_delay: float) -> None:
    """Test that ScrapingConfig rejects negative crawl_delays."""
    with pytest.raises(ValidationError):
        ScrapingConfig(crawl_delay=crawl_delay)


@settings(max_examples=50)  # type: ignore[misc]
@given(  # type: ignore[misc]
    retry_limit=st.integers(max_value=-1),
)
def test_scraping_config_invalid_retry_limit(retry_limit: int) -> None:
    """Test that ScrapingConfig rejects negative retry_limits."""
    with pytest.raises(ValidationError):
        ScrapingConfig(retry_limit=retry_limit)
