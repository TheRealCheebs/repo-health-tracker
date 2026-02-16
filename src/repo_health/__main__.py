"""Main entry point for the repo-health CLI."""

import click
from rich.console import Console

from .cli.fetch import fetch_command
from .cli.generate import generate_command

console = Console()


@click.group()
@click.version_option()
def main():
    """Repo Health Analyzer - Analyze GitHub repository health."""
    pass


main.add_command(fetch_command, name="fetch")
main.add_command(generate_command, name="generate")


if __name__ == "__main__":
    main()
