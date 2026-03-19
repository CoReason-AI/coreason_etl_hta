# Copyright (c) 2026 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_etl_hta

"""Main entry point and dlt pipeline configuration for coreason_etl_hta.

This module sets up the dlt pipeline and orchestrates the Bronze layer ingestion.
"""

from collections.abc import Iterator
from typing import Any

import dlt

from coreason_etl_hta.config import InahtaConfig
from coreason_etl_hta.identity import IdentityResolutionTask
from coreason_etl_hta.scraper import ScrapeInahtaPageTask
from coreason_etl_hta.utils.logger import logger


@dlt.resource(
    name="inahta_assessments_raw",
    write_disposition="merge",
    primary_key="assessment_hash_id",
    # max_table_nesting=0 ensures that nested raw_data dicts are saved intact as JSONB
    max_table_nesting=0,
)
def inahta_assessments_resource(config: InahtaConfig | None = None) -> Iterator[dict[str, Any]]:
    """dlt resource for INAHTA assessments.

    Yields data specifically formatted to prevent schema shredding:
    {"assessment_hash_id": hash_id, "coreason_id": coreason_id, "raw_data": scraped_dict}
    """
    if config is None:
        config = InahtaConfig()

    scraper = ScrapeInahtaPageTask(config)
    identity_resolver = IdentityResolutionTask()

    page_number = 1
    has_next = True

    while has_next:
        # 1. Scrape the page
        raw_assessments, has_next = scraper.execute(page_number)

        if not raw_assessments:
            logger.warning(f"No assessments found on page {page_number}. Stopping.")
            break

        # 2. Resolve identities and structure the payload
        resolved_assessments = identity_resolver.execute(raw_assessments)

        # 3. Yield to dlt pipeline
        # Yielding dict conforming to Bronze layer specs:
        # {"assessment_hash_id": hash_id, "coreason_id": coreason_id, "raw_data": scraped_dict}
        yield from resolved_assessments

        page_number += 1


def run_pipeline() -> dlt.Pipeline:
    """Initialize and run the full dlt pipeline."""
    logger.info("Starting INAHTA Bronze Layer ingestion pipeline")

    pipeline = dlt.pipeline(
        pipeline_name="coreason_etl_hta_pipeline",
        destination="postgres",
        dataset_name="bronze",
    )

    load_info = pipeline.run(inahta_assessments_resource())
    logger.info(f"Pipeline finished with load info:\n{load_info}")

    return pipeline
