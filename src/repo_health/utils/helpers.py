# src/repo_health/utils/helpers.py

from datetime import datetime, timedelta, timezone
from statistics import median
from typing import List, Dict, Any


def parse_datetime(dt_str: str) -> datetime | None:
    """Parses an ISO datetime string, handling 'Z' suffix for UTC."""
    if not dt_str:
        return None
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).astimezone(
        timezone.utc
    )


def now_utc() -> datetime:
    """Returns the current time in UTC."""
    return datetime.now(timezone.utc)


def safe_median(values: List[float]) -> float:
    """Calculates the median of a list, returning 0 for empty lists."""
    return median(values) if values else 0


def group_by_month(items: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Groups a list of items by their creation month."""
    from collections import defaultdict

    buckets = defaultdict(list)
    for item in items:
        created = parse_datetime(item.get("createdAt"))
        if created:
            key = created.strftime("%Y-%m")
            buckets[key].append(item)
    return buckets


def filter_last_days(items: List[Dict[str, Any]], days: int) -> List[Dict[str, Any]]:
    """Filters a list of items to include only those from the last N days."""
    cutoff = now_utc() - timedelta(days=days)
    return [item for item in items if parse_datetime(item.get("createdAt")) >= cutoff]
