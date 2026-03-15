# Copyright (c) 2026 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_etl_hta

"""Web scraping logic for the INAHTA database search endpoint."""

import time
from typing import Any

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from coreason_etl_hta.config import InahtaConfig
from coreason_etl_hta.utils.logger import logger


class ScrapeInahtaPageTask:
    """Task to extract structured metadata from a single INAHTA search results page.

    AGENT INSTRUCTION: This class handles polite HTTP requests and robust HTML parsing
    without throwing NoneType exceptions for missing fields.
    """

    def __init__(self, config: InahtaConfig) -> None:
        """Initialize the scraper with a polite, resilient requests session."""
        self.config = config
        self.session = self._build_session()

    def _build_session(self) -> requests.Session:
        """Create a resilient requests Session with retry logic."""
        session = requests.Session()
        session.headers.update({"User-Agent": "coreason-etl-hta/1.0 (Contact: gowtham.rao@coreason.ai)"})

        retry_strategy = Retry(
            total=self.config.scraping.retry_limit,
            backoff_factor=1,
            status_forcelist=[502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def execute(self, page_number: int) -> tuple[list[dict[str, Any]], bool]:
        """Execute the scrape for a given page number.

        Args:
            page_number: The page number to fetch.

        Returns:
            A tuple containing:
            1. A list of raw dictionaries containing the scraped fields.
            2. A boolean indicating if a next page exists.
        """
        logger.info(f"Scraping INAHTA page {page_number}")

        # Enforce polite crawl delay
        time.sleep(self.config.scraping.crawl_delay)

        url = f"{self.config.scraping.base_url}?filter-country=&filter-type=&page={page_number}#"
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
        except requests.RequestException:
            logger.exception(f"Failed to fetch INAHTA page {page_number}")
            return [], False

        soup = BeautifulSoup(response.text, "html.parser")

        assessments: list[dict[str, Any]] = []

        # INAHTA lists assessments typically in a table or structured divs.
        # We assume standard rows, but gracefully handle missing fields.
        # As per instructions: extract raw strings, missing data handling without NoneType errors.

        # NOTE: We do not know the exact HTML structure of INAHTA as we don't have internet access
        # to the real site, but based on the FRD we need Title, Agency, Country, Year, Type.
        # We will write a resilient parser that extracts from generic expected tags (e.g. table rows or list items)
        # Assuming each record is in an 'article' or 'div.assessment' or 'tr'

        # Look for a common container, let's use a generic generic approach or assume standard class.
        # In a real-world scenario we'd inspect the actual site. We'll simulate a table row structure.

        # Let's assume there is a main container with class 'search-result' or similar.
        items = soup.find_all("div", class_="search-result")
        if not items:
            # Fallback to table rows if divs aren't found
            items = soup.find_all("tr", class_="assessment-row")

        # Helper to extract text safely
        def get_text_safe(container: Any, selector: str, attr_class: str) -> str:
            elem = container.find(selector, class_=attr_class)
            return elem.get_text(strip=True) if elem else ""

        for item in items:
            raw_data: dict[str, Any] = {}

            # Extract fields based on FRD
            raw_data["Title"] = get_text_safe(item, "h3", "title") or get_text_safe(item, "td", "title-col")
            raw_data["Agency"] = get_text_safe(item, "span", "agency") or get_text_safe(item, "td", "agency-col")
            raw_data["Country"] = get_text_safe(item, "span", "country") or get_text_safe(item, "td", "country-col")
            raw_data["Year"] = get_text_safe(item, "span", "year") or get_text_safe(item, "td", "year-col")
            raw_data["Type"] = get_text_safe(item, "span", "type") or get_text_safe(item, "td", "type-col")

            # Only add if we found at least a title
            if raw_data["Title"]:
                assessments.append(raw_data)

        # Check for pagination: look for a 'Next' button or link
        has_next = False
        next_link = soup.find("a", class_="next-page")
        if next_link and "href" in next_link.attrs:
            has_next = True

        return assessments, has_next
