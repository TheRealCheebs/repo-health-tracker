# tests/test_engine/test_metrics.py

import pytest
from datetime import datetime, timezone, timedelta

from src.repo_health.engine.metrics import MetricsCalculator

# Use static, absolute dates for predictable test results
NOW = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def sample_prs():
    """Provides a sample list of PRs with static dates."""
    return [
        {
            "number": 1,
            "title": "First PR by user1",
            "state": "MERGED",
            "createdAt": (NOW - timedelta(days=10)).isoformat().replace("+00:00", "Z"),
            "mergedAt": (NOW - timedelta(days=8)).isoformat().replace("+00:00", "Z"),
            "author": {"login": "user1", "id": 101},
            "mergedBy": {"login": "user2", "id": 102},
            "labels": ["enhancement"],
            "reviews": [
                {
                    "author": {"login": "user2", "id": 102},
                    "submittedAt": (NOW - timedelta(days=9))
                    .isoformat()
                    .replace("+00:00", "Z"),
                    "state": "APPROVED",
                }
            ],
            "comments": [],
        },
        {
            "number": 2,
            "title": "Second PR by user1",
            "state": "OPEN",
            "createdAt": (NOW - timedelta(days=5)).isoformat().replace("+00:00", "Z"),
            "mergedAt": None,
            "author": {"login": "user1", "id": 101},
            "mergedBy": None,
            "labels": [],
            "reviews": [],
            "comments": [
                {
                    "author": {"login": "user2", "id": 102},
                    "createdAt": (NOW - timedelta(days=4, hours=23))
                    .isoformat()
                    .replace("+00:00", "Z"),
                }
            ],
        },
        {
            "number": 3,
            "title": "PR by a new user",
            "state": "OPEN",
            "createdAt": (NOW - timedelta(days=1)).isoformat().replace("+00:00", "Z"),
            "mergedAt": None,
            "author": {"login": "user3", "id": 103},
            "mergedBy": None,
            "labels": [],
            "reviews": [],
            "comments": [],
        },
    ]


@pytest.fixture
def sample_issues():
    """Provides a sample list of Issues with static dates."""
    return [
        {
            "number": 101,
            "title": "First Issue by user1",
            "state": "CLOSED",
            "createdAt": (NOW - timedelta(days=20)).isoformat().replace("+00:00", "Z"),
            "closedAt": (NOW - timedelta(days=15)).isoformat().replace("+00:00", "Z"),
            "author": {"login": "user1", "id": 101},
            "labels": ["bug"],
            "comments": [],
        },
        {
            "number": 102,
            "title": "Issue by a returning user",
            "state": "OPEN",
            "createdAt": (NOW - timedelta(days=2)).isoformat().replace("+00:00", "Z"),
            "closedAt": None,
            "author": {
                "login": "user2",
                "id": 102,
            },  # user2 was a reviewer, now an author
            "labels": [],
            "comments": [],
        },
    ]


def test_compute_execution_metrics(sample_prs):
    """Tests the calculation of execution metrics."""
    calculator = MetricsCalculator(prs=sample_prs, issues=[])
    metrics = calculator.compute_execution_metrics(sample_prs)

    # PR #1: Merge time is 2 days. First response is 1 day (24 hours).
    # PR #2: No merge time. First response is 1 hour.
    # PR #3: No merge time, no response.

    assert metrics["total_prs"] == 3
    # Median of [2.0, None, None] is 2.0
    assert metrics["median_merge_days"] == 2.0
    # Median of [24.0, 1.0] is 12.5 hours
    assert metrics["median_first_response_hours"] == 12.5
    # user2 (ID 102) is the only reviewer, so they have 100% of reviews.
    assert metrics["review_top1_pct"] == 100.0
    assert metrics["review_top2_pct"] == 100.0


def test_compute_community_metrics_all_time(sample_prs, sample_issues):
    """Tests community metrics for the entire project history."""
    all_items = sample_prs + sample_issues
    # All-time window starts at the first contribution
    project_start = NOW - timedelta(days=20)
    calculator = MetricsCalculator(prs=sample_prs, issues=sample_issues)

    metrics = calculator.compute_community_metrics(
        all_items, window_start=project_start
    )

    # Unique AUTHORS: user1 (101), user2 (102), user3 (103).
    assert metrics["unique_contributors"] == 3
    # All are "new" because the window starts with their very first contribution.
    assert metrics["new_contributors"] == 3
    assert metrics["returning_contributors"] == 0
    assert metrics["return_rate_pct"] == 0


def test_compute_community_metrics_rolling_window(sample_prs, sample_issues):
    """Tests community metrics for a rolling window to find returning contributors."""
    all_items = sample_prs + sample_issues
    # Set a window start that is after user1's first contribution
    window_start = NOW - timedelta(days=12)
    calculator = MetricsCalculator(prs=sample_prs, issues=sample_issues)

    metrics = calculator.compute_community_metrics(all_items, window_start=window_start)

    # Unique AUTHORS in the window: user1 (101), user2 (102), user3 (103).
    assert metrics["unique_contributors"] == 3

    # user1's first was 20 days ago, so they are "returning".
    # user2's first was 10 days ago (as reviewer), so they are "new".
    # user3's first was 1 day ago, so they are "new".
    assert metrics["new_contributors"] == 2  # user2, user3
    assert metrics["returning_contributors"] == 1  # user1
    assert metrics["return_rate_pct"] == (1 / 3) * 100
