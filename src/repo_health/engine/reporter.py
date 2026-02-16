# src/repo_health/engine/reporter.py

import json
import os
from typing import Any, Dict

from .metrics import MetricsCalculator


class ReportGenerator:
    """Generates reports from fetched data."""

    def __init__(self, data_dir: str = "data", output_file: str = "repo_health.json"):
        """
        Initialize the report generator.

        Args:
            data_dir: Directory containing the fetched raw JSON files.
            output_file: Path to save the generated report JSON.
        """
        self.prs_path = os.path.join(data_dir, "prs_raw.json")
        self.issues_path = os.path.join(data_dir, "issues_raw.json")
        self.output_file = output_file

    def generate(self) -> None:
        """Loads data, runs analysis, and saves the report."""
        # Load raw data
        with open(self.prs_path, "r", encoding="utf-8") as f:
            prs = json.load(f)
        with open(self.issues_path, "r", encoding="utf-8") as f:
            issues = json.load(f)

        # Initialize calculator and run analysis
        calculator = MetricsCalculator(prs, issues)
        metrics = calculator.analyze_all()

        # Save the final report
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)

        print(f"Analysis complete. Output written to {self.output_file}")
