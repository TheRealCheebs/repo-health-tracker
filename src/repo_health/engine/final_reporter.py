# src/repo_health/engine/final_reporter.py

"""Generates a comprehensive final report combining metrics, scores, and risk analysis."""

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from .metrics import MetricsCalculator
from .scorer import RepoHealthScorer


class FinalReporter:
    """Generates a comprehensive final report."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir

    def _load_raw_data(self) -> tuple[List[Dict], List[Dict]]:
        """Loads raw PR and issue data."""
        prs_path = os.path.join(self.data_dir, "prs_raw.json")
        issues_path = os.path.join(self.data_dir, "issues_raw.json")

        with open(prs_path, "r", encoding="utf-8") as f:
            prs = json.load(f)
        with open(issues_path, "r", encoding="utf-8") as f:
            issues = json.load(f)
        return prs, issues

    def _get_open_items(self, items: List[Dict]) -> List[Dict]:
        """Filters for open items."""
        return [item for item in items if item.get("state") == "OPEN"]

    def _calculate_backlog_snapshot(
        self, open_prs: List[Dict], open_issues: List[Dict]
    ) -> Dict[str, Any]:
        """Calculates detailed backlog metrics."""
        now = datetime.now(timezone.utc)

        def days_old(date_str):
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return (now - dt).days

        def filter_ids_by_age(items, min_days):
            return [
                item["number"]
                for item in items
                if days_old(item["createdAt"]) >= min_days
            ]

        prs_over_365 = filter_ids_by_age(open_prs, 365)
        issues_over_365 = filter_ids_by_age(open_issues, 365)
        issues_over_730 = filter_ids_by_age(open_issues, 730)

        # Calculate median ages
        pr_ages = [days_old(pr["createdAt"]) for pr in open_prs]
        issue_ages = [days_old(issue["createdAt"]) for issue in open_issues]

        return {
            "open_prs": len(open_prs),
            "open_issues": len(open_issues),
            "prs_over_365_days": len(prs_over_365),
            "issues_over_365_days": len(issues_over_365),
            "issues_over_730_days": len(issues_over_730),
            "median_pr_age_days_est": int(sorted(pr_ages)[len(pr_ages) // 2])
            if pr_ages
            else 0,
            "median_issue_age_days_est": int(sorted(issue_ages)[len(issue_ages) // 2])
            if issue_ages
            else 0,
        }

    def _generate_risk_flags(self, snapshot: Dict[str, Any]) -> List[str]:
        """Generates a list of risk flags based on the backlog snapshot."""
        risk_flags = []

        if (
            snapshot["open_prs"] > 0
            and snapshot["prs_over_365_days"] / snapshot["open_prs"] > 0.35
        ):
            risk_flags.append(
                f"{int(100 * snapshot['prs_over_365_days'] / snapshot['open_prs'])}% of open PRs are over 1 year old"
            )

        if (
            snapshot["open_issues"] > 0
            and snapshot["issues_over_365_days"] / snapshot["open_issues"] > 0.6
        ):
            risk_flags.append(
                f"{int(100 * snapshot['issues_over_365_days'] / snapshot['open_issues'])}% of open issues are over 1 year old"
            )

        if snapshot["issues_over_730_days"] > 0:
            risk_flags.append(
                f"{int(100 * snapshot['issues_over_730_days'] / snapshot['open_issues'])}% of open issues are over 2 years old"
            )

        # Add generic backlog warning
        if snapshot["open_issues"] > 20:  # Arbitrary threshold
            risk_flags.append(
                "High issue count suggests tracker reflects historical intent rather than active roadmap"
            )

        return risk_flags

    def _generate_stalled_actions(
        self, open_prs: List[Dict], open_issues: List[Dict]
    ) -> Dict[str, List[int]]:
        """Generates lists of PRs/issues that are likely stalled."""
        return {
            "archive_prs_over_365_days": [
                pr["number"]
                for pr in open_prs
                if (
                    datetime.now(timezone.utc)
                    - datetime.fromisoformat(pr["createdAt"].replace("Z", "+00:00"))
                ).days
                > 365
            ],
            "close_issues_over_730_days": [
                issue["number"]
                for issue in open_issues
                if (
                    datetime.now(timezone.utc)
                    - datetime.fromisoformat(issue["createdAt"].replace("Z", "+00:00"))
                ).days
                > 730
            ],
            "decision_required_prs_180_365_days": [
                pr["number"]
                for pr in open_prs
                if 180
                < (
                    datetime.now(timezone.utc)
                    - datetime.fromisoformat(pr["createdAt"].replace("Z", "+00:00"))
                ).days
                <= 365
            ],
            "decision_required_issues_180_365_days": [
                issue["number"]
                for issue in open_issues
                if 180
                < (
                    datetime.now(timezone.utc)
                    - datetime.fromisoformat(issue["createdAt"].replace("Z", "+00:00"))
                ).days
                <= 365
            ],
        }

    def generate(self) -> Dict[str, Any]:
        """Generates the complete final report."""
        prs, issues = self._load_raw_data()

        # 1. Calculate metrics
        calculator = MetricsCalculator(prs, issues)
        metrics = calculator.analyze_all()

        # 2. Calculate score
        scorer = RepoHealthScorer(metrics)
        score_report = scorer.calculate_overall_score()
        metrics["score"] = score_report

        # 3. Analyze backlog and risks
        open_prs = self._get_open_items(prs)
        open_issues = self._get_open_items(issues)

        backlog_snapshot = self._calculate_backlog_snapshot(open_prs, open_issues)
        risk_flags = self._generate_risk_flags(backlog_snapshot)
        stalled_actions = self._generate_stalled_actions(open_prs, open_issues)

        # 4. Combine everything
        final_report = {
            "report_generated_at": datetime.now(timezone.utc).isoformat(),
            "metrics": metrics,
            "backlog_snapshot": backlog_snapshot,
            "risk_flags": risk_flags,
            "stalled_actions": stalled_actions,
        }

        return final_report

    def generate_summary_report(self) -> Dict[str, Any]:
        """Generates a lean summary report suitable for LLM input."""
        prs, issues = self._load_raw_data()

        # We only need to run the analysis parts that are required for the summary
        calculator = MetricsCalculator(prs, issues)
        metrics = calculator.analyze_all()

        scorer = RepoHealthScorer(metrics)
        score_report = scorer.calculate_overall_score()

        # Analyze backlog and risks
        open_prs = self._get_open_items(prs)
        open_issues = self._get_open_items(issues)

        backlog_snapshot = self._calculate_backlog_snapshot(open_prs, open_issues)
        risk_flags = self._generate_risk_flags(backlog_snapshot)
        stalled_actions = self._generate_stalled_actions(open_prs, open_issues)

        # Combine ONLY the essential parts
        summary_report = {
            "report_generated_at": datetime.now(timezone.utc).isoformat(),
            "score": score_report,
            "backlog_snapshot": backlog_snapshot,
            "risk_flags": risk_flags,
            "stalled_actions": stalled_actions,
        }

        return summary_report
