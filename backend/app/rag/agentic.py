from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
from math import log2

from sqlalchemy.orm import Session

from app.db.models import IndexedDocument, Issue, PullRequest, Release
from app.rag.retriever import SearchResult, search_repository_history
from app.services.rhd import route_intent
from app.services.text import snippet, vectorize


class RetrievalStrategy(StrEnum):
    BM25 = "BM25"
    DENSE = "DENSE"
    CODE = "CODE"
    GRAPH = "GRAPH"
    RECENT = "RECENT"
    RELEASE = "RELEASE"
    PR = "PR"
    ISSUE = "ISSUE"


@dataclass(frozen=True)
class QueryPlan:
    intent: str
    strategies: list[RetrievalStrategy]
    max_candidates: int = 12
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvidenceCandidate:
    repository_id: int
    source_type: str
    source_id: int
    github_number: int | None
    title: str
    snippet: str
    source_url: str | None
    score: float
    retrievers: tuple[str, ...]


def plan_query(question: str) -> QueryPlan:
    intent = route_intent(question)
    text = question.lower()
    strategies: list[RetrievalStrategy] = [RetrievalStrategy.BM25, RetrievalStrategy.DENSE]
    reasons = ["lexical_semantic_baseline"]
    if any(term in text for term in ["release", "regression", "after", "v1.", "broke"]):
        strategies.extend([RetrievalStrategy.RELEASE, RetrievalStrategy.PR, RetrievalStrategy.RECENT])
        reasons.append("release_temporal_context")
    if any(term in text for term in ["pr", "pull request", "blast radius", "change"]):
        strategies.extend([RetrievalStrategy.PR, RetrievalStrategy.CODE, RetrievalStrategy.GRAPH])
        reasons.append("change_risk_context")
    if any(term in text for term in ["code", "symbol", "function", "file", "root cause", "stack"]):
        strategies.extend([RetrievalStrategy.CODE, RetrievalStrategy.GRAPH])
        reasons.append("code_context")
    if any(term in text for term in ["security", "secret", "credential", "vulnerability"]):
        strategies.extend([RetrievalStrategy.ISSUE, RetrievalStrategy.CODE])
        reasons.append("security_evidence_context")
    if intent in {"DUPLICATE_ANALYSIS", "ISSUE_LOOKUP", "NEEDS_INFORMATION", "TOP_PRIORITIES"}:
        strategies.append(RetrievalStrategy.ISSUE)
        reasons.append("issue_backlog_context")
    deduped = list(dict.fromkeys(strategies))
    return QueryPlan(intent=intent, strategies=deduped, reason_codes=tuple(reasons))


def retrieve_agentic_evidence(db: Session, repository_id: int, question: str, top_k: int = 8) -> dict[str, object]:
    plan = plan_query(question)
    candidates: dict[tuple[str, int], EvidenceCandidate] = {}
    for strategy in plan.strategies:
        for candidate in _retrieve_for_strategy(db, repository_id, question, strategy, plan.max_candidates):
            key = (candidate.source_type, candidate.source_id)
            existing = candidates.get(key)
            if existing:
                merged_retrievers = tuple(dict.fromkeys([*existing.retrievers, *candidate.retrievers]))
                candidates[key] = EvidenceCandidate(
                    repository_id=existing.repository_id,
                    source_type=existing.source_type,
                    source_id=existing.source_id,
                    github_number=existing.github_number,
                    title=existing.title,
                    snippet=existing.snippet,
                    source_url=existing.source_url,
                    score=round(existing.score + candidate.score * 0.4, 4),
                    retrievers=merged_retrievers,
                )
            else:
                candidates[key] = candidate
    ranked = sorted(candidates.values(), key=lambda item: item.score, reverse=True)[:top_k]
    critic = evidence_critic(repository_id, ranked)
    return {
        "plan": {"intent": plan.intent, "strategies": [item.value for item in plan.strategies], "reason_codes": list(plan.reason_codes)},
        "evidence": [item.__dict__ for item in ranked],
        "critic": critic,
    }


def _retrieve_for_strategy(db: Session, repository_id: int, question: str, strategy: RetrievalStrategy, limit: int) -> list[EvidenceCandidate]:
    if strategy in {RetrievalStrategy.BM25, RetrievalStrategy.DENSE}:
        return [_from_search_result(result, strategy) for result in search_repository_history(db, repository_id, question, top_k=limit)]
    if strategy == RetrievalStrategy.RECENT:
        docs = db.query(IndexedDocument).filter_by(repository_id=repository_id).order_by(IndexedDocument.indexed_at.desc()).limit(limit).all()
        return [_from_document(doc, question, strategy, 0.2) for doc in docs]
    if strategy == RetrievalStrategy.RELEASE:
        releases = db.query(Release).filter_by(repository_id=repository_id).order_by(Release.published_at.desc().nullslast()).limit(limit).all()
        return [_candidate(repository_id, "release", item.id, None, item.tag, item.body or item.name or item.tag, item.html_url, 0.55, strategy) for item in releases]
    if strategy == RetrievalStrategy.PR:
        prs = db.query(PullRequest).filter_by(repository_id=repository_id).order_by(PullRequest.updated_at.desc().nullslast()).limit(limit).all()
        return [_candidate(repository_id, "pull_request", item.id, item.github_pr_number, item.title, item.body or item.title, item.html_url, 0.45, strategy) for item in prs]
    if strategy == RetrievalStrategy.ISSUE:
        issues = db.query(Issue).filter_by(repository_id=repository_id).order_by(Issue.updated_at.desc().nullslast()).limit(limit).all()
        return [_candidate(repository_id, "issue", item.id, item.github_issue_number, item.title, item.body or item.title, item.html_url, 0.4, strategy) for item in issues]
    if strategy in {RetrievalStrategy.CODE, RetrievalStrategy.GRAPH}:
        docs = db.query(IndexedDocument).filter_by(repository_id=repository_id, source_type="code").limit(limit).all()
        return [_from_document(doc, question, strategy, 0.5 if strategy == RetrievalStrategy.CODE else 0.35) for doc in docs]
    return []


def _from_search_result(result: SearchResult, strategy: RetrievalStrategy) -> EvidenceCandidate:
    return EvidenceCandidate(
        repository_id=result.repository_id,
        source_type=result.source_type,
        source_id=result.source_id,
        github_number=result.github_number,
        title=result.title,
        snippet=result.snippet,
        source_url=result.source_url,
        score=result.relevance_score,
        retrievers=(strategy.value,),
    )


def _from_document(doc: IndexedDocument, question: str, strategy: RetrievalStrategy, base_score: float) -> EvidenceCandidate:
    query_vector = vectorize(question)
    keyword_hits = sum(1 for token in query_vector if token in (doc.text or "").lower() or token in doc.title.lower())
    score = base_score + min(keyword_hits * 0.04, 0.24)
    return _candidate(doc.repository_id, doc.source_type, doc.source_id, doc.github_number, doc.title, doc.text, doc.source_url, score, strategy)


def _candidate(repository_id: int, source_type: str, source_id: int, github_number: int | None, title: str, text: str, source_url: str | None, score: float, strategy: RetrievalStrategy) -> EvidenceCandidate:
    return EvidenceCandidate(repository_id, source_type, source_id, github_number, title, snippet(text, title), source_url, round(score, 4), (strategy.value,))


def evidence_critic(repository_id: int, candidates: list[EvidenceCandidate]) -> dict[str, object]:
    violations = [item for item in candidates if item.repository_id != repository_id]
    source_mix = Counter(item.source_type for item in candidates)
    coverage = "HIGH" if len(candidates) >= 5 and len(source_mix) >= 2 else "MEDIUM" if candidates else "LOW"
    return {
        "status": "FAILED" if violations else "PASSED",
        "repository_isolation_violations": len(violations),
        "grounding_coverage": coverage,
        "source_mix": dict(source_mix),
    }


def evaluate_retrieval(retrieved_ids: list[str], relevant_ids: set[str], k: int = 5) -> dict[str, float]:
    top = retrieved_ids[:k]
    hits = [1 if item in relevant_ids else 0 for item in top]
    recall = sum(hits) / len(relevant_ids) if relevant_ids else 0.0
    precision = sum(hits) / k if k else 0.0
    reciprocal_rank = next((1 / (idx + 1) for idx, item in enumerate(top) if item in relevant_ids), 0.0)
    dcg = sum(hit / log2(idx + 2) for idx, hit in enumerate(hits))
    ideal_hits = [1] * min(len(relevant_ids), k)
    idcg = sum(hit / log2(idx + 2) for idx, hit in enumerate(ideal_hits))
    ndcg = dcg / idcg if idcg else 0.0
    return {
        "recall_at_k": round(recall, 4),
        "precision_at_k": round(precision, 4),
        "mrr": round(reciprocal_rank, 4),
        "ndcg": round(ndcg, 4),
    }
