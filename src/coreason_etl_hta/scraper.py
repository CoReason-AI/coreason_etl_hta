# Copyright (c) 2026 CoReason, Inc.
# Licensed under the Prosperity Public License 3.0

import time
from typing import Any
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from coreason_etl_hta.config import InahtaConfig
from coreason_etl_hta.utils.logger import logger

class ScrapeInahtaPageTask:
    def __init__(self, config: InahtaConfig) -> None:
        self.config = config
        self.session = self._build_session()

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
            "Referer": "https://database.inahta.org/",
        })
        
        cookie_string = "_gid=GA1.2.98598860.1774412198; XSRF-TOKEN=eyJpdiI6IlhXd3I1UVBRVis0YjRVdjlcL3BUNnhRPT0iLCJ2YWx1ZSI6InMyNzRwRnhRVzgwXC9RNHlRck5zbUZlZWMraW1BbXJ3QXdVRUYweUNvUVFnYmFYYlRYYjVuWGlcL2VqdG5tZEZhNiIsIm1hYyI6IjdlMTM3OTNkNDY3ZTlmM2YyNWVlNmQyMzBkMWYxZTA2MTYzOGI1OTg0NjYyMDMxYzM1NjA4OTYzZjBjODRiNzgifQ%3D%3D; hta_database_session=eyJpdiI6InlaelNTQ3VsdEdyc0VlR1V1aHBmNkE9PSIsInZhbHVlIjoiSmdzQlZPODJTaTgzNlNUb0o3aHdXR3lsenF6cGorcFMxT3VLYlJvcmNVTzhXY2F2S1dDdzJGUFRTNUtKNmdycCIsIm1hYyI6IjlmMjM2NGQ3ZjcxNDk5ZmRkNjdjOTQ3ZTYyNzEyYjEwMThmZTI0YjcyYTA3ZDVkMjRmMTM0MDNlNTE3NDI5MjIifQ%3D%3D"
        
        for cookie in cookie_string.split("; "):
            if "=" in cookie:
                key, value = cookie.split("=", 1)
                session.cookies.set(key, value)

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
        logger.info(f"Scraping INAHTA page {page_number}")
        
        # Lowered crawl delay to 0.2 seconds so the 248 pages download faster!
        time.sleep(0.2)

        url = f"https://database.inahta.org/?page={page_number}"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
        except requests.RequestException:
            logger.exception(f"Failed to fetch INAHTA page {page_number}")
            return [], False

        soup = BeautifulSoup(response.text, "html.parser")
        assessments: list[dict[str, Any]] = []

        rows = soup.find_all("tr")
        for row in rows:
            cols = row.find_all(["td", "th"])
            
            if len(cols) >= 4:
                texts = [col.get_text(separator=" ", strip=True) for col in cols]
                title = texts[3]
                
                if title.lower() == "title" or not title:
                    continue
                    
                raw_data = {
                    "Title": title,
                    "Agency": texts[2],
                    "Year": texts[1],
                    "Country": "Unknown", # Set to Unknown so it doesn't get filtered out of the Gold layer
                    "Type": "Unknown",
                }
                assessments.append(raw_data)

        # The pipeline will now ONLY stop when it hits a page that has 0 records on it.
        has_next = len(assessments) > 0

        return assessments, has_next
