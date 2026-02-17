# src/repo_health/cli/report.py

"""CLI command for generating the final comprehensive report."""

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
    default="final_report.json",
    help="Path for the final report JSON file.",
    type=click.Path(dir_okay=False),
)
def report_command(data_dir: str, output: str):
    """Generates a comprehensive final report with metrics, scores, and risk analysis."""
    reporter = FinalReporter(data_dir)
    final_report = reporter.generate()

    with open(output, "w", encoding="utf-8") as f:
        json.dump(final_report, f, indent=2)

    console.print(f"[green]Final report saved to {output}[/green]")
    console.print(
        f"[bold]Overall Score: {final_report['metrics']['score']['overall_score']}/100[/bold]"
    )
    if final_report["risk_flags"]:
        console.print(
            f"[yellow]Risk Flags Detected: {len(final_report['risk_flags'])}[/yellow]"
        )
