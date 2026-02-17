# src/repo_health/cli/score.py

"""CLI command for scoring repository health."""

import json
import os
from typing import Any, Dict

import click
from rich.console import Console
from rich.table import Table

from ..engine.scorer import RepoHealthScorer

console = Console()


@click.command()
@click.option(
    "--metrics-file",
    default="repo_health.json",
    help="Path to the generated metrics JSON file.",
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--save-to-metrics",
    is_flag=True,
    help="If set, saves the score back into the metrics file for historical tracking.",
)
def score_command(metrics_file: str, save_to_metrics: bool):
    """Calculates and displays a deterministic repo health score."""
    with open(metrics_file, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    scorer = RepoHealthScorer(metrics)
    score_report = scorer.calculate_overall_score()

    table = Table(
        title="Repo Health Score", show_header=True, header_style="bold magenta"
    )
    table.add_column("Category", style="cyan", width=20)
    table.add_column("Score", style="green", width=10)
    table.add_column("Weight", style="dim", width=10)

    for category, score in score_report["sub_scores"].items():
        weight = score_report["weights"][category]
        table.add_row(
            category.replace("_", " ").title(), f"{score}/100", f"{weight * 100}%"
        )

    table.add_row("---", "---", "---")
    table.add_row(
        "Overall Score", f"[bold]{score_report['overall_score']}/100[/bold]", "100%"
    )

    console.print(table)

    if save_to_metrics:
        from datetime import datetime, timezone

        metrics["score"] = score_report
        metrics["score_calculated_at"] = datetime.now(timezone.utc).isoformat()

        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)

        console.print(f"\n[green]Score saved to {metrics_file}[/green]")
