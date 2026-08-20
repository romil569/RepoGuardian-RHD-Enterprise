from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from time import perf_counter
from typing import Protocol
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.core.config import settings


@dataclass
class ModelRequest:
    task: str
    prompt: str
    repository_visibility: str = "public"
    require_json: bool = False


@dataclass
class ModelResponse:
    provider: str
    model: str
    task: str
    status: str
    content: str
    latency_ms: int
    error: str | None = None
    tokens: int | None = None


class ModelProvider(Protocol):
    name: str
    model: str

    def configured(self) -> bool:
        ...

    def generate(self, request: ModelRequest) -> ModelResponse:
        ...


@dataclass
class ProviderCircuit:
    failures: int = 0
    successes: int = 0
    opened_until: datetime | None = None

    def allow(self) -> bool:
        return self.opened_until is None or datetime.now(UTC) >= self.opened_until

    def record_success(self) -> None:
        self.successes += 1
        self.failures = 0
        self.opened_until = None

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= 3:
            self.opened_until = datetime.now(UTC) + timedelta(minutes=5)


class DeterministicProvider:
    name = "deterministic"
    model = "template-router"

    def configured(self) -> bool:
        return True

    def generate(self, request: ModelRequest) -> ModelResponse:
        start = perf_counter()
        return ModelResponse(
            provider=self.name,
            model=self.model,
            task=request.task,
            status="OK",
            content=f"Deterministic fallback handled {request.task}. Use repository tools for factual evidence.",
            latency_ms=int((perf_counter() - start) * 1000),
        )


@dataclass
class ConfigOnlyProvider:
    name: str
    model: str
    api_key: str | None = None
    local_endpoint: str | None = None

    def configured(self) -> bool:
        if self.api_key:
            return True
        if self.local_endpoint:
            try:
                with urlopen(f"{self.local_endpoint.rstrip('/')}/api/tags", timeout=0.5) as response:
                    return 200 <= response.status < 500
            except (OSError, URLError):
                return False
        return False

    def generate(self, request: ModelRequest) -> ModelResponse:
        start = perf_counter()
        if not self.configured():
            return ModelResponse(self.name, self.model, request.task, "NOT_CONFIGURED", "", int((perf_counter() - start) * 1000), error="Provider is not configured")
        return ModelResponse(self.name, self.model, request.task, "NOT_IMPLEMENTED", "", int((perf_counter() - start) * 1000), error="Network provider adapter is configured but not executed in this environment")


@dataclass
class OllamaProvider:
    name: str
    model: str
    base_url: str
    timeout_seconds: int = 60

    def configured(self) -> bool:
        if settings.is_serverless:
            return False
        try:
            with urlopen(f"{self.base_url.rstrip('/')}/api/tags", timeout=0.5) as response:
                return 200 <= response.status < 500
        except (OSError, URLError):
            return False

    def generate(self, request: ModelRequest) -> ModelResponse:
        start = perf_counter()
        if settings.is_serverless:
            return ModelResponse(self.name, self.model, request.task, "NOT_CONFIGURED", "", int((perf_counter() - start) * 1000), error="Ollama is local-development only in managed cloud")
        if not self.configured():
            return ModelResponse(self.name, self.model, request.task, "NOT_CONFIGURED", "", int((perf_counter() - start) * 1000), error="Ollama API is not reachable")

        payload: dict[str, object] = {
            "model": self.model,
            "prompt": request.prompt,
            "stream": False,
            "options": {
                "num_ctx": 1024,
                "num_predict": 256,
                "temperature": 0.1,
            },
        }
        if request.require_json:
            payload["format"] = "json"

        try:
            http_request = Request(
                f"{self.base_url.rstrip('/')}/api/generate",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(http_request, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            return ModelResponse(self.name, self.model, request.task, "ERROR", "", int((perf_counter() - start) * 1000), error=str(exc))

        return ModelResponse(
            provider=self.name,
            model=self.model,
            task=request.task,
            status="OK",
            content=str(body.get("response", "")),
            latency_ms=int((perf_counter() - start) * 1000),
            tokens=body.get("eval_count") if isinstance(body.get("eval_count"), int) else None,
        )


@dataclass
class ModelGateway:
    providers: dict[str, ModelProvider]
    priority: list[str]
    circuits: dict[str, ProviderCircuit] = field(default_factory=dict)
    telemetry: list[ModelResponse] = field(default_factory=list)

    @classmethod
    def from_settings(cls) -> "ModelGateway":
        providers: dict[str, ModelProvider] = {
            "ollama": OllamaProvider("ollama", settings.ollama_model, settings.ollama_base_url, settings.ollama_timeout_seconds),
            "groq": ConfigOnlyProvider("groq", settings.groq_model, api_key=settings.groq_api_key),
            "openrouter": ConfigOnlyProvider("openrouter", settings.openrouter_model, api_key=settings.openrouter_api_key),
            "openai": ConfigOnlyProvider("openai", settings.openai_model, api_key=settings.openai_api_key),
            "deterministic": DeterministicProvider(),
        }
        priority = [item.strip() for item in settings.ai_provider_priority.split(",") if item.strip()]
        return cls(providers=providers, priority=priority)

    def generate(self, request: ModelRequest) -> ModelResponse:
        for provider_name in self.priority:
            provider = self.providers.get(provider_name)
            if not provider:
                continue
            if request.repository_visibility == "private" and provider_name not in {"ollama", "deterministic"} and not settings.allow_external_model_for_private_repos:
                continue
            circuit = self.circuits.setdefault(provider_name, ProviderCircuit())
            if not circuit.allow():
                continue
            response = provider.generate(request)
            self.telemetry.append(response)
            if response.status == "OK":
                circuit.record_success()
                return response
            circuit.record_failure()
        fallback = self.providers["deterministic"].generate(request)
        self.telemetry.append(fallback)
        return fallback

    def status(self) -> list[dict[str, object]]:
        rows = []
        for name, provider in self.providers.items():
            circuit = self.circuits.setdefault(name, ProviderCircuit())
            rows.append(
                {
                    "provider": name,
                    "model": provider.model,
                    "configured": provider.configured(),
                    "circuit_open": not circuit.allow(),
                    "successes": circuit.successes,
                    "failures": circuit.failures,
                }
            )
        return rows
