"""CLI command for generating reports from fetched data."""

import click
from rich.console import Console

from ..engine.reporter import ReportGenerator
from ..config.settings import get_settings

console = Console()


@click.command()
@click.option(
    "--data-dir",
    default="data",
    help="Directory containing the fetched data",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
)
@click.option(
    "--output",
    default="repo_health.json",
    help="Output file for the generated report",
    type=click.Path(dir_okay=False),
)
def generate_command(data_dir, output):
    """Generate a health report from fetched data."""
    settings = get_settings()
    generator = ReportGenerator(
        data_dir=data_dir,
        output_file=output,
    )

    with console.status("[bold green]Generating report..."):
        generator.generate()

    console.print(f"[green]Repo health metrics saved to {output}[/green]")
