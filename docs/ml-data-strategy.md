# ML Data Strategy

RepoGuardian does not promote ML models from tiny demo data. Training requires defensible, reproducible public or user-authorized data and temporal validation.

## Collection

Use `scripts/build-ml-dataset.py` with an explicit repository allow-list. The collector records the repository, collection timestamp, row counts, and public GitHub API basis. Private repositories are out of scope unless the user explicitly authorizes them.

Example allow-list:

```json
{
  "repositories": ["owner/repository"]
}
```

Dry run:

```powershell
python scripts\build-ml-dataset.py --allow-list data\ml\allow-list.example.json --dry-run
```

## Activation Thresholds

| Model | Minimum Data Before Training | Acceptance Rule |
|---|---:|---|
| Duplicate ML | 200 labeled duplicate/nonduplicate pairs | Beat deterministic baseline on F1 or PR-AUC with acceptable precision |
| Priority ML | 500 issues with defensible priority/severity labels | Macro F1 and per-class recall must meet documented threshold |
| PR Risk ML | 300 PRs with documented weak/strong risk labels | Must report `risk_label_source`; no causation claims from proxy labels |
| Resolution Time | 500 closed issues with creation-time-safe features | Beat median/moving-baseline MAE |
| Backlog Forecast | 26+ weekly history points | Beat moving average or remain deterministic |
| Anomaly Detection | 26+ stable operational windows | Report anomalies as signals, not incidents |
| Release Risk | 50 releases with post-release windows | Beat deterministic release analyzer |
| Reviewer Recommendation | 300 historical reviewed PRs | Top-3 recall must exceed ownership heuristic |

## Leakage Controls

- Prefer temporal splits: train on earlier history and validate/test on later history.
- Do not use future labels or final-state features for creation-time predictions.
- Keep duplicate issue pairs grouped so near-identical examples do not leak across splits.
- Preserve dataset version, feature version, repository list, training window, test window, metrics, and artifact checksum for every model artifact.

## Current Status

No model is activated from ML training yet. Registry cards correctly remain `DETERMINISTIC_FALLBACK` until a dataset meets the thresholds above.
