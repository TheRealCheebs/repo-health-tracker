#!/usr/bin/env python3

"""
Analyze raw PRs and Issues JSON to propose labeling for backlog cleanup.
This version uses a rule-based engine and an external JSON taxonomy file.
"""

import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple

import click

# --- IMPORTANT ---
# Add the 'src' directory to the Python path to import our project's modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from repo_health.utils.helpers import parse_datetime


def load_taxonomy(file_path: str) -> Dict[str, Any]:
    """Loads the label taxonomy from a JSON file."""
    if not os.path.exists(file_path):
        click.echo(f"Error: Taxonomy file not found at {file_path}", err=True)
        raise FileNotFoundError(f"Taxonomy file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


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
@click.option(
    "--taxonomy-file",
    default="label_taxonomy.json",
    help="Path to the JSON file containing the label taxonomy.",
    type=click.Path(exists=True, dir_okay=False),
)
def main(data_dir: str, output: str, taxonomy_file: str):
    """Generates a cleanup proposal for open PRs and issues."""
    try:
        taxonomy = load_taxonomy(taxonomy_file)
    except FileNotFoundError:
        return

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

    proposal = generate_proposals(prs, issues, taxonomy)

    os.makedirs(os.path.dirname(output), exist_ok=True)

    with open(output, "w", encoding="utf-8") as f:
        json.dump(proposal, f, indent=2)

    click.echo(f"Cleanup proposal saved to {output}")
    click.echo(
        f"{len(proposal['open_prs'])} open PRs, {len(proposal['open_issues'])} open Issues analyzed."
    )


def infer_labels(
    item: Dict[str, Any], taxonomy: Dict[str, Any]
) -> Tuple[set[str], list[str]]:
    """Infer a set of labels for an item based on its properties and the taxonomy."""
    suggested_labels = set()
    reasoning = []

    keyword_map = taxonomy.get("keyword_map", {})
    status_rules = taxonomy.get("status_rules", {})

    # 1. Infer from title keywords
    title = item.get("title", "").lower()
    for label, keywords in keyword_map.items():
        for keyword in keywords:
            if keyword in title:
                suggested_labels.add(label)
                reasoning.append(f"Title contains keyword '{keyword}' -> {label}")

    # 2. Infer from state and age
    created_at = parse_datetime(item.get("createdAt"))
    if not created_at:
        return suggested_labels, reasoning

    age_days = (datetime.now(timezone.utc) - created_at).days

    # Check for draft status
    if item.get("isDraft", False):
        draft_label = status_rules.get("draft_label")
        if draft_label:
            suggested_labels.add(draft_label)
            reasoning.append("Item is a draft PR -> status:draft")

    # Check for triage status if it's an open item (including drafts)
    if item.get("state") == "OPEN":
        needs_triage_label = status_rules.get("needs_triage_label")
        if needs_triage_label:
            suggested_labels.add(needs_triage_label)
            reasoning.append(f"Item state is OPEN -> {needs_triage_label}")

        # Check for age/stale status (this is now independent of the draft check)
        stale_threshold = status_rules.get("stale_threshold_days")
        aging_threshold = status_rules.get("aging_threshold_days")

        if stale_threshold and age_days > stale_threshold:
            # If it's stale, mark it as stale and do not also mark it as aging
            suggested_labels.add("status:stale")
            reasoning.append(
                f"Item is {age_days} days old (> {stale_threshold}) -> status:stale"
            )
        elif aging_threshold and age_days > aging_threshold:
            # It's not stale, but it is aging
            suggested_labels.add("status:aging")
            reasoning.append(
                f"Item is {age_days} days old (> {aging_threshold}) -> status:aging"
            )

    # 3. Ensure a scope is assigned
    has_scope = any(label.startswith("scope:") for label in suggested_labels)
    if not has_scope:
        tbd_label = status_rules.get("tbd_label")
        if tbd_label:
            suggested_labels.add(tbd_label)
            reasoning.append("No scope could be inferred -> {tbd_label}")

    return suggested_labels, reasoning


def generate_proposals(
    prs: List[Dict[str, Any]], issues: List[Dict[str, Any]], taxonomy: Dict[str, Any]
) -> Dict[str, Any]:
    """Generates the cleanup proposal dictionary."""
    proposals = {"open_prs": [], "open_issues": []}

    # Process PRs separately
    for item in prs:
        if item.get("state") not in ["OPEN", "DRAFT"]:
            continue

        author_obj = item.get("author", {})
        author_login = author_obj.get("login", "unknown")

        created_at = parse_datetime(item.get("createdAt"))
        age_days = (
            (datetime.now(timezone.utc) - created_at).days if created_at else None
        )

        suggested_labels, reasoning = infer_labels(item, taxonomy)

        proposals["open_prs"].append(
            {
                "number": item.get("number"),
                "title": item.get("title"),
                "author": author_login,
                "age_days": age_days,
                "current_labels": item.get("labels", []),
                "suggested_labels": sorted(list(suggested_labels)),
                "reasoning": reasoning,
            }
        )

    # Process Issues separately
    for item in issues:
        if item.get("state") not in ["OPEN", "DRAFT"]:
            continue

        author_obj = item.get("author", {})
        author_login = author_obj.get("login", "unknown")

        created_at = parse_datetime(item.get("createdAt"))
        age_days = (
            (datetime.now(timezone.utc) - created_at).days if created_at else None
        )

        suggested_labels, reasoning = infer_labels(item, taxonomy)

        proposals["open_issues"].append(
            {
                "number": item.get("number"),
                "title": item.get("title"),
                "author": author_login,
                "age_days": age_days,
                "current_labels": item.get("labels", []),
                "suggested_labels": sorted(list(suggested_labels)),
                "reasoning": reasoning,
            }
        )

    return proposals


if __name__ == "__main__":
    main()
