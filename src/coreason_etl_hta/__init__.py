# Copyright (c) 2026 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_etl_hta

"""
ETL pipeline for aggregating Health Technology Assessment (HTA) reports data
"""

__version__ = "0.1.0"
__author__ = "Akshaya M"
__email__ = "akshaya.movvar@coreason.ai"

from .main import run_pipeline

__all__ = ["run_pipeline"]
