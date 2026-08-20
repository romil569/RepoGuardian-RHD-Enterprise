from __future__ import annotations

import hashlib
import hmac

from app.api.routes.github_webhook import event_source, normalize_summary, verify_signature
from app.core.config import settings
from app.db.models import Repository, RepositoryEvent
from app.ml.registry import MLModelStatus, model_status_cards
from app.platform.queue import JobType
from app.platform.runtime import job_queue
from app.services.code_intelligence import analyze_source_tree, build_code_graph, root_cause_hypotheses


def add_repo(db_session, full_name: str = "owner/repo") -> Repository:
    repo = Repository(github_id=123, owner="owner", name="repo", full_name=full_name, html_url=f"https://github.com/{full_name}")
    db_session.add(repo)
    db_session.commit()
    return repo


def test_webhook_signature_verification(monkeypatch):
    monkeypatch.setattr(settings, "github_webhook_secret", "secret")
    body = b'{"zen":"Keep it logically awesome."}'
    digest = hmac.new(b"secret", body, hashlib.sha256).hexdigest()
    assert verify_signature(body, f"sha256={digest}") is True
    assert verify_signature(body, "sha256=bad") is False


def test_webhook_stores_event_and_queues_job(db_session, monkeypatch):
    repo = add_repo(db_session)
    monkeypatch.setattr(settings, "github_webhook_secret", None)
    payload = {"action": "opened", "repository": {"full_name": repo.full_name}, "issue": {"id": 99, "number": 1}}
    source_type, source_id = event_source(payload)
    event = RepositoryEvent(repository_id=repo.id, event_type="issues", source_type=source_type, source_id=source_id, summary=normalize_summary("issues", payload))
    db_session.add(event)
    db_session.commit()
    job = job_queue.enqueue(JobType.ISSUE_INVESTIGATION, repo.id, {"event_id": event.id}, correlation_id="delivery-1")
    assert db_session.query(RepositoryEvent).filter_by(repository_id=repo.id, event_type="issues").count() == 1
    assert job_queue.get(job.id) is not None


def test_code_intelligence_extracts_symbols_and_graph(tmp_path):
    source = tmp_path / "app.py"
    source.write_text("import os\n\nclass AuthService:\n    def validate_token(self):\n        return True\n", encoding="utf-8")
    analysis = analyze_source_tree(1, tmp_path)
    assert analysis["languages"] == ["Python"]
    assert any(symbol["symbol_name"] == "AuthService" for symbol in analysis["symbols"])
    graph = build_code_graph(1, analysis)
    assert graph.neighbors("repo:1", "CONTAINS")
    hypotheses = root_cause_hypotheses("auth token fails", analysis)
    assert hypotheses[0]["hypothesis"] != "INSUFFICIENT_EVIDENCE"


def test_ml_registry_reports_insufficient_data_without_fake_metrics():
    cards = model_status_cards()
    assert {card.status for card in cards} == {MLModelStatus.DETERMINISTIC_FALLBACK}
    assert all(card.metrics["reason"] == "INSUFFICIENT_TRAINING_DATA" for card in cards)
