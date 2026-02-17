"""Main entry point for the repo-health CLI."""

import click
from rich.console import Console

from .cli.fetch import fetch_command
from .cli.generate import generate_command
from .cli.score import score_command
from .cli.report import report_command
from .cli.summary import summary_command

console = Console()


@click.group()
@click.version_option()
def main():
    """Repo Health Analyzer - Analyze GitHub repository health."""
    pass


main.add_command(fetch_command, name="fetch")
main.add_command(generate_command, name="generate")
main.add_command(score_command, name="score")
main.add_command(report_command, name="report")
main.add_command(summary_command, name="summary")


if __name__ == "__main__":
    main()
