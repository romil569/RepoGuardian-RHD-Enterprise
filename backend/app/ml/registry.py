from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MLModelStatus(StrEnum):
    TRAINED_AND_VALIDATED = "TRAINED_AND_VALIDATED"
    TRAINED_LOW_DATA_WARNING = "TRAINED_LOW_DATA_WARNING"
    NOT_TRAINED_INSUFFICIENT_DATA = "NOT_TRAINED_INSUFFICIENT_DATA"
    DETERMINISTIC_FALLBACK = "DETERMINISTIC_FALLBACK"


@dataclass(frozen=True)
class ModelCard:
    name: str
    task: str
    status: MLModelStatus
    training_rows: int
    test_rows: int
    metrics: dict[str, float | str]
    fallback: str
    version: str = "untrained-v0"


MODEL_NAMES = [
    ("Duplicate ML", "duplicate_prediction", "deterministic duplicate engine"),
    ("Priority ML", "priority_prediction", "deterministic priority engine"),
    ("PR Risk ML", "pr_risk_prediction", "deterministic PR risk rules"),
    ("Resolution Time ML", "resolution_time_forecast", "historical median fallback"),
    ("Backlog Forecasting", "backlog_forecast", "repository health trend fallback"),
    ("Anomaly Detection", "repository_anomaly_detection", "deterministic threshold fallback"),
    ("Release Risk", "release_risk_prediction", "release regression analyzer"),
    ("Reviewer Recommendation", "reviewer_recommendation", "maintainer policy fallback"),
]


def model_status_cards(training_rows_by_task: dict[str, int] | None = None, minimum_rows: int = 30) -> list[ModelCard]:
    rows = training_rows_by_task or {}
    cards: list[ModelCard] = []
    for name, task, fallback in MODEL_NAMES:
        training_rows = rows.get(task, 0)
        if training_rows >= minimum_rows:
            status = MLModelStatus.TRAINED_LOW_DATA_WARNING
            metrics: dict[str, float | str] = {"validation": "not run in current environment"}
            test_rows = max(1, int(training_rows * 0.2))
        elif training_rows > 0:
            status = MLModelStatus.NOT_TRAINED_INSUFFICIENT_DATA
            metrics = {"reason": "INSUFFICIENT_TRAINING_DATA"}
            test_rows = 0
        else:
            status = MLModelStatus.DETERMINISTIC_FALLBACK
            metrics = {"reason": "INSUFFICIENT_TRAINING_DATA"}
            test_rows = 0
        cards.append(ModelCard(name=name, task=task, status=status, training_rows=training_rows, test_rows=test_rows, metrics=metrics, fallback=fallback))
    return cards
