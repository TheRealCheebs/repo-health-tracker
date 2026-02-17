# src/repo_health/cli/summary.py

"""CLI command for generating a lean summary report for LLM input."""

import json
import os
import click
from rich.console import Console

from ..engine.final_reporter import FinalReporter

console = Console()


@click.command()
@click.option(
    "--data-dir",
    default="data",
    help="Directory containing the fetched raw JSON files (e.g., 'data/')",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
)
@click.option(
    "--output",
    default="summary_report.json",
    help="Path for the lean summary report JSON file.",
    type=click.Path(dir_okay=False),
)
def summary_command(data_dir: str, output: str):
    """Generates a lean summary report with scores, risk flags, and stalled actions."""
    reporter = FinalReporter(data_dir)
    summary_report = reporter.generate_summary_report()

    with open(output, "w", encoding="utf-8") as f:
        json.dump(summary_report, f, indent=2)

    console.print(f"[green]Lean summary report saved to {output}[/green]")
    console.print(
        f"[bold]Overall Score: {summary_report['score']['overall_score']}/100[/bold]"
    )
    if summary_report["risk_flags"]:
        console.print(
            f"[yellow]Risk Flags Detected: {len(summary_report['risk_flags'])}[/yellow]"
        )
