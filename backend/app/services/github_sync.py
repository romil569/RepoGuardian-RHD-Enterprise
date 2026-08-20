from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from time import perf_counter
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Comment, Issue, PullRequest, Release, Repository
from app.github.client import GitHubCliService, GitHubRestService, github_service
from app.services.indexing import index_repository


def stable_github_int(value: object) -> int:
    text = str(value or "0")
    if text.isdigit():
        return int(text)
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:12], 16) % 2_000_000_000


def parse_dt(value: str | None):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def label_names(labels: list[dict[str, Any]] | None) -> list[str]:
    return [label.get("name", "") for label in labels or [] if label.get("name")]


def connect_repository(db: Session, full_name: str, github: GitHubCliService | GitHubRestService | None = None) -> tuple[Repository, bool]:
    github = github or github_service()
    metadata = github.get_repository(full_name)
    owner = metadata["owner"]["login"] if isinstance(metadata.get("owner"), dict) else full_name.split("/")[0]
    name = metadata.get("name") or full_name.split("/")[-1]
    existing = db.query(Repository).filter_by(full_name=metadata.get("nameWithOwner", full_name)).one_or_none()
    created = existing is None
    repo = existing or Repository(github_id=stable_github_int(metadata.get("id")), owner=owner, name=name, full_name=metadata.get("nameWithOwner", full_name), html_url=metadata["url"])
    repo.github_id = stable_github_int(metadata.get("id"))
    repo.owner = owner
    repo.name = name
    repo.full_name = metadata.get("nameWithOwner", full_name)
    repo.description = metadata.get("description")
    repo.html_url = metadata["url"]
    repo.default_branch = (metadata.get("defaultBranchRef") or {}).get("name") or "main"
    repo.language = (metadata.get("primaryLanguage") or {}).get("name")
    repo.stars = metadata.get("stargazerCount") or 0
    repo.updated_at = parse_dt(metadata.get("updatedAt")) or datetime.now(UTC)
    if created:
        repo.created_at = parse_dt(metadata.get("createdAt")) or datetime.now(UTC)
        db.add(repo)
    db.commit()
    db.refresh(repo)
    return repo, created


def _upsert_issue(db: Session, repository_id: int, item: dict[str, Any]) -> tuple[Issue, str]:
    number = item["number"]
    issue = db.query(Issue).filter_by(repository_id=repository_id, github_issue_number=number).one_or_none()
    status = "updated" if issue else "added"
    issue = issue or Issue(repository_id=repository_id, github_issue_number=number, github_id=stable_github_int(item.get("id")), html_url=item["url"], title=item["title"], state=item["state"])
    issue.github_id = stable_github_int(item.get("id")) or issue.github_id or 0
    issue.title = item["title"]
    issue.body = item.get("body") or ""
    issue.state = item.get("state") or "UNKNOWN"
    issue.author = (item.get("author") or {}).get("login")
    issue.labels = label_names(item.get("labels"))
    issue.html_url = item["url"]
    issue.created_at = parse_dt(item.get("createdAt"))
    issue.updated_at = parse_dt(item.get("updatedAt"))
    issue.closed_at = parse_dt(item.get("closedAt"))
    issue.last_synced_at = datetime.now(UTC)
    issue.analysis_status = "PENDING" if status == "added" else issue.analysis_status
    if status == "added":
        db.add(issue)
    return issue, status


def _upsert_pr(db: Session, repository_id: int, item: dict[str, Any]) -> tuple[PullRequest, str]:
    number = item["number"]
    pr = db.query(PullRequest).filter_by(repository_id=repository_id, github_pr_number=number).one_or_none()
    status = "updated" if pr else "added"
    pr = pr or PullRequest(repository_id=repository_id, github_pr_number=number, github_id=stable_github_int(item.get("id")), html_url=item["url"], title=item["title"], state=item["state"])
    pr.github_id = stable_github_int(item.get("id")) or pr.github_id or 0
    pr.title = item["title"]
    pr.body = item.get("body") or ""
    pr.state = item.get("state") or "UNKNOWN"
    pr.author = (item.get("author") or {}).get("login")
    pr.html_url = item["url"]
    pr.created_at = parse_dt(item.get("createdAt"))
    pr.updated_at = parse_dt(item.get("updatedAt"))
    pr.merged_at = parse_dt(item.get("mergedAt"))
    pr.last_synced_at = datetime.now(UTC)
    if status == "added":
        db.add(pr)
    return pr, status


def _upsert_release(db: Session, repository_id: int, item: dict[str, Any]) -> tuple[Release, str]:
    tag = item["tagName"]
    release = db.query(Release).filter_by(repository_id=repository_id, tag=tag).one_or_none()
    status = "updated" if release else "added"
    release = release or Release(repository_id=repository_id, tag=tag, github_id=stable_github_int(item.get("id")), html_url=item["url"])
    release.github_id = stable_github_int(item.get("id")) or release.github_id or 0
    release.name = item.get("name")
    release.body = item.get("body") or ""
    release.html_url = item["url"]
    release.published_at = parse_dt(item.get("publishedAt"))
    release.last_synced_at = datetime.now(UTC)
    if status == "added":
        db.add(release)
    return release, status


def _upsert_comment(db: Session, repository_id: int, issue_id: int, item: dict[str, Any]) -> str:
    comment = db.query(Comment).filter_by(repository_id=repository_id, github_id=item["id"]).one_or_none()
    status = "updated" if comment else "added"
    comment = comment or Comment(repository_id=repository_id, github_id=item["id"], issue_id=issue_id)
    comment.issue_id = issue_id
    comment.author = item.get("user")
    comment.body = item.get("body") or ""
    comment.html_url = item.get("html_url")
    comment.created_at = parse_dt(item.get("created_at"))
    comment.updated_at = parse_dt(item.get("updated_at"))
    if status == "added":
        db.add(comment)
    return status


def sync_repository(db: Session, repository_id: int, github: GitHubCliService | GitHubRestService | None = None) -> dict[str, object]:
    start = perf_counter()
    repo = db.get(Repository, repository_id)
    if not repo:
        raise ValueError("Repository not found")
    github = github or github_service()
    counts = {
        "issues_added": 0,
        "issues_updated": 0,
        "pull_requests_added": 0,
        "pull_requests_updated": 0,
        "comments_added": 0,
        "comments_updated": 0,
        "releases_added": 0,
        "releases_updated": 0,
    }
    issue_limit = settings.max_public_issues if settings.public_analysis_mode else 100
    pr_limit = settings.max_public_prs if settings.public_analysis_mode else 100
    release_limit = settings.max_public_releases if settings.public_analysis_mode else 30
    for item in github.get_repository_issues(repo.full_name, limit=issue_limit):
        issue, status = _upsert_issue(db, repo.id, item)
        db.flush()
        counts[f"issues_{status}"] += 1
        for comment in github.get_issue_comments(repo.full_name, issue.github_issue_number):
            comment_status = _upsert_comment(db, repo.id, issue.id, comment)
            counts[f"comments_{comment_status}"] += 1
    for item in github.get_pull_requests(repo.full_name, limit=pr_limit):
        _, status = _upsert_pr(db, repo.id, item)
        counts[f"pull_requests_{status}"] += 1
    for item in github.get_releases(repo.full_name, limit=release_limit):
        _, status = _upsert_release(db, repo.id, item)
        counts[f"releases_{status}"] += 1
    repo.last_synced_at = datetime.now(UTC)
    db.commit()
    documents_indexed = index_repository(db, repo.id)
    bounded = settings.public_analysis_mode and any(
        [
            counts["issues_added"] + counts["issues_updated"] >= issue_limit,
            counts["pull_requests_added"] + counts["pull_requests_updated"] >= pr_limit,
            counts["releases_added"] + counts["releases_updated"] >= release_limit,
        ]
    )
    return {**counts, "documents_indexed": documents_indexed, "duration": round(perf_counter() - start, 3), "bounded_initial_review": bounded}
