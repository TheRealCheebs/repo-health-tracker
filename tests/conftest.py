"""Pytest configuration for the repo health analyzer."""

import json
import os
from datetime import datetime
from typing import Any, Dict

import pytest


@pytest.fixture
def sample_pr_data() -> Dict[str, Any]:
    """Sample PR data for testing."""
    return {
        "number": 123,
        "title": "Test PR",
        "state": "MERGED",
        "createdAt": "2023-01-01T12:00:00Z",
        "mergedAt": "2023-01-02T12:00:00Z",
        "author": {"login": "testuser"},
        "mergedBy": {"login": "reviewer"},
        "reviews": {
            "edges": [
                {
                    "node": {
                        "author": {"login": "reviewer"},
                        "createdAt": "2023-01-01T15:00:00Z",
                        "state": "APPROVED",
                    }
                }
            ]
        },
        "comments": {
            "edges": [
                {
                    "node": {
                        "author": {"login": "commenter"},
                        "createdAt": "2023-01-01T16:00:00Z",
                    }
                }
            ]
        },
    }


@pytest.fixture
def sample_issue_data() -> Dict[str, Any]:
    """Sample issue data for testing."""
    return {
        "number": 456,
        "title": "Test Issue",
        "state": "CLOSED",
        "createdAt": "2023-01-01T10:00:00Z",
        "closedAt": "2023-01-03T10:00:00Z",
        "author": {"login": "testuser"},
        "comments": {
            "edges": [
                {
                    "node": {
                        "author": {"login": "commenter"},
                        "createdAt": "2023-01-01T11:00:00Z",
                    }
                }
            ]
        },
    }


@pytest.fixture
def sample_prs_data(sample_pr_data) -> list[Dict[str, Any]]:
    """Sample PRs data for testing."""
    return [sample_pr_data]


@pytest.fixture
def sample_issues_data(sample_issue_data) -> list[Dict[str, Any]]:
    """Sample issues data for testing."""
    return [sample_issue_data]


@pytest.fixture
def temp_data_dir(tmp_path) -> str:
    """Create a temporary data directory with sample files."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Create sample PRs file
    prs_file = data_dir / "prs_raw.json"
    prs_file.write_text(
        json.dumps(
            [
                {
                    "number": 123,
                    "title": "Test PR",
                    "state": "MERGED",
                    "createdAt": "2023-01-01T12:00:00Z",
                    "mergedAt": "2023-01-02T12:00:00Z",
                    "author": {"login": "testuser"},
                    "mergedBy": {"login": "reviewer"},
                    "reviews": {
                        "edges": [
                            {
                                "node": {
                                    "author": {"login": "reviewer"},
                                    "createdAt": "2023-01-01T15:00:00Z",
                                    "state": "APPROVED",
                                }
                            }
                        ]
                    },
                    "comments": {
                        "edges": [
                            {
                                "node": {
                                    "author": {"login": "commenter"},
                                    "createdAt": "2023-01-01T16:00:00Z",
                                }
                            }
                        ]
                    },
                }
            ]
        )
    )

    # Create sample issues file
    issues_file = data_dir / "issues_raw.json"
    issues_file.write_text(
        json.dumps(
            [
                {
                    "number": 456,
                    "title": "Test Issue",
                    "state": "CLOSED",
                    "createdAt": "2023-01-01T10:00:00Z",
                    "closedAt": "2023-01-03T10:00:00Z",
                    "author": {"login": "testuser"},
                    "comments": {
                        "edges": [
                            {
                                "node": {
                                    "author": {"login": "commenter"},
                                    "createdAt": "2023-01-01T11:00:00Z",
                                }
                            }
                        ]
                    },
                }
            ]
        )
    )

    return str(data_dir)


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing."""
    monkeypatch.setenv("GITHUB_TOKEN", "test_token")
    monkeypatch.setenv("GITHUB_OWNER", "test_owner")
    monkeypatch.setenv("GITHUB_REPO", "test_repo")
    monkeypatch.setenv("START_DATE", "2023-01-01")
