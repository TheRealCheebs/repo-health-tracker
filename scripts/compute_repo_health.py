import json
import statistics
from datetime import datetime, timedelta

# -------------------------
# Load JSON inputs
# -------------------------
with open("repo_health.json") as f:
    repo_health = json.load(f)

with open("open_issues.json") as f:
    open_issues = json.load(f)

with open("open_pr.json") as f:
    open_prs = json.load(f)


# -------------------------
# Helper functions
# -------------------------
def days_old(date_str):
    """Calculate days old from ISO format date string."""
    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    return (datetime.utcnow() - dt).days


def median_age(items):
    ages = [days_old(i["created_at"]) for i in items if "created_at" in i]
    return int(statistics.median(ages)) if ages else 0


def filter_ids_by_age(items, min_days):
    return [
        i["id"]
        for i in items
        if "created_at" in i and days_old(i["created_at"]) >= min_days
    ]


# -------------------------
# Calculate metrics
# -------------------------
backlog_snapshot = {
    "open_prs": len(open_prs),
    "open_issues": len(open_issues),
    "prs_over_365_days": len(filter_ids_by_age(open_prs, 365)),
    "issues_over_365_days": len(filter_ids_by_age(open_issues, 365)),
    "issues_over_730_days": len(filter_ids_by_age(open_issues, 730)),
    "median_pr_age_days_est": median_age(open_prs),
    "median_issue_age_days_est": median_age(open_issues),
}

# Risk flags
risk_flags = []

if backlog_snapshot["prs_over_365_days"] / max(backlog_snapshot["open_prs"], 1) > 0.35:
    risk_flags.append(
        f"{int(100 * backlog_snapshot['prs_over_365_days'] / backlog_snapshot['open_prs'])}% of open PRs are over 1 year old"
    )

if (
    backlog_snapshot["issues_over_365_days"] / max(backlog_snapshot["open_issues"], 1)
    > 0.6
):
    risk_flags.append(
        f"{int(100 * backlog_snapshot['issues_over_365_days'] / backlog_snapshot['open_issues'])}% of open issues are over 1 year old"
    )

if backlog_snapshot["issues_over_730_days"] > 0:
    risk_flags.append(
        f"{int(100 * backlog_snapshot['issues_over_730_days'] / backlog_snapshot['open_issues'])}% of open issues are over 2 years old"
    )

# Add generic backlog warning
risk_flags.append(
    "High likelihood that issue tracker reflects historical intent rather than active roadmap"
)

# Stalled actions
stalled_actions = {
    "archive_prs_over_365_days": filter_ids_by_age(open_prs, 365),
    "close_issues_over_730_days": filter_ids_by_age(open_issues, 730),
    "decision_required_prs_180_365_days": filter_ids_by_age(open_prs, 180),
    "decision_required_issues_180_365_days": filter_ids_by_age(open_issues, 180),
}

# -------------------------
# Combine final JSON
# -------------------------
final_report = {
    "strategy_score": repo_health.get("strategy_score", 0),
    "execution_score": repo_health.get("execution_score", 0),
    "community_score": repo_health.get("community_score", 0),
    "lowest_lens": repo_health.get("lowest_lens", ""),
    "trends": repo_health.get("trends", {}),
    "backlog_snapshot": backlog_snapshot,
    "risk_flags": risk_flags,
    "stalled_actions": stalled_actions,
}

# -------------------------
# Save final JSON
# -------------------------
with open("final_report.json", "w") as f:
    json.dump(final_report, f, indent=2)

print("Final report saved to final_report.json")
