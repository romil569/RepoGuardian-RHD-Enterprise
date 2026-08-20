# ML Platform

RHD ML is represented as explicit model cards. A model is not described as trained unless it has sufficient rows and validation.

Current model status values:

- `TRAINED_AND_VALIDATED`
- `TRAINED_LOW_DATA_WARNING`
- `NOT_TRAINED_INSUFFICIENT_DATA`
- `DETERMINISTIC_FALLBACK`

Current model registry:

- Duplicate ML
- Priority ML
- PR Risk ML
- Resolution Time ML
- Backlog Forecasting
- Anomaly Detection
- Release Risk
- Reviewer Recommendation

Current implementation status:

All listed models report deterministic fallback or insufficient training data unless reproducible training rows are provided. Existing deterministic engines remain the production demo fallback.

Future training rows must record repository, target, timestamp, feature version, and split assignment to reduce leakage risk.
