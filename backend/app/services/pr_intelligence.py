from __future__ import annotations

import re
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.db.models import BlastRadiusFinding, CodeSymbolIndex, PRRiskAssessment, PullRequest


RISK_TERMS = {
    "migration": 0.18,
    "auth": 0.16,
    "security": 0.18,
    "payment": 0.16,
    "database": 0.14,
    "schema": 0.14,
    "delete": 0.12,
    "permission": 0.12,
    "deploy": 0.1,
}


def assess_pr_risk(db: Session, repository_id: int, pr_number: int, persist: bool = True) -> dict[str, object]:
    pr = _load_pr(db, repository_id, pr_number)
    text = f"{pr.title}\n{pr.body or ''}".lower()
    factors = [{"reason": term, "weight": weight} for term, weight in RISK_TERMS.items() if term in text]
    symbols = _matching_symbols(db, repository_id, text)
    score = min(0.95, 0.18 + sum(float(item["weight"]) for item in factors) + min(len(symbols) * 0.04, 0.2))
    risk_level = "HIGH" if score >= 0.68 else "MEDIUM" if score >= 0.4 else "LOW"
    evidence_refs = [{"source_type": "pull_request", "source_id": pr.id, "github_number": pr.github_pr_number, "title": pr.title, "url": pr.html_url}]
    evidence_refs.extend({"source_type": "code_symbol", "source_id": item.id, "title": item.symbol_name, "file_path": item.file_path} for item in symbols[:5])
    test_recommendations = recommend_tests(pr.title, pr.body or "", [item.file_path for item in symbols])
    reviewers = sorted({pr.author for pr in [pr] if pr.author} | {symbol.metadata_json.get("last_author", "") for symbol in symbols if isinstance(symbol.metadata_json, dict)})[:4]
    result = {
        "repository_id": repository_id,
        "pull_request_id": pr.id,
        "github_pr_number": pr.github_pr_number,
        "risk_level": risk_level,
        "risk_score": round(score, 4),
        "factors": factors or [{"reason": "bounded_metadata_only", "weight": 0.18}],
        "recommended_reviewers": [item for item in reviewers if item],
        "test_recommendations": test_recommendations,
        "evidence_refs": evidence_refs,
        "status": "DETERMINISTIC_EVIDENCE_GROUNDED",
    }
    if persist:
        existing = db.query(PRRiskAssessment).filter_by(repository_id=repository_id, pull_request_id=pr.id).one_or_none()
        if existing:
            existing.risk_level = result["risk_level"]
            existing.risk_score = result["risk_score"]
            existing.factors = result["factors"]
            existing.recommended_reviewers = result["recommended_reviewers"]
            existing.test_recommendations = result["test_recommendations"]
            existing.evidence_refs = result["evidence_refs"]
            existing.created_at = datetime.now(UTC)
        else:
            db.add(PRRiskAssessment(**{key: result[key] for key in ("repository_id", "pull_request_id", "github_pr_number", "risk_level", "risk_score", "factors", "recommended_reviewers", "test_recommendations", "evidence_refs")}))
        db.commit()
    return result


def analyze_blast_radius(db: Session, repository_id: int, pr_number: int, persist: bool = True) -> dict[str, object]:
    pr = _load_pr(db, repository_id, pr_number)
    text = f"{pr.title}\n{pr.body or ''}".lower()
    symbols = _matching_symbols(db, repository_id, text)
    components = sorted(
        {Pathish(symbol.file_path).component for symbol in symbols}
        | set(re.findall(r"\b(api|backend|frontend|database|auth|tests?|docs|deployment)\b", text))
    )
    if not components:
        components = ["metadata-only"]
    impact_level = "HIGH" if any(item in components for item in ["api", "backend", "database", "auth"]) and len(components) >= 2 else "MEDIUM" if len(components) >= 2 else "LOW"
    evidence_refs = [{"source_type": "pull_request", "source_id": pr.id, "github_number": pr.github_pr_number, "title": pr.title, "url": pr.html_url}]
    evidence_refs.extend({"source_type": "code_symbol", "source_id": symbol.id, "file_path": symbol.file_path, "title": symbol.symbol_name} for symbol in symbols[:8])
    result = {
        "repository_id": repository_id,
        "pull_request_id": pr.id,
        "scope": "pull_request",
        "impact_level": impact_level,
        "affected_components": components[:8],
        "evidence_refs": evidence_refs,
        "status": "DETERMINISTIC_EVIDENCE_GROUNDED",
    }
    if persist:
        db.add(BlastRadiusFinding(**{key: result[key] for key in ("repository_id", "pull_request_id", "scope", "impact_level", "affected_components", "evidence_refs")}))
        db.commit()
    return result


def recommend_tests(title: str, body: str, paths: list[str]) -> list[str]:
    text = f"{title} {body} {' '.join(paths)}".lower()
    recommendations = []
    if any(term in text for term in ["api", "backend", "fastapi", "route"]):
        recommendations.append("Run backend route and service regression tests for affected API paths.")
    if any(term in text for term in ["frontend", "tsx", "ui", "page"]):
        recommendations.append("Run frontend typecheck, build, and Playwright route coverage.")
    if any(term in text for term in ["database", "migration", "schema"]):
        recommendations.append("Run migration upgrade on a disposable database before deployment.")
    if any(term in text for term in ["auth", "permission", "token", "secret"]):
        recommendations.append("Add security regression coverage for authorization and secret redaction.")
    return recommendations or ["Run repository smoke tests and targeted tests for files named in the PR evidence."]


def _load_pr(db: Session, repository_id: int, pr_number: int) -> PullRequest:
    pr = db.query(PullRequest).filter_by(repository_id=repository_id, github_pr_number=pr_number).one_or_none()
    if not pr:
        raise ValueError("Pull request not found")
    return pr


def _matching_symbols(db: Session, repository_id: int, text: str) -> list[CodeSymbolIndex]:
    tokens = {token for token in re.findall(r"[a-zA-Z_][a-zA-Z0-9_]{2,}", text.lower())}
    if not tokens:
        return []
    symbols = db.query(CodeSymbolIndex).filter_by(repository_id=repository_id).limit(200).all()
    return [symbol for symbol in symbols if any(token in f"{symbol.file_path} {symbol.symbol_name}".lower() for token in tokens)][:20]


class Pathish:
    def __init__(self, value: str) -> None:
        self.value = value

    @property
    def component(self) -> str:
        first = self.value.split("/", 1)[0]
        return first if first and "." not in first else "root"
