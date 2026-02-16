"""Data normalization utilities for the repo health analyzer."""

import json
from datetime import datetime
from typing import Any, Dict, List

from ..config.settings import get_settings


class DataNormalizer:
    """Normalizes raw GitHub data for analysis."""

    @staticmethod
    def normalize_prs(prs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize pull request data.

        Args:
            prs: List of raw PR data from GitHub API.

        Returns:
            List of normalized PR data.
        """
        normalized = []

        for pr in prs:
            # Extract basic PR information
            normalized_pr = {
                "number": pr["number"],
                "title": pr["title"],
                "state": pr["state"],
                "created_at": pr["createdAt"],
                "merged_at": pr.get("mergedAt"),
                "author": pr["author"]["login"],
                "merged_by": pr.get("mergedBy", {}).get("login")
                if pr.get("mergedBy")
                else None,
            }

            # Extract review information
            reviews = []
            for review_edge in pr.get("reviews", {}).get("edges", []):
                review = review_edge["node"]
                reviews.append(
                    {
                        "author": review["author"]["login"],
                        "created_at": review["createdAt"],
                        "state": review["state"],
                    }
                )

            normalized_pr["reviews"] = reviews

            # Extract comment information
            comments = []
            for comment_edge in pr.get("comments", {}).get("edges", []):
                comment = comment_edge["node"]
                comments.append(
                    {
                        "author": comment["author"]["login"],
                        "created_at": comment["createdAt"],
                    }
                )

            normalized_pr["comments"] = comments

            # Calculate additional metrics
            if normalized_pr["merged_at"]:
                created_at = datetime.fromisoformat(
                    normalized_pr["created_at"].replace("Z", "+00:00")
                )
                merged_at = datetime.fromisoformat(
                    normalized_pr["merged_at"].replace("Z", "+00:00")
                )
                normalized_pr["merge_time_days"] = (merged_at - created_at).days

            # Calculate first response time
            if reviews:
                first_review = min(reviews, key=lambda r: r["created_at"])
                created_at = datetime.fromisoformat(
                    normalized_pr["created_at"].replace("Z", "+00:00")
                )
                first_response_at = datetime.fromisoformat(
                    first_review["created_at"].replace("Z", "+00:00")
                )
                normalized_pr["first_response_time_days"] = (
                    first_response_at - created_at
                ).days
            elif comments:
                first_comment = min(comments, key=lambda c: c["created_at"])
                created_at = datetime.fromisoformat(
                    normalized_pr["created_at"].replace("Z", "+00:00")
                )
                first_response_at = datetime.fromisoformat(
                    first_comment["created_at"].replace("Z", "+00:00")
                )
                normalized_pr["first_response_time_days"] = (
                    first_response_at - created_at
                ).days

            normalized.append(normalized_pr)

        return normalized

    @staticmethod
    def normalize_issues(issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize issue data.

        Args:
            issues: List of raw issue data from GitHub API.

        Returns:
            List of normalized issue data.
        """
        normalized = []

        for issue in issues:
            # Extract basic issue information
            normalized_issue = {
                "number": issue["number"],
                "title": issue["title"],
                "state": issue["state"],
                "created_at": issue["createdAt"],
                "closed_at": issue.get("closedAt"),
                "author": issue["author"]["login"],
            }

            # Extract comment information
            comments = []
            for comment_edge in issue.get("comments", {}).get("edges", []):
                comment = comment_edge["node"]
                comments.append(
                    {
                        "author": comment["author"]["login"],
                        "created_at": comment["createdAt"],
                    }
                )

            normalized_issue["comments"] = comments

            # Calculate additional metrics
            if normalized_issue["closed_at"]:
                created_at = datetime.fromisoformat(
                    normalized_issue["created_at"].replace("Z", "+00:00")
                )
                closed_at = datetime.fromisoformat(
                    normalized_issue["closed_at"].replace("Z", "+00:00")
                )
                normalized_issue["close_time_days"] = (closed_at - created_at).days

            # Calculate first response time
            if comments:
                first_comment = min(comments, key=lambda c: c["created_at"])
                created_at = datetime.fromisoformat(
                    normalized_issue["created_at"].replace("Z", "+00:00")
                )
                first_response_at = datetime.fromisoformat(
                    first_comment["created_at"].replace("Z", "+00:00")
                )
                normalized_issue["first_response_time_days"] = (
                    first_response_at - created_at
                ).days

            normalized.append(normalized_issue)

        return normalized

    @classmethod
    def normalize_and_save(
        cls,
        prs_path: str,
        issues_path: str,
        output_prs_path: str,
        output_issues_path: str,
    ) -> None:
        """Normalize raw PR and issue data and save to new files.

        Args:
            prs_path: Path to raw PR data file.
            issues_path: Path to raw issue data file.
            output_prs_path: Path to save normalized PR data.
            output_issues_path: Path to save normalized issue data.
        """
        # Load raw data
        with open(prs_path, "r") as f:
            prs = json.load(f)

        with open(issues_path, "r") as f:
            issues = json.load(f)

        # Normalize data
        normalized_prs = cls.normalize_prs(prs)
        normalized_issues = cls.normalize_issues(issues)

        # Save normalized data
        with open(output_prs_path, "w") as f:
            json.dump(normalized_prs, f, indent=2)

        with open(output_issues_path, "w") as f:
            json.dump(normalized_issues, f, indent=2)
