# Copyright (c) 2026 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_etl_hta

"""Identity resolution logic using Polars."""

import hashlib
import uuid
from typing import Any

import polars as pl

# UUIDv5 Namespace for INAHTA
NAMESPACE_INAHTA = uuid.uuid5(uuid.NAMESPACE_URL, "https://database.inahta.org")


def _generate_coreason_id_batch(s: pl.Series) -> pl.Series:
    """Generate UUIDv5 from a Series of string hashes.

    This function handles potential nulls gracefully by mapping to None
    when the input hash is missing.
    """
    return pl.Series([str(uuid.uuid5(NAMESPACE_INAHTA, str(val))) if val is not None else None for val in s])


class IdentityResolutionTask:
    """Task to resolve identities for scraped assessments using Polars.

    AGENT INSTRUCTION: Compute `assessment_hash_id` from Title, Agency, and Year.
    Compute `coreason_id` entirely in Python utilizing `.map_batches()`
    on the source ID Series to apply `uuid.uuid5(NAMESPACE_INAHTA, assessment_hash_id)`.
    Yield data specifically structured to prevent dlt from shredding the schema.
    """

    def execute(self, assessments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Resolve identities and structure the payload for the Bronze layer.

        Args:
            assessments: A list of raw dictionaries containing scraped fields.

        Returns:
            A list of formatted dictionaries containing the resolved identities
            and the intact raw data payload.
        """
        if not assessments:
            return []

        # Load scraped dictionaries into a Polars DataFrame
        df = pl.DataFrame(assessments)

        # Ensure required columns exist for hashing, fill nulls with empty string
        for col in ["Title", "Agency", "Year"]:
            if col not in df.columns:
                df = df.with_columns(pl.lit("").alias(col))
            else:
                # Fill nulls with empty string to avoid null propagation during concatenation
                df = df.with_columns(pl.col(col).fill_null(""))

        # Generate `assessment_hash_id` using md5 on Title + Agency + Year
        # We concatenate strings with a pipe delimiter to prevent boundary collisions
        df = df.with_columns(
            pl.concat_str([pl.col("Title"), pl.col("Agency"), pl.col("Year")], separator="|").alias("_concat_key")
        )

        df = df.with_columns(
            pl.col("_concat_key")
            .map_elements(
                lambda x: hashlib.md5(x.encode("utf-8"), usedforsecurity=False).hexdigest(),
                return_dtype=pl.String,
            )
            .alias("assessment_hash_id")
        )

        # Generate `coreason_id` using `.map_batches()`
        df = df.with_columns(pl.col("assessment_hash_id").map_batches(_generate_coreason_id_batch).alias("coreason_id"))

        # Structure the payload: {"assessment_hash_id": hash_id, "coreason_id": coreason_id, "raw_data": scraped_dict}
        # The easiest way to keep "raw_data" is to attach the original dicts, or reconstruct.
        # Let's reconstruct by dropping the generated columns.
        results = []
        df_dicts = df.to_dicts()

        for original_dict, augmented_dict in zip(assessments, df_dicts, strict=True):
            results.append(
                {
                    "assessment_hash_id": augmented_dict["assessment_hash_id"],
                    "coreason_id": augmented_dict["coreason_id"],
                    "raw_data": original_dict,
                }
            )

        return results
