# src/repo_health/engine/metrics.py

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

from ..utils.helpers import (
    parse_datetime,
    now_utc,
    safe_median,
    group_by_month,
    filter_last_days,
)


class MetricsCalculator:
    """Calculates various metrics for repository health analysis."""

    def __init__(self, prs: List[Dict[str, Any]], issues: List[Dict[str, Any]]):
        """Initialize the calculator with PR and issue data."""
        self.prs = prs
        self.issues = issues
        self.all_items = prs + issues
        self.first_seen_global = self._build_first_seen_map()

    def _build_first_seen_map(self) -> Dict[int, datetime]:
        """Builds a map of each user ID to their first-ever contribution timestamp."""
        first_seen = {}
        sorted_items = sorted(
            self.all_items,
            key=lambda x: parse_datetime(x.get("createdAt"))
            or datetime.max.replace(tzinfo=timezone.utc),
        )

        for item in sorted_items:
            author_obj = item.get("author")
            if not author_obj or not author_obj.get("id"):
                continue

            user_id = author_obj["id"]
            created = parse_datetime(item.get("createdAt"))

            if user_id and created and user_id not in first_seen:
                first_seen[user_id] = created

        return first_seen

    def compute_execution_metrics(
        self, prs_subset: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculates execution metrics like merge time and response time."""
        merge_durations = []
        first_response_times = []
        reviewer_counts = Counter()

        for pr in prs_subset:
            created = parse_datetime(pr.get("createdAt"))
            merged = parse_datetime(pr.get("mergedAt"))

            if created and merged:
                merge_durations.append((merged - created).total_seconds() / 86400)

            author_obj = pr.get("author")
            author_id = author_obj.get("id") if author_obj else None
            response_events = []

            for comment in pr.get("comments") or []:
                comment_author_obj = comment.get("author")
                if (
                    comment_author_obj
                    and comment_author_obj.get("id") != author_id
                    and comment_author_obj.get("login", "").lower() != "codecov[bot]"
                ):
                    response_events.append(parse_datetime(comment.get("createdAt")))

            for review in pr.get("reviews") or []:
                review_author_obj = review.get("author")
                if review_author_obj and review_author_obj.get("id") != author_id:
                    response_events.append(parse_datetime(review.get("submittedAt")))
                    reviewer_counts[review_author_obj["id"]] += 1

            if created and response_events:
                first_response = min(filter(None, response_events))
                first_response_times.append(
                    (first_response - created).total_seconds() / 3600
                )

        review_total = sum(reviewer_counts.values())
        review_top1_pct, review_top2_pct = 0, 0
        if review_total > 0:
            top_reviewers = reviewer_counts.most_common(2)

            review_top1_pct = top_reviewers[0][1] / review_total * 100
            review_top2_pct = sum(r[1] for r in top_reviewers) / review_total * 100

        return {
            "median_merge_days": safe_median(merge_durations),
            "median_first_response_hours": safe_median(first_response_times),
            "review_top1_pct": review_top1_pct,
            "review_top2_pct": review_top2_pct,
            "total_prs": len(prs_subset),
            "top_reviewers_by_id": reviewer_counts.most_common(10),
        }

    def compute_community_metrics(
        self, items_subset: List[Dict[str, Any]], window_start: datetime
    ) -> Dict[str, Any]:
        """Calculates community metrics like contributor counts and return rate."""
        author_counts = Counter()
        new_contributors = set()
        returning_contributors = set()

        for item in items_subset:
            author_obj = item.get("author")
            if not author_obj or not author_obj.get("id"):
                continue

            user_id = author_obj["id"]
            created = parse_datetime(item.get("createdAt"))

            if not created:
                continue

            author_counts[user_id] += 1

            first_seen = self.first_seen_global.get(user_id)
            if first_seen and first_seen >= window_start:
                new_contributors.add(user_id)
            else:
                returning_contributors.add(user_id)

        total_actions = sum(author_counts.values())
        author_top1_pct, author_top2_pct = 0, 0
        if total_actions > 0:
            top_authors = author_counts.most_common(2)
            author_top1_pct = top_authors[0][1] / total_actions * 100
            if len(top_authors) > 1:
                author_top2_pct = sum(a[1] for a in top_authors) / total_actions * 100

        return {
            "unique_contributors": len(author_counts),
            "new_contributors": len(new_contributors),
            "returning_contributors": len(returning_contributors),
            "return_rate_pct": (
                len(returning_contributors) / len(author_counts) * 100
                if author_counts
                else 0
            ),
            "author_top1_pct": author_top1_pct,
            "author_top2_pct": author_top2_pct,
            "top_authors_by_id": author_counts.most_common(10),
        }

    def compute_backlog(self, as_of: datetime) -> Dict[str, Any]:
        """Computes backlog metrics as of a specific point in time."""
        open_prs = []
        open_issues = []

        for pr in self.prs:
            created = parse_datetime(pr.get("createdAt"))
            merged = parse_datetime(pr.get("mergedAt"))
            if created and created <= as_of and (not merged or merged > as_of):
                open_prs.append(pr)

        for issue in self.issues:
            created = parse_datetime(issue.get("createdAt"))
            if created and created <= as_of and issue.get("state") != "CLOSED":
                open_issues.append(issue)

        return {
            "open_pr_count": len(open_prs),
            "open_issue_count": len(open_issues),
            "median_open_pr_age_days": safe_median(
                [(as_of - parse_datetime(pr["createdAt"])).days for pr in open_prs]
            ),
            "median_open_issue_age_days": safe_median(
                [
                    (as_of - parse_datetime(issue["createdAt"])).days
                    for issue in open_issues
                ]
            ),
        }

    def analyze_all(self) -> Dict[str, Any]:
        """Orchestrates the full analysis across all-time, rolling, and monthly windows."""
        result = {}

        project_start = (
            min(self.first_seen_global.values())
            if self.first_seen_global
            else now_utc()
        )

        result["all_time"] = {
            "execution": self.compute_execution_metrics(self.prs),
            "community": self.compute_community_metrics(self.all_items, project_start),
        }

        result["rolling_windows"] = {}
        for days in [365, 180, 90]:
            window_start = now_utc() - timedelta(days=days)
            window_prs = filter_last_days(self.prs, days)
            window_issues = filter_last_days(self.issues, days)
            window_items = window_prs + window_issues

            result["rolling_windows"][f"last_{days}_days"] = {
                "execution": self.compute_execution_metrics(window_prs),
                "community": self.compute_community_metrics(window_items, window_start),
            }

        monthly_prs = group_by_month(self.prs)
        monthly_issues = group_by_month(self.issues)
        all_months = sorted(set(monthly_prs.keys()) | set(monthly_issues.keys()))
        result["monthly"] = {}

        for month in all_months:
            month_prs = monthly_prs.get(month, [])
            month_issues = monthly_issues.get(month, [])
            month_items = month_prs + month_issues

            month_start = datetime.strptime(month + "-01", "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
            next_month = (
                month_start.replace(month=month_start.month % 12 + 1, day=1)
                if month_start.month < 12
                else month_start.replace(year=month_start.year + 1, month=1, day=1)
            )
            month_end = next_month - timedelta(days=1)

            result["monthly"][month] = {
                "execution": self.compute_execution_metrics(month_prs),
                "community": self.compute_community_metrics(month_items, month_start),
                "backlog": self.compute_backlog(month_end),
            }

        return result
