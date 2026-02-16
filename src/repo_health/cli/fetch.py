"""CLI command for fetching data from GitHub."""

import click
from rich.console import Console

from ..data.fetcher import GitHubDataFetcher
from ..config.settings import get_settings

console = Console()


@click.command()
@click.option(
    "--output-dir",
    default="data",
    help="Directory to save the fetched data",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
)
def fetch_command(output_dir):
    """Fetch data from GitHub API."""
    settings = get_settings()
    fetcher = GitHubDataFetcher(
        token=settings.github_token,
        owner=settings.github_owner,
        repo=settings.github_repo,
        start_date=settings.start_date,
        output_dir=output_dir,
    )

    with console.status("[bold green]Fetching data from GitHub..."):
        prs_count, issues_count = fetcher.fetch_all()

    console.print(f"[green]Saved {prs_count} PRs and {issues_count} issues.[/green]")
    console.print("[green]Snapshot overwrite complete.[/green]")
