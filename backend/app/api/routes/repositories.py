from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Issue, PullRequest, Release, Repository
from app.db.session import get_db
from app.github.client import GitHubAuthenticationError, GitHubNotFoundError, GitHubServiceError
from app.rag.retriever import search_repository_history
from app.services.audit import log_audit_event
from app.services.github_sync import connect_repository, sync_repository

router = APIRouter(prefix="/api/repositories", tags=["repositories"])


class ConnectRepositoryRequest(BaseModel):
    repository: str


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


def repo_dict(repo: Repository) -> dict[str, object]:
    return {
        "id": repo.id,
        "github_id": repo.github_id,
        "owner": repo.owner,
        "name": repo.name,
        "full_name": repo.full_name,
        "description": repo.description,
        "html_url": repo.html_url,
        "default_branch": repo.default_branch,
        "language": repo.language,
        "stars": repo.stars,
        "created_at": repo.created_at,
        "updated_at": repo.updated_at,
        "last_synced_at": repo.last_synced_at,
    }


def issue_dict(issue: Issue) -> dict[str, object]:
    latest = issue.investigations[-1] if issue.investigations else None
    return {
        "id": issue.id,
        "repository_id": issue.repository_id,
        "github_issue_number": issue.github_issue_number,
        "title": issue.title,
        "body": issue.body,
        "state": issue.state,
        "author": issue.author,
        "labels": issue.labels,
        "html_url": issue.html_url,
        "analysis_status": issue.analysis_status,
        "classification": latest.classification if latest else None,
        "priority": latest.priority if latest else None,
        "escalation": latest.escalation_decision if latest else None,
        "created_at": issue.created_at,
        "updated_at": issue.updated_at,
        "closed_at": issue.closed_at,
        "last_synced_at": issue.last_synced_at,
    }


def pr_dict(pr: PullRequest) -> dict[str, object]:
    return {
        "id": pr.id,
        "repository_id": pr.repository_id,
        "github_pr_number": pr.github_pr_number,
        "title": pr.title,
        "body": pr.body,
        "state": pr.state,
        "author": pr.author,
        "html_url": pr.html_url,
        "created_at": pr.created_at,
        "updated_at": pr.updated_at,
        "merged_at": pr.merged_at,
    }


def release_dict(release: Release) -> dict[str, object]:
    return {
        "id": release.id,
        "repository_id": release.repository_id,
        "tag": release.tag,
        "name": release.name,
        "body": release.body,
        "html_url": release.html_url,
        "published_at": release.published_at,
    }


def handle_github_error(exc: Exception) -> HTTPException:
    if isinstance(exc, GitHubAuthenticationError):
        return HTTPException(status_code=401, detail="GitHub authentication failed")
    if isinstance(exc, GitHubNotFoundError):
        return HTTPException(status_code=404, detail="Repository not found")
    if isinstance(exc, GitHubServiceError):
        return HTTPException(status_code=502, detail=str(exc))
    return HTTPException(status_code=500, detail="Unexpected repository operation failure")


@router.post("/connect")
def connect(request: ConnectRepositoryRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    full_name = request.repository.strip()
    if "/" not in full_name:
        raise HTTPException(status_code=422, detail="Repository must be in owner/name format")
    if settings.demo_github_repository and full_name != settings.demo_github_repository:
        raise HTTPException(status_code=403, detail="Only the configured demo repository may be connected in this environment")
    try:
        repo, created = connect_repository(db, full_name)
    except Exception as exc:
        raise handle_github_error(exc) from exc
    log_audit_event(
        db,
        "REPOSITORY_CONNECTED",
        f"Connected repository {repo.full_name}.",
        repository_id=repo.id,
        metadata={"created": created},
    )
    db.commit()
    db.refresh(repo)
    return {"status": "connected", "created": created, "repository": repo_dict(repo)}


@router.get("")
def list_repositories(db: Session = Depends(get_db)) -> list[dict[str, object]]:
    return [repo_dict(repo) for repo in db.query(Repository).order_by(Repository.id).all()]


@router.get("/{repository_id}")
def get_repository(repository_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    repo = db.get(Repository, repository_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo_dict(repo)


@router.post("/{repository_id}/sync")
def sync(repository_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        result = sync_repository(db, repository_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise handle_github_error(exc) from exc
    log_audit_event(
        db,
        "REPOSITORY_SYNCED",
        f"Synchronized repository {db.get(Repository, repository_id).full_name}.",
        repository_id=repository_id,
        metadata={"documents_indexed": result.get("documents_indexed", 0)},
    )
    db.commit()
    return result


@router.get("/{repository_id}/issues")
def list_issues(repository_id: int, limit: int = Query(100, ge=1, le=200), db: Session = Depends(get_db)) -> list[dict[str, object]]:
    return [
        issue_dict(issue)
        for issue in db.query(Issue)
        .filter_by(repository_id=repository_id)
        .order_by(Issue.github_issue_number)
        .limit(limit)
        .all()
    ]


@router.get("/{repository_id}/pull-requests")
def list_pull_requests(repository_id: int, db: Session = Depends(get_db)) -> list[dict[str, object]]:
    return [pr_dict(pr) for pr in db.query(PullRequest).filter_by(repository_id=repository_id).order_by(PullRequest.github_pr_number).all()]


@router.get("/{repository_id}/releases")
def list_releases(repository_id: int, db: Session = Depends(get_db)) -> list[dict[str, object]]:
    return [release_dict(release) for release in db.query(Release).filter_by(repository_id=repository_id).order_by(Release.id).all()]


@router.post("/{repository_id}/search")
def search(repository_id: int, request: SearchRequest, db: Session = Depends(get_db)) -> list[dict[str, object]]:
    if not db.get(Repository, repository_id):
        raise HTTPException(status_code=404, detail="Repository not found")
    return [result.__dict__ for result in search_repository_history(db, repository_id, request.query, request.top_k)]
