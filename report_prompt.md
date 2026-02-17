You are analyzing an open-source repository from the perspective of three lenses:

1. strategy_value (long-term impact and alignment with goals)
2. execution_systems (how efficiently PRs and issues are processed)
3. community_sustainability (health and activity of contributors/community).

I will provide you with a JSON report containing:

- metrics (including scores for execution, community, and backlog)
- backlog_snapshot (open PRs/issues, PRs/issues older than 365 or 730 days, median age estimates)
- risk_flags
- stalled_actions (lists of PRs/issues needing attention)

Your task is to **produce a Markdown report** with the following sections:

1. **Repository Health Overview**
   - Include the three lens scores, the lowest scoring lens, and the trends.
   - Include a concise snapshot of open PRs/issues, aged items, and median ages.

2. **Risk Flags**
   - List each risk flag clearly as bullet points.

3. **Stalled Actions**
   - List PRs/issues needing attention in bullet or numeric lists as provided.

4. **Structural Diagnosis** *(generate this based on the report, not provided directly)*
   - Identify the primary constraint affecting repository health.
   - Identify a secondary constraint if present.
   - Describe any system pattern contributing to backlog issues.
   - Give a short execution signal: what’s actually working versus what is hidden by backlog or risk.

5. **Recommendation** *(generate actionable steps based on the report)*
   - Suggest concrete actions to address the primary and secondary constraints.
   - Provide measurable goals or target outcomes if possible (e.g., % backlog reduction, median age reduction).

6. **Weekly Narrative**
   - Summarize the overall repository health in 3–5 paragraphs.
   - Reference the quantitative metrics from the report.
   - Explain structural diagnosis and recommendations in plain language.
   - Provide insight on strategy, execution, and community lenses.

Formatting rules:

- Use Markdown headers (`##`, `###`) for sections.
- Keep all lists as bullet points where applicable.
- Do **not** output any raw JSON.
- Ensure that all numbers, percentages, and trends match the provided JSON exactly.
- Use the report to **derive** structural diagnosis and recommendations—do not hallucinate unrelated metrics.
- Keep the narrative consistent with trends and backlog snapshot.

Here is the JSON report to analyze:

{{ data | tojson(indent=2) }}
