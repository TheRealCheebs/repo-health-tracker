# AGENTS.md

This document provides a high-level guide for AI agents to understand, interact with, and contribute to the Repo Health Analyzer project.

## Project Purpose

The Repo Health Analyzer is a command-line tool that fetches historical data from a GitHub repository, calculates deterministic health metrics, and generates reports to track project trends over time. It is designed for automated, weekly analysis.

## Core Architecture

The project is structured as a modern Python package using the `src/` layout.

* **`src/repo_health/cli/`**: Contains `click`-based commands (`fetch`, `generate`, `score`, `report`, `summary`). Each file is a self-contained command.
* **`src/repo_health/engine/`**: Contains the core analysis logic.
  * `fetcher.py`: Handles GitHub GraphQL API interaction and data normalization.
  * `metrics.py`: Calculates all time-series, rolling, and all-time metrics.
  * `scorer.py`: Calculates a deterministic 0-100 health score based on configurable targets.
  * `final_reporter.py`: Orchestrates the creation of a comprehensive report.
* **`src/repo_health/config/`**: Manages configuration and environment variables using `pydantic-settings`.
* **`src/repo_health/utils/`**: Contains shared helper functions.
* **`scripts/`**: Contains standalone Python scripts for auxiliary tasks like LLM report generation and backlog cleanup proposals.

## Key Workflows

1. **Data Fetching**: `uv run repo-health fetch` is the only command that contacts the GitHub API. It saves raw data to `data/prs_raw.json` and `data/issues_raw.json`.
2. **Analysis & Scoring**:
    * `uv run repo-health generate` creates `repo_health.json` with all historical metrics.
    * `uv run repo-health score` calculates and displays the 0-100 health score.
    * `uv run repo-health report` creates a massive `final_report.json` with all data, scores, and risk analysis.
    * `uv run repo-health summary` creates a lean `summary_report.json` with only the essential data needed for LLM input. **This is the preferred input for LLMs.**
3. **LLM Report Generation**: The `scripts/generate_routestr_report.py` script reads the lean summary, uses a Jinja2 template (`report_prompt.md`) to format a prompt, and sends it to the `routestr` API via the standard `openai` library.

## Important Files

* `pyproject.toml`: The single source of truth for dependencies, metadata, and project configuration.
* `src/repo_health/data/fetcher.py`: Critical for data correctness. Normalizes raw GraphQL data into a clean, predictable format.
* `src/repo_health/engine/metrics.py`: The heart of the analysis. All historical calculations happen here.
* `src/repo_health/engine/scorer.py`: Defines the deterministic scoring logic. Targets and weights are configured here.
* `scripts/generate_routestr_report.py`: The bridge between our data and the LLM.

## Design Philosophy

* **Deterministic**: All analysis is based on math and logic, not on probabilistic models. This ensures consistency and allows for reliable trend tracking.
* **Decoupled**: The core analysis tool is separate from the LLM narrative generation. This keeps the analysis tool lean and allows flexibility in choosing LLM providers.
* **CLI-First**: The project is designed to be used from the command line.
* **Efficiency**: The `summary` command is designed to minimize token usage and cost when interfacing with LLMs.

## How to Contribute (For AI Agents)

* **Code Style**: Adhere to the style defined by `black` and `isort`. Run `uv run black src/ tests/` and `uv run isort src/ tests/` before suggesting code.
* **Testing**: When fixing a bug or adding a feature, write a corresponding test in the `tests/` directory. Use `pytest` and mock external API calls.
* **Dependencies**: Add new dependencies to the `[dependency-groups]` table in `pyproject.toml`.
* **Error Handling**: Prioritize clear error messages. The `fetcher.py` is a good example of handling API errors gracefully.
* **Configuration**: Use `pydantic-settings` for any new configuration, following the pattern in `src/repo_health/config/settings.py`.
* **CLI Commands**: New commands should be added as a new file in `src/repo_health/cli/` and registered in `src/repo_health/__main__.py`. Use `click` for the interface.
