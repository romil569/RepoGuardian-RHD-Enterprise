# Repository Health Score

RepoGuardian Prompt 3 computes repository health deterministically from synchronized repository records and completed investigations. The score is intentionally explainable and stable for tests.

## Inputs

- Open issues in the synchronized repository
- Stale open issues, using `STALE_ISSUE_DAYS` or the default 30 days
- Completed investigation priority values
- Completed investigation escalation decisions
- Synchronized issue comments for first-response timing
- Synchronized pull request and release counts for activity signals

## Dimension Scores

Each dimension is clamped to `0..100`.

- Backlog: `100 - open_issue_count * 4`
- Staleness: `100 - stale_open_issue_ratio * 100`
- Priority risk: `100 - high_priority_count * 8 - critical_count * 15`
- Duplicate burden: `100 - possible_duplicate_ratio * 100`
- Response: `100` when no response data exists; otherwise `100 - median_first_response_hours`

The overall health score is the rounded average of the five dimensions.

## States

- `HEALTHY`: score >= 80
- `WATCH`: score >= 60
- `DEGRADED`: score >= 40
- `CRITICAL_ATTENTION`: score < 40

## Output

`GET /api/repositories/{repository_id}/health` returns the overall score, dimension scores, raw signals, classification and priority distributions, and a minimal issue creation versus closure history. When fewer than 20 synchronized issues exist, the history marks `insufficient_history: true`.
