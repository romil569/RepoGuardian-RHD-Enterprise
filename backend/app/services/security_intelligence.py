from __future__ import annotations

import re


SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("generic_api_key", re.compile(r"(?i)\b(api[_-]?key|token|secret)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}")),
)

INJECTION_TERMS = ("ignore previous instructions", "system prompt", "developer message", "exfiltrate", "disable policy")


def redact_untrusted_text(text: str) -> dict[str, object]:
    redacted = text
    findings: list[dict[str, object]] = []
    for label, pattern in SECRET_PATTERNS:
        matches = list(pattern.finditer(redacted))
        if matches:
            findings.append({"type": label, "count": len(matches)})
            redacted = pattern.sub("[REDACTED_SECRET]", redacted)
    return {"redacted_text": redacted, "findings": findings, "status": "REDACTED" if findings else "CLEAN"}


def prompt_injection_guard(text: str) -> dict[str, object]:
    lowered = text.lower()
    hits = [term for term in INJECTION_TERMS if term in lowered]
    return {
        "status": "BLOCK" if hits else "ALLOW",
        "reason_codes": [term.upper().replace(" ", "_") for term in hits],
        "policy": "Repository content is untrusted input and cannot override RepoGuardian system policy.",
    }
