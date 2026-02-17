# src/repo_health/engine/scorer.py

"""Deterministic scoring system for repository health."""

from typing import Dict, Any, Tuple


class RepoHealthScorer:
    """Calculates a deterministic repo health score from metrics."""

    def __init__(self, metrics: Dict[str, Any]):
        """Initialize the scorer with a metrics dictionary."""
        self.metrics = metrics
        # --- CONFIGURABLE WEIGHTS ---
        # These should sum to 1.0
        self.weights = {
            "execution": 0.4,
            "community": 0.4,
            "backlog": 0.2,
        }
        # --- CONFIGURABLE TARGETS ---
        # Define what "good" (score=100) and "bad" (score=0) look like
        self.targets = {
            # Lower is better
            "median_merge_days": {"good": 1, "bad": 30},
            "median_first_response_hours": {"good": 2, "bad": 168},  # 1 week
            "review_top1_pct": {"good": 30, "bad": 90},
            # Higher is better
            "return_rate_pct": {"good": 60, "bad": 10},
            # Lower is better
            "median_open_pr_age_days": {"good": 7, "bad": 90},
            "median_open_issue_age_days": {"good": 14, "bad": 180},
        }

    def _score_metric(self, metric_name: str, value: float) -> float:
        """Scores a single metric based on its target range."""
        target = self.targets.get(metric_name)
        if not target:
            return 0.0  # No target defined, score is 0

        good, bad = target["good"], target["bad"]

        # Handle cases where lower is better
        if good < bad:
            if value <= good:
                return 100.0
            if value >= bad:
                return 0.0
            # Linear interpolation between bad and good
            return 100.0 * (bad - value) / (bad - good)

        # Handle cases where higher is better
        else:
            if value >= good:
                return 100.0
            if value <= bad:
                return 0.0
            # Linear interpolation between bad and good
            return 100.0 * (value - bad) / (good - bad)

    def calculate_execution_score(
        self, execution_metrics: Dict[str, Any]
    ) -> Tuple[float, Dict[str, float]]:
        """Calculates the execution health sub-score."""
        scores = {
            "merge_velocity": self._score_metric(
                "median_merge_days", execution_metrics.get("median_merge_days", 0)
            ),
            "responsiveness": self._score_metric(
                "median_first_response_hours",
                execution_metrics.get("median_first_response_hours", 0),
            ),
            "review_bottleneck": self._score_metric(
                "review_top1_pct", execution_metrics.get("review_top1_pct", 0)
            ),
        }
        # Simple average of the three components
        sub_score = sum(scores.values()) / len(scores)
        return sub_score, scores

    def calculate_community_score(
        self, community_metrics: Dict[str, Any]
    ) -> Tuple[float, Dict[str, float]]:
        """Calculates the community health sub-score."""
        scores = {
            "contributor_stickiness": self._score_metric(
                "return_rate_pct", community_metrics.get("return_rate_pct", 0)
            ),
            # We can add more here, like contributor diversity, etc.
        }
        sub_score = sum(scores.values()) / len(scores)
        return sub_score, scores

    def calculate_backlog_score(
        self, backlog_metrics: Dict[str, Any]
    ) -> Tuple[float, Dict[str, float]]:
        """Calculates the backlog health sub-score."""
        scores = {
            "pr_age": self._score_metric(
                "median_open_pr_age_days",
                backlog_metrics.get("median_open_pr_age_days", 0),
            ),
            "issue_age": self._score_metric(
                "median_open_issue_age_days",
                backlog_metrics.get("median_open_issue_age_days", 0),
            ),
        }
        sub_score = sum(scores.values()) / len(scores)
        return sub_score, scores

    def calculate_overall_score(self) -> Dict[str, Any]:
        """Calculates the overall repo health score."""
        all_time_metrics = self.metrics.get("all_time", {})

        exec_score, exec_breakdown = self.calculate_execution_score(
            all_time_metrics.get("execution", {})
        )
        comm_score, comm_breakdown = self.calculate_community_score(
            all_time_metrics.get("community", {})
        )

        # Use the most recent rolling window for backlog, as it's more relevant
        latest_backlog_metrics = (
            self.metrics.get("rolling_windows", {})
            .get("last_90_days", {})
            .get("backlog", {})
        )
        back_score, back_breakdown = self.calculate_backlog_score(
            latest_backlog_metrics
        )

        overall_score = (
            exec_score * self.weights["execution"]
            + comm_score * self.weights["community"]
            + back_score * self.weights["backlog"]
        )

        return {
            "overall_score": round(overall_score, 2),
            "sub_scores": {
                "execution": round(exec_score, 2),
                "community": round(comm_score, 2),
                "backlog": round(back_score, 2),
            },
            "breakdown": {
                "execution": exec_breakdown,
                "community": comm_breakdown,
                "backlog": back_breakdown,
            },
            "weights": self.weights,
        }
