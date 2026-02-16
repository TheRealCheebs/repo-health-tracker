# src/repo_health/data/fetcher.py

"""GraphQL data fetcher for GitHub repository data."""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Tuple

import requests
from rich.console import Console

from ..config.settings import get_settings

console = Console()


class GitHubDataFetcher:
    """Fetches data from GitHub GraphQL API and normalizes it."""

    def __init__(
        self,
        token: str,
        owner: str,
        repo: str,
        start_date: datetime,
        output_dir: str = "data",
    ):
        """Initialize the fetcher."""
        self.token = token
        self.owner = owner
        self.repo = repo
        self.start_date = start_date
        self.output_dir = output_dir
        self.api_url = "https://api.github.com/graphql"
        self.headers = {
            "Authorization": f"bearer {token}",
            "Accept": "application/vnd.github.v4.idl",
        }

    def _execute_query(self, query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a GraphQL query and handle potential errors."""
        response = requests.post(
            self.api_url,
            json={"query": query, "variables": variables},
            headers=self.headers,
        )
        response.raise_for_status()
        response_json = response.json()

        if "errors" in response_json:
            error_messages = [error["message"] for error in response_json["errors"]]
            raise ValueError(
                f"GraphQL API returned errors: {', '.join(error_messages)}"
            )
        if "data" not in response_json:
            raise ValueError(
                "Unexpected response from GraphQL API: 'data' key is missing."
            )
        return response_json

    def _get_author_info(self, author_obj) -> Dict[str, Any]:
        """Helper to safely extract author information."""
        if not author_obj:
            return {"login": "ghost", "id": None}

        # The object will always have a login from the 'Actor' interface
        info = {"login": author_obj.get("login", "ghost")}

        # The databaseId will only exist if the author is a 'User'
        # due to our `... on User` fragment
        info["id"] = author_obj.get("databaseId")

        return info

    def fetch_prs(self) -> List[Dict[str, Any]]:
        """Fetch pull requests and return a normalized list."""
        normalized_prs = []
        cursor = None
        has_more = True

        while has_more:
            query = """
            query($owner: String!, $repo: String!, $cursor: String) {
              repository(owner: $owner, name: $repo) {
                pullRequests(first: 100, after: $cursor, orderBy: {field: CREATED_AT, direction: DESC}) {
                  edges {
                    node {
                      number
                      title
                      state
                      createdAt
                      mergedAt
                      mergedBy { login, ... on User { databaseId } }
                      author { login, ... on User { databaseId } }
                      labels(first: 20) {
                        edges {
                          node {
                            name
                          }
                        }
                      }
                      reviews(first: 100) {
                        edges {
                          node {
                            author { login, ... on User { databaseId } }
                            submittedAt
                            state
                          }
                        }
                      }
                      comments(first: 100) {
                        edges {
                          node {
                            author { login, ... on User { databaseId } }
                            createdAt
                          }
                        }
                      }
                    }
                    cursor
                  }
                  pageInfo { hasNextPage }
                }
              }
            }
            """

            variables = {"owner": self.owner, "repo": self.repo, "cursor": cursor}
            response = self._execute_query(query, variables)
            pr_data = response["data"]["repository"]["pullRequests"]

            for edge in pr_data["edges"]:
                raw_pr = edge["node"]

                normalized_pr = {
                    "number": raw_pr["number"],
                    "title": raw_pr["title"],
                    "state": raw_pr["state"],
                    "createdAt": raw_pr["createdAt"],
                    "mergedAt": raw_pr.get("mergedAt"),
                    "author": self._get_author_info(raw_pr.get("author")),
                    "mergedBy": self._get_author_info(raw_pr.get("mergedBy")),
                }

                normalized_pr["labels"] = [
                    label["node"]["name"]
                    for label in raw_pr.get("labels", {}).get("edges", [])
                ]

                normalized_pr["reviews"] = [
                    {
                        "author": self._get_author_info(review["node"].get("author")),
                        "submittedAt": review["node"]["submittedAt"],
                        "state": review["node"]["state"],
                    }
                    for review in raw_pr.get("reviews", {}).get("edges", [])
                    if review["node"].get("author")
                ]

                normalized_pr["comments"] = [
                    {
                        "author": self._get_author_info(comment["node"].get("author")),
                        "createdAt": comment["node"]["createdAt"],
                    }
                    for comment in raw_pr.get("comments", {}).get("edges", [])
                    if comment["node"].get("author")
                ]

                normalized_prs.append(normalized_pr)
                cursor = edge["cursor"]

            has_more = pr_data["pageInfo"]["hasNextPage"]

            if (
                normalized_prs
                and datetime.fromisoformat(
                    normalized_prs[-1]["createdAt"].replace("Z", "+00:00")
                )
                < self.start_date
            ):
                normalized_prs = [
                    pr
                    for pr in normalized_prs
                    if datetime.fromisoformat(pr["createdAt"].replace("Z", "+00:00"))
                    >= self.start_date
                ]
                break

        return normalized_prs

    def fetch_issues(self) -> List[Dict[str, Any]]:
        """Fetch issues and return a normalized list."""
        normalized_issues = []
        cursor = None
        has_more = True

        while has_more:
            query = """
            query($owner: String!, $repo: String!, $cursor: String) {
              repository(owner: $owner, name: $repo) {
                issues(first: 100, after: $cursor, orderBy: {field: CREATED_AT, direction: DESC}) {
                  edges {
                    node {
                      number
                      title
                      state
                      createdAt
                      closedAt
                      author { login, ... on User { databaseId } }
                      labels(first: 20) {
                        edges {
                          node {
                            name
                          }
                        }
                      }
                      comments(first: 100) {
                        edges {
                          node {
                            author { login, ... on User { databaseId } }
                            createdAt
                          }
                        }
                      }
                    }
                    cursor
                  }
                  pageInfo { hasNextPage }
                }
              }
            }
            """

            variables = {"owner": self.owner, "repo": self.repo, "cursor": cursor}
            response = self._execute_query(query, variables)
            issue_data = response["data"]["repository"]["issues"]

            for edge in issue_data["edges"]:
                raw_issue = edge["node"]

                normalized_issue = {
                    "number": raw_issue["number"],
                    "title": raw_issue["title"],
                    "state": raw_issue["state"],
                    "createdAt": raw_issue["createdAt"],
                    "closedAt": raw_issue.get("closedAt"),
                    "author": self._get_author_info(raw_issue.get("author")),
                }

                normalized_issue["labels"] = [
                    label["node"]["name"]
                    for label in raw_issue.get("labels", {}).get("edges", [])
                ]

                normalized_issue["comments"] = [
                    {
                        "author": self._get_author_info(comment["node"].get("author")),
                        "createdAt": comment["node"]["createdAt"],
                    }
                    for comment in raw_issue.get("comments", {}).get("edges", [])
                    if comment["node"].get("author")
                ]

                normalized_issues.append(normalized_issue)
                cursor = edge["cursor"]

            has_more = issue_data["pageInfo"]["hasNextPage"]

            if (
                normalized_issues
                and datetime.fromisoformat(
                    normalized_issues[-1]["createdAt"].replace("Z", "+00:00")
                )
                < self.start_date
            ):
                normalized_issues = [
                    issue
                    for issue in normalized_issues
                    if datetime.fromisoformat(issue["createdAt"].replace("Z", "+00:00"))
                    >= self.start_date
                ]
                break

        return normalized_issues

    def fetch_all(self) -> Tuple[int, int]:
        """Fetch all PRs and issues, and save the normalized data."""
        prs = self.fetch_prs()
        issues = self.fetch_issues()

        prs_path = os.path.join(self.output_dir, "prs_raw.json")
        with open(prs_path, "w", encoding="utf-8") as f:
            json.dump(prs, f, indent=2)

        issues_path = os.path.join(self.output_dir, "issues_raw.json")
        with open(issues_path, "w", encoding="utf-8") as f:
            json.dump(issues, f, indent=2)

        return len(prs), len(issues)
