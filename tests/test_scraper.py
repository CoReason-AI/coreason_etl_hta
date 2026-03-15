# Copyright (c) 2026 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_etl_hta

"""Unit tests for the web scraping client."""

from unittest import mock

import pytest
import responses
from requests.exceptions import RequestException

from coreason_etl_hta.config import InahtaConfig, ScrapingConfig
from coreason_etl_hta.scraper import ScrapeInahtaPageTask


@pytest.fixture
def config() -> InahtaConfig:
    """Fixture to provide a standard configuration."""
    return InahtaConfig(
        scraping=ScrapingConfig(base_url="https://database.inahta.org/", crawl_delay=0.1, retry_limit=3)
    )


@pytest.fixture
def scraper(config: InahtaConfig) -> ScrapeInahtaPageTask:
    """Fixture to provide a configured ScrapeInahtaPageTask instance."""
    return ScrapeInahtaPageTask(config)


@responses.activate
@mock.patch("time.sleep")
def test_scrape_inahta_page_success(mock_sleep: mock.MagicMock, scraper: ScrapeInahtaPageTask) -> None:
    """Test successful scraping of a page with valid HTML data."""
    url = "https://database.inahta.org/?filter-country=&filter-type=&page=1#"

    html_content = """
    <html>
        <body>
            <div class="search-result">
                <h3 class="title">Test Report 1</h3>
                <span class="agency">CADTH</span>
                <span class="country">Canada</span>
                <span class="year">2023</span>
                <span class="type">Rapid Assessment</span>
            </div>
            <div class="search-result">
                <h3 class="title">Test Report 2</h3>
                <span class="agency">NICE</span>
                <!-- Missing country, year, and type to test robustness -->
            </div>
            <a class="next-page" href="?page=2">Next</a>
        </body>
    </html>
    """

    responses.add(responses.GET, url, body=html_content, status=200)

    assessments, has_next = scraper.execute(page_number=1)

    # Verify sleep was called for politeness
    mock_sleep.assert_called_once_with(0.1)

    # Verify results
    assert len(assessments) == 2
    assert assessments[0] == {
        "Title": "Test Report 1",
        "Agency": "CADTH",
        "Country": "Canada",
        "Year": "2023",
        "Type": "Rapid Assessment",
    }
    assert assessments[1] == {
        "Title": "Test Report 2",
        "Agency": "NICE",
        "Country": "",
        "Year": "",
        "Type": "",
    }
    assert has_next is True


@responses.activate
@mock.patch("time.sleep")
def test_scrape_inahta_page_table_fallback(mock_sleep: mock.MagicMock, scraper: ScrapeInahtaPageTask) -> None:
    """Test successful scraping of a page with table rows data structure."""
    url = "https://database.inahta.org/?filter-country=&filter-type=&page=2#"

    html_content = """
    <html>
        <body>
            <table>
                <tr class="assessment-row">
                    <td class="title-col">Test Report 3</td>
                    <td class="agency-col">HAS</td>
                    <td class="country-col">France</td>
                    <td class="year-col">2022</td>
                    <td class="type-col">Full Report</td>
                </tr>
            </table>
            <!-- No next page link -->
        </body>
    </html>
    """

    responses.add(responses.GET, url, body=html_content, status=200)

    assessments, has_next = scraper.execute(page_number=2)

    mock_sleep.assert_called_once_with(0.1)

    assert len(assessments) == 1
    assert assessments[0]["Title"] == "Test Report 3"
    assert assessments[0]["Agency"] == "HAS"
    assert has_next is False


@responses.activate
@mock.patch("time.sleep")
def test_scrape_inahta_page_empty(mock_sleep: mock.MagicMock, scraper: ScrapeInahtaPageTask) -> None:
    """Test scraping a page with no results."""
    url = "https://database.inahta.org/?filter-country=&filter-type=&page=3#"
    html_content = "<html><body><p>No results found.</p></body></html>"

    responses.add(responses.GET, url, body=html_content, status=200)

    assessments, has_next = scraper.execute(page_number=3)

    mock_sleep.assert_called_once_with(0.1)

    assert assessments == []
    assert has_next is False


@responses.activate
@mock.patch("time.sleep")
def test_scrape_inahta_page_http_error(mock_sleep: mock.MagicMock, scraper: ScrapeInahtaPageTask) -> None:
    """Test scraping a page that returns a 404 (or other non-retried HTTP error)."""
    url = "https://database.inahta.org/?filter-country=&filter-type=&page=4#"
    responses.add(responses.GET, url, status=404)

    assessments, has_next = scraper.execute(page_number=4)

    mock_sleep.assert_called_once_with(0.1)

    assert assessments == []
    assert has_next is False


@mock.patch("time.sleep")
@mock.patch("requests.Session.get")
def test_scrape_inahta_page_retries_and_fails(
    mock_get: mock.MagicMock, mock_sleep: mock.MagicMock, scraper: ScrapeInahtaPageTask
) -> None:
    """Test that the scraper respects retries on 503 and then eventually fails gracefully.

    Using mock.patch for requests.Session.get directly, since urllib3.util.Retry works beneath
    the layer that `responses` intercepts, and responses doesn't support the urllib3 retries natively.
    """

    # We will just verify that the HTTPAdapter was correctly mounted
    # with a Retry object containing the expected properties during `__init__`.
    adapter = scraper.session.adapters.get("https://")
    assert adapter is not None
    # We must type ignore here as the base class adapter doesn't type hint max_retries
    assert adapter.max_retries.total == 3  # type: ignore[attr-defined]
    assert sorted(adapter.max_retries.status_forcelist) == [502, 503, 504]  # type: ignore[attr-defined]

    # Simulate a final RequestException coming out of the get request
    # (this simulates what happens after urllib3 finishes all its retries)
    mock_get.side_effect = RequestException("Max retries exceeded")

    assessments, has_next = scraper.execute(page_number=5)

    mock_sleep.assert_called_once_with(0.1)

    assert assessments == []
    assert has_next is False


@responses.activate
@mock.patch("time.sleep")
def test_scrape_inahta_page_network_exception(mock_sleep: mock.MagicMock, scraper: ScrapeInahtaPageTask) -> None:
    """Test scraping a page that raises a generic network exception."""
    url = "https://database.inahta.org/?filter-country=&filter-type=&page=6#"

    responses.add(responses.GET, url, body=RequestException("Network timeout"))

    assessments, has_next = scraper.execute(page_number=6)

    mock_sleep.assert_called_once_with(0.1)

    assert assessments == []
    assert has_next is False
