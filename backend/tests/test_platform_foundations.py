from __future__ import annotations

import json

from app.platform import model_gateway
from app.platform.model_gateway import ConfigOnlyProvider, DeterministicProvider, ModelGateway, ModelRequest, OllamaProvider
from app.platform.queue import JobStatus, JobType, LocalJobQueue
from app.platform.stores import LocalGraphStore


def test_local_job_queue_deduplicates_and_runs_job():
    queue = LocalJobQueue()
    first = queue.enqueue(JobType.REPOSITORY_SYNC, 1, {"depth": "initial"}, correlation_id="repo-1-sync")
    duplicate = queue.enqueue(JobType.REPOSITORY_SYNC, 1, {"depth": "initial"}, correlation_id="repo-1-sync")
    assert duplicate.id == first.id

    ran = []
    completed = queue.run_next({JobType.REPOSITORY_SYNC: lambda job: ran.append(job.repository_id)})
    assert completed is not None
    assert completed.status == JobStatus.COMPLETED
    assert ran == [1]


def test_local_job_queue_records_missing_handler_failure():
    queue = LocalJobQueue()
    job = queue.enqueue(JobType.CODE_INDEX, 1, {})
    result = queue.run_next({})
    assert result is job
    assert job.status == JobStatus.FAILED
    assert job.error == "No handler registered"


def test_local_graph_store_requires_verified_nodes_and_traverses_neighbors():
    graph = LocalGraphStore()
    graph.add_node("repo:1", ["Repository"], {"full_name": "owner/repo"})
    graph.add_node("issue:1", ["Issue"], {"number": 1})
    graph.add_edge("repo:1", "issue:1", "CONTAINS")
    assert graph.neighbors("repo:1", "CONTAINS")[0]["node"]["properties"]["number"] == 1


def test_model_gateway_uses_deterministic_fallback_when_cloud_unconfigured():
    gateway = ModelGateway(
        providers={
            "groq": ConfigOnlyProvider("groq", "test-model", api_key=None),
            "deterministic": DeterministicProvider(),
        },
        priority=["groq", "deterministic"],
    )
    response = gateway.generate(ModelRequest(task="intent", prompt="What should I fix first?"))
    assert response.provider == "deterministic"
    assert response.status == "OK"
    status = {item["provider"]: item for item in gateway.status()}
    assert status["groq"]["failures"] == 1


def test_model_gateway_private_repo_skips_external_provider():
    gateway = ModelGateway(
        providers={
            "openrouter": ConfigOnlyProvider("openrouter", "free", api_key="configured"),
            "deterministic": DeterministicProvider(),
        },
        priority=["openrouter", "deterministic"],
    )
    response = gateway.generate(ModelRequest(task="summary", prompt="summarize", repository_visibility="private"))
    assert response.provider == "deterministic"


def test_local_provider_requires_reachable_endpoint():
    provider = ConfigOnlyProvider("ollama", "test-model", local_endpoint="http://127.0.0.1:9")
    assert provider.configured() is False


def test_ollama_provider_generates_with_local_api(monkeypatch):
    calls = []

    class FakeResponse:
        status = 200

        def __init__(self, payload: dict[str, object] | None = None):
            self.payload = payload or {}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps(self.payload).encode("utf-8")

    def fake_urlopen(request, timeout):
        calls.append((request, timeout))
        if isinstance(request, str):
            return FakeResponse()
        return FakeResponse({"response": "RepoGuardian local model OK", "eval_count": 5})

    monkeypatch.setattr(model_gateway, "urlopen", fake_urlopen)
    provider = OllamaProvider("ollama", "qwen3:1.7b", "http://127.0.0.1:11434", timeout_seconds=30)

    response = provider.generate(ModelRequest(task="probe", prompt="Say OK"))

    assert response.status == "OK"
    assert response.provider == "ollama"
    assert response.content == "RepoGuardian local model OK"
    assert response.tokens == 5
    assert len(calls) == 2
