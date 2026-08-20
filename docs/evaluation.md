# Evaluation Framework

RepoGuardian Prompt 3 supports maintainer feedback as labeled correction data for completed investigations.

## Feedback API

- `POST /api/investigations/{investigation_id}/feedback`
- `GET /api/investigations/{investigation_id}/feedback`

Allowed targets are:

- `classification`
- `priority`
- `duplicate_recommendation`
- `escalation_recommendation`
- `security_signal`

Allowed statuses are:

- `CORRECT`
- `INCORRECT`
- `ADJUSTED`

Corrected values are validated against the allowed enum values for the selected target.

## Metrics

`GET /api/repositories/{repository_id}/evaluation` reads feedback for that repository. Fewer than three labeled feedback items returns:

```json
{
  "status": "INSUFFICIENT_LABELED_DATA",
  "labeled_count": 0,
  "metrics": {},
  "confusion_matrix": []
}
```

With at least three labeled items, the endpoint reports:

- `human_agreement_rate`
- `classification_accuracy`
- Classification confusion matrix rows as predicted, actual, and count

The current implementation is deterministic and intentionally simple. Future prompts can expand it with per-signal metrics, reviewer identity, sampling windows, calibration charts, and drift monitoring.
