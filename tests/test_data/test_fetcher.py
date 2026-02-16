# tests/test_data/test_fetcher.py

import json
import pytest
from unittest.mock import patch

from src.repo_health.data.fetcher import GitHubDataFetcher
from datetime import datetime, timezone

# This is a mock GraphQL response that mimics the real GitHub API structure
MOCK_PR_RESPONSE = {
    "data": {
        "repository": {
            "pullRequests": {
                "edges": [
                    {
                        "node": {
                            "number": 123,
                            "title": "A test PR",
                            "state": "MERGED",
                            "createdAt": "2023-10-26T10:00:00Z",
                            "mergedAt": "2023-10-27T10:00:00Z",
                            "author": {"login": "testuser", "databaseId": 501},
                            "mergedBy": {"login": "reviewer", "databaseId": 502},
                            "labels": {"edges": [{"node": {"name": "bug"}}]},
                            "reviews": {"edges": []},
                            "comments": {"edges": []},
                        },
                        "cursor": "abc123",
                    }
                ],
                "pageInfo": {"hasNextPage": False},
            }
        }
    }
}

MOCK_ISSUE_RESPONSE = {
    "data": {
        "repository": {
            "issues": {
                "edges": [
                    {
                        "node": {
                            "number": 456,
                            "title": "A test issue",
                            "state": "OPEN",
                            "createdAt": "2023-10-25T10:00:00Z",
                            "closedAt": None,
                            "author": {"login": "another-user", "databaseId": 503},
                            "labels": {"edges": []},
                            "comments": {"edges": []},
                        },
                        "cursor": "def456",
                    }
                ],
                "pageInfo": {"hasNextPage": False},
            }
        }
    }
}


@patch("src.repo_health.data.fetcher.requests.post")
def test_fetch_prs_normalizes_data(mock_post, tmp_path):
    """Tests that the fetcher correctly normalizes PR data."""
    # Configure the mock to return our fake response
    mock_response = mock_post.return_value
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_PR_RESPONSE
    mock_response.raise_for_status.return_value = None

    start_date = datetime(2023, 10, 1, tzinfo=timezone.utc)
    fetcher = GitHubDataFetcher(
        token="fake_token",
        owner="fake_owner",
        repo="fake_repo",
        start_date=start_date,
        output_dir=str(tmp_path),
    )

    prs = fetcher.fetch_prs()

    assert len(prs) == 1
    pr = prs[0]

    # Check that the data has been flattened and normalized
    assert pr["number"] == 123
    assert pr["author"] == {"login": "testuser", "id": 501}
    assert pr["mergedBy"] == {"login": "reviewer", "id": 502}
    assert pr["labels"] == ["bug"]  # Should be a list of strings
    assert pr["reviews"] == []  # Should be a list of dicts
    assert pr["comments"] == []  # Should be a list of dicts


@patch("src.repo_health.data.fetcher.requests.post")
def test_fetch_issues_normalizes_data(mock_post, tmp_path):
    """Tests that the fetcher correctly normalizes issue data."""
    mock_response = mock_post.return_value
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_ISSUE_RESPONSE
    mock_response.raise_for_status.return_value = None

    start_date = datetime(2023, 10, 1, tzinfo=timezone.utc)
    fetcher = GitHubDataFetcher(
        token="fake_token",
        owner="fake_owner",
        repo="fake_repo",
        start_date=start_date,
        output_dir=str(tmp_path),
    )

    issues = fetcher.fetch_issues()

    assert len(issues) == 1
    issue = issues[0]

    assert issue["number"] == 456
    assert issue["author"] == {"login": "another-user", "id": 503}
    assert issue["labels"] == []  # Should be a list of strings
