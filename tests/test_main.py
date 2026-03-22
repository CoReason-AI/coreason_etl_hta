# Copyright (c) 2026 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_etl_hta

"""Tests for the main pipeline execution and dlt configurations."""

from unittest import mock

import pytest
from dlt.pipeline.pipeline import Pipeline

from coreason_etl_hta.config import InahtaConfig, ScrapingConfig
from coreason_etl_hta.main import inahta_assessments_resource, run_pipeline


@pytest.fixture
def config() -> InahtaConfig:
    """Fixture providing a basic config for tests."""
    return InahtaConfig(
        scraping=ScrapingConfig(base_url="https://test.database.inahta.org/", crawl_delay=0.0, retry_limit=1)
    )


@mock.patch("coreason_etl_hta.main.ScrapeInahtaPageTask")
@mock.patch("coreason_etl_hta.main.IdentityResolutionTask")
def test_inahta_assessments_resource_generator(
    mock_identity_class: mock.MagicMock,
    mock_scraper_class: mock.MagicMock,
    config: InahtaConfig,
) -> None:
    """Test that the dlt resource correctly yields items and stops when no more pages."""
    mock_scraper = mock_scraper_class.return_value
    mock_identity = mock_identity_class.return_value

    # Scraper returns some data for page 1, and empty list for page 2
    mock_scraper.execute.side_effect = [
        ([{"Title": "Report 1"}], True),  # Page 1
        ([], False),  # Page 2
    ]

    resolved_data = [
        {"assessment_hash_id": "hash1", "coreason_id": "uuid1", "raw_data": {"Title": "Report 1"}},
    ]
    mock_identity.execute.return_value = resolved_data

    # Initialize resource generator
    resource_generator = inahta_assessments_resource(config)

    # We can cast to list since it's a generator yielding dicts
    results = list(resource_generator)

    # Asserts
    assert len(results) == 1
    assert results[0] == resolved_data[0]

    # Verify calls
    assert mock_scraper.execute.call_count == 2
    mock_scraper.execute.assert_any_call(1)
    mock_scraper.execute.assert_any_call(2)

    mock_identity.execute.assert_called_once_with([{"Title": "Report 1"}])


@mock.patch("coreason_etl_hta.main.ScrapeInahtaPageTask")
@mock.patch("coreason_etl_hta.main.IdentityResolutionTask")
def test_inahta_assessments_resource_multiple_pages(
    mock_identity_class: mock.MagicMock,
    mock_scraper_class: mock.MagicMock,
    config: InahtaConfig,
) -> None:
    """Test the resource correctly handles multiple pages where the last page has no next link."""
    mock_scraper = mock_scraper_class.return_value
    mock_identity = mock_identity_class.return_value

    mock_scraper.execute.side_effect = [
        ([{"Title": "Report 1"}], True),  # Page 1
        ([{"Title": "Report 2"}], False),  # Page 2 (last page)
    ]

    mock_identity.execute.side_effect = [
        [{"assessment_hash_id": "h1", "coreason_id": "u1", "raw_data": {"Title": "Report 1"}}],
        [{"assessment_hash_id": "h2", "coreason_id": "u2", "raw_data": {"Title": "Report 2"}}],
    ]

    results = list(inahta_assessments_resource(config))

    assert len(results) == 2
    assert results[0]["assessment_hash_id"] == "h1"
    assert results[1]["assessment_hash_id"] == "h2"

    assert mock_scraper.execute.call_count == 2
    mock_scraper.execute.assert_any_call(1)
    mock_scraper.execute.assert_any_call(2)


@mock.patch("coreason_etl_hta.main.ScrapeInahtaPageTask")
@mock.patch("coreason_etl_hta.main.IdentityResolutionTask")
def test_inahta_assessments_resource_empty_but_has_next(
    mock_identity_class: mock.MagicMock,
    mock_scraper_class: mock.MagicMock,
    config: InahtaConfig,
) -> None:
    """Test the resource breaks the loop if an empty list is returned despite has_next=True."""
    mock_scraper = mock_scraper_class.return_value
    mock_identity = mock_identity_class.return_value

    mock_scraper.execute.side_effect = [
        ([{"Title": "Report 1"}], True),  # Page 1
        ([], True),  # Page 2: empty list but has_next is erroneously True
    ]

    mock_identity.execute.side_effect = [
        [{"assessment_hash_id": "h1", "coreason_id": "u1", "raw_data": {"Title": "Report 1"}}],
    ]

    results = list(inahta_assessments_resource(config))

    assert len(results) == 1
    assert results[0]["assessment_hash_id"] == "h1"

    # Verify it stopped at page 2 instead of looping infinitely
    assert mock_scraper.execute.call_count == 2
    mock_identity.execute.assert_called_once()


@mock.patch("coreason_etl_hta.main.ScrapeInahtaPageTask")
def test_inahta_assessments_resource_exception_propagation(
    mock_scraper_class: mock.MagicMock,
    config: InahtaConfig,
) -> None:
    """Test that unexpected exceptions from dependencies bubble up."""
    mock_scraper = mock_scraper_class.return_value

    mock_scraper.execute.side_effect = Exception("Simulated fatal scraper failure")

    with pytest.raises(Exception, match="Simulated fatal scraper failure"):
        list(inahta_assessments_resource(config))


@mock.patch("coreason_etl_hta.main.InahtaConfig")
@mock.patch("coreason_etl_hta.main.ScrapeInahtaPageTask")
@mock.patch("coreason_etl_hta.main.IdentityResolutionTask")
def test_inahta_assessments_resource_default_config(
    mock_identity_class: mock.MagicMock,
    mock_scraper_class: mock.MagicMock,
    mock_config_class: mock.MagicMock,
) -> None:
    """Test that the dlt resource correctly initializes InahtaConfig when None is passed."""
    mock_scraper = mock_scraper_class.return_value

    # Scraper returns empty immediately
    mock_scraper.execute.return_value = ([], False)

    mock_config = mock_config_class.return_value

    # Initialize resource generator without config
    resource_generator = inahta_assessments_resource(None)
    list(resource_generator)

    mock_config_class.assert_called_once()
    mock_scraper_class.assert_called_once_with(mock_config)
    mock_identity_class.assert_called_once()


@mock.patch("coreason_etl_hta.main.dlt.pipeline")
@mock.patch("coreason_etl_hta.main.inahta_assessments_resource")
def test_run_pipeline(mock_resource: mock.MagicMock, mock_pipeline: mock.MagicMock) -> None:
    """Test pipeline initialization and execution."""
    mock_pipeline_instance = mock.MagicMock(spec=Pipeline)
    mock_pipeline.return_value = mock_pipeline_instance
    mock_pipeline_instance.run.return_value = "Mock Load Info"

    mock_resource_instance = mock.MagicMock()
    mock_resource.return_value = mock_resource_instance

    pipeline = run_pipeline()

    # Asserts
    assert pipeline == mock_pipeline_instance
    mock_pipeline.assert_called_once_with(
        pipeline_name="coreason_etl_hta_pipeline",
        destination="postgres",
        dataset_name="bronze",
    )
    mock_pipeline_instance.run.assert_called_once_with(mock_resource_instance)
    mock_resource.assert_called_once()


def test_dlt_schema_naming_conventions() -> None:
    """Test that the dlt resource and dataset naming strictly follow the Gold/Silver/Bronze pattern."""
    assert inahta_assessments_resource.name == "coreason_etl_hta_bronze_inahta_assessments"
