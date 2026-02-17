#!/usr/bin/env python3

"""
Analyze raw PRs and Issues JSON to propose labeling for backlog cleanup.
This version can output to JSON or a Markdown table.
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
from repo_health.config.settings import get_settings


def load_taxonomy(file_path: str) -> Dict[str, Any]:
    """Loads the label taxonomy from a JSON file."""
    if not os.path.exists(file_path):
        click.echo(f"Error: Taxonomy file not found at {file_path}", err=True)
        raise FileNotFoundError(f"Taxonomy file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(proposal: Dict[str, Any], output_path: str):
    """Writes the proposal as a JSON file."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(proposal, f, indent=2)


def write_markdown(proposal: Dict[str, Any], output_path: str, owner: str, repo: str):
    """Writes the proposal as a Markdown file with tables."""
    base_url = f"https://github.com/{owner}/{repo}"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# Cleanup Proposal for {owner}/{repo}\n\n")
        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # Helper to create a table from a list of items
        def create_table(items: List[Dict[str, Any]]):
            if not items:
                return "No items to display.\n"

            header = (
                "| # | Title | Author | Age | Current Labels | Suggested Labels |\n"
            )
            header += "|---|---|---|---|---|---|\n"

            rows = ""
            for item in items:
                num = item.get("number")
                title = item.get("title", "").replace("|", "\\|")  # Escape pipe chars
                author = item.get("author", "")
                age = f"{item.get('age_days', 'N/A')} days"
                current = ", ".join(item.get("current_labels", [])).replace("|", "\\|")
                suggested = ", ".join(item.get("suggested_labels", [])).replace(
                    "|", "\\|"
                )

                rows += f"| [{num}]({base_url}/pull/{num}) | {title} | {author} | {age} | {current} | {suggested} |\n"

            return header + rows + "\n"

        # Write PRs table
        f.write("## Pull Requests\n\n")
        f.write(create_table(proposal.get("open_prs", [])))

        # Write Issues table
        f.write("## Issues\n\n")

        # Note: The URL for issues is different from PRs
        def create_issue_table(items: List[Dict[str, Any]]):
            if not items:
                return "No items to display.\n"

            header = (
                "| # | Title | Author | Age | Current Labels | Suggested Labels |\n"
            )
            header += "|---|---|---|---|---|---|\n"

            rows = ""
            for item in items:
                num = item.get("number")
                title = item.get("title", "").replace("|", "\\|")
                author = item.get("author", "")
                age = f"{item.get('age_days', 'N/A')} days"
                current = ", ".join(item.get("current_labels", [])).replace("|", "\\|")
                suggested = ", ".join(item.get("suggested_labels", [])).replace(
                    "|", "\\|"
                )

                rows += f"| [{num}]({base_url}/issues/{num}) | {title} | {author} | {age} | {current} | {suggested} |\n"

            return header + rows + "\n"

        f.write(create_issue_table(proposal.get("open_issues", [])))


@click.command()
@click.option(
    "--data-dir",
    default="data",
    help="Directory containing the fetched raw JSON files (e.g., 'data/')",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
)
@click.option(
    "--output",
    default="data/cleanup_proposal",
    help="Base path for the output file. The extension (.json or .md) will be added automatically.",
    type=click.Path(dir_okay=False),
)
@click.option(
    "--taxonomy-file",
    default="label_taxonomy.json",
    help="Path to the JSON file containing the label taxonomy.",
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--output-format",
    default="json",
    type=click.Choice(["json", "markdown"], case_sensitive=False),
    help="The format for the output file.",
)
def main(data_dir: str, output: str, taxonomy_file: str, output_format: str):
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

    # Determine final output path and writer
    if output_format == "markdown":
        output_path = f"{output}.md"
        settings = get_settings()  # Get owner/repo for links
        write_markdown(
            proposal, output_path, settings.github_owner, settings.github_repo
        )
    else:  # Default to JSON
        output_path = f"{output}.json"
        write_json(proposal, output_path)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    click.echo(f"Cleanup proposal saved to {output_path}")
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

    title = item.get("title", "").lower()
    for label, keywords in keyword_map.items():
        for keyword in keywords:
            if keyword in title:
                suggested_labels.add(label)
                reasoning.append(f"Title contains keyword '{keyword}' -> {label}")

    created_at = parse_datetime(item.get("createdAt"))
    if not created_at:
        return suggested_labels, reasoning

    age_days = (datetime.now(timezone.utc) - created_at).days

    if item.get("isDraft", False):
        draft_label = status_rules.get("draft_label")
        if draft_label:
            suggested_labels.add(draft_label)
            reasoning.append("Item is a draft PR -> status:draft")

    if item.get("state") == "OPEN":
        needs_triage_label = status_rules.get("needs_triage_label")
        if needs_triage_label:
            suggested_labels.add(needs_triage_label)
            reasoning.append(f"Item state is OPEN -> {needs_triage_label}")

        stale_threshold = status_rules.get("stale_threshold_days")
        aging_threshold = status_rules.get("aging_threshold_days")

        if stale_threshold and age_days > stale_threshold:
            suggested_labels.add("status:stale")
            reasoning.append(
                f"Item is {age_days} days old (> {stale_threshold}) -> status:stale"
            )
        elif aging_threshold and age_days > aging_threshold:
            suggested_labels.add("status:aging")
            reasoning.append(
                f"Item is {age_days} days old (> {aging_threshold}) -> status:aging"
            )

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
