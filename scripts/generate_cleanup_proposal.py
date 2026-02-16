#!/usr/bin/env python3

"""
Analyze raw PRs and Issues JSON to propose labeling for backlog cleanup.
Focuses on open items and uses past labels to suggest labels for stale tickets.
"""

import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Dict, Any, List

import click

# --- IMPORTANT ---
# Add the 'src' directory to the Python path to import our project's modules
# This is necessary for scripts that live outside the 'src' directory.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from repo_health.utils.helpers import parse_datetime


@click.command()
@click.option(
    "--data-dir",
    default="data",
    help="Directory containing the fetched raw JSON files (e.g., 'data/')",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
)
@click.option(
    "--output",
    default="data/cleanup_proposal.json",
    help="Output file for the cleanup proposal",
    type=click.Path(dir_okay=False),
)
def main(data_dir: str, output: str):
    """Generates a cleanup proposal for open PRs and issues."""
    prs_path = os.path.join(data_dir, "prs_raw.json")
    issues_path = os.path.join(data_dir, "issues_raw.json")

    if not os.path.exists(prs_path) or not os.path.exists(issues_path):
        click.echo(
            f"Raw PR or Issue JSON not found at {prs_path} / {issues_path}", err=True
        )
        return

    with open(prs_path, "r", encoding="utf-8") as f:
        prs = json.load(f)
    with open(issues_path, "r", encoding="utf-8") as f:
        issues = json.load(f)

    proposal = generate_proposals(prs, issues)

    # Ensure the output directory exists
    os.makedirs(os.path.dirname(output), exist_ok=True)

    with open(output, "w", encoding="utf-8") as f:
        json.dump(proposal, f, indent=2)

    click.echo(f"Cleanup proposal saved to {output}")
    click.echo(
        f"{len(proposal['open_prs'])} open PRs, {len(proposal['open_issues'])} open Issues analyzed."
    )


def suggest_labels(item: Dict[str, Any], past_label_counts: defaultdict) -> List[str]:
    """Suggest labels based on previous label usage."""
    # The new data structure has labels as a list of strings, e.g., ["bug", "enhancement"]
    # If it has labels already, keep them.
    if item.get("labels"):
        return item["labels"]

    # Otherwise, suggest the top label used historically for the same state.
    state = item.get("state", "OPEN").lower()
    most_common = past_label_counts[state].most_common(1)
    return [most_common[0][0]] if most_common else []


def generate_proposals(
    prs: List[Dict[str, Any]], issues: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Generates the cleanup proposal dictionary."""
    # Build past label usage
    past_label_counts = defaultdict(Counter)
    for collection in [prs, issues]:
        for item in collection:
            state = item.get("state", "OPEN").lower()
            # Labels are now a simple list of strings.
            labels = item.get("labels") or []
            for label_name in labels:
                past_label_counts[state][label_name] += 1

    proposals = {"open_prs": [], "open_issues": []}
    now = datetime.now(timezone.utc)

    for collection, key in [(prs, "open_prs"), (issues, "open_issues")]:
        for item in collection:
            if item.get("state") != "OPEN":
                continue

            created_at = parse_datetime(item.get("createdAt"))
            age_days = (now - created_at).days if created_at else None

            # Author is now an object, so we need to get the login from it.
            author_obj = item.get("author", {})
            author_login = author_obj.get("login", "unknown")

            proposals[key].append(
                {
                    "number": item.get("number"),
                    "title": item.get("title"),
                    "author": author_login,
                    "age_days": age_days,
                    "current_labels": item.get("labels", []),
                    "suggested_labels": suggest_labels(item, past_label_counts),
                }
            )

    return proposals


if __name__ == "__main__":
    main()
