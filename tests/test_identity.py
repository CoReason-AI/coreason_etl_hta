# Copyright (c) 2026 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_etl_hta

"""Tests for identity resolution logic using Polars."""

import hashlib
import uuid

import pytest

from coreason_etl_hta.identity import NAMESPACE_INAHTA, IdentityResolutionTask


@pytest.fixture
def identity_task() -> IdentityResolutionTask:
    """Fixture providing a configured IdentityResolutionTask."""
    return IdentityResolutionTask()


def test_identity_resolution_empty_list(identity_task: IdentityResolutionTask) -> None:
    """Test identity resolution returns empty list when given empty input."""
    assert identity_task.execute([]) == []


def test_identity_resolution_basic_success(identity_task: IdentityResolutionTask) -> None:
    """Test basic successful identity resolution."""
    raw_data = {
        "Title": "Test Title",
        "Agency": "Test Agency",
        "Year": "2023",
        "Type": "Full Assessment",
    }
    results = identity_task.execute([raw_data])
    assert len(results) == 1

    expected_hash_id = hashlib.md5(b"Test Title|Test Agency|2023", usedforsecurity=False).hexdigest()
    expected_coreason_id = str(uuid.uuid5(NAMESPACE_INAHTA, expected_hash_id))

    assert results[0]["assessment_hash_id"] == expected_hash_id
    assert results[0]["coreason_id"] == expected_coreason_id
    assert results[0]["raw_data"] == raw_data


def test_identity_resolution_missing_fields(identity_task: IdentityResolutionTask) -> None:
    """Test identity resolution handles missing fields safely."""
    raw_data = {
        "Title": "Test Title 2",
        # Missing Agency and Year
    }
    results = identity_task.execute([raw_data])
    assert len(results) == 1

    # Should default to empty strings
    expected_hash_id = hashlib.md5(b"Test Title 2||", usedforsecurity=False).hexdigest()
    expected_coreason_id = str(uuid.uuid5(NAMESPACE_INAHTA, expected_hash_id))

    assert results[0]["assessment_hash_id"] == expected_hash_id
    assert results[0]["coreason_id"] == expected_coreason_id
    assert results[0]["raw_data"] == raw_data


def test_identity_resolution_none_fields(identity_task: IdentityResolutionTask) -> None:
    """Test identity resolution handles None values safely."""
    raw_data = {
        "Title": "Test Title 3",
        "Agency": None,
        "Year": None,
    }
    results = identity_task.execute([raw_data])
    assert len(results) == 1

    # Should replace None with empty strings
    expected_hash_id = hashlib.md5(b"Test Title 3||", usedforsecurity=False).hexdigest()
    expected_coreason_id = str(uuid.uuid5(NAMESPACE_INAHTA, expected_hash_id))

    assert results[0]["assessment_hash_id"] == expected_hash_id
    assert results[0]["coreason_id"] == expected_coreason_id
    assert results[0]["raw_data"] == raw_data


def test_identity_resolution_multiple_records(identity_task: IdentityResolutionTask) -> None:
    """Test identity resolution processes multiple records concurrently."""
    assessments = [
        {"Title": "Title A", "Agency": "Agency A", "Year": "2020"},
        {"Title": "Title B", "Agency": "Agency B", "Year": "2021"},
    ]
    results = identity_task.execute(assessments)
    assert len(results) == 2

    hash_a = hashlib.md5(b"Title A|Agency A|2020", usedforsecurity=False).hexdigest()
    coreason_a = str(uuid.uuid5(NAMESPACE_INAHTA, hash_a))
    assert results[0]["assessment_hash_id"] == hash_a
    assert results[0]["coreason_id"] == coreason_a

    hash_b = hashlib.md5(b"Title B|Agency B|2021", usedforsecurity=False).hexdigest()
    coreason_b = str(uuid.uuid5(NAMESPACE_INAHTA, hash_b))
    assert results[1]["assessment_hash_id"] == hash_b
    assert results[1]["coreason_id"] == coreason_b
