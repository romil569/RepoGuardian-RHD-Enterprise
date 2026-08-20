from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import settings


class GitHubServiceError(RuntimeError):
    pass


class GitHubAuthenticationError(GitHubServiceError):
    pass


class GitHubNotFoundError(GitHubServiceError):
    pass


@dataclass(frozen=True)
class GitHubCliService:
    repo: str | None = None

    def _gh(self) -> str:
        if settings.github_cli_path:
            return settings.github_cli_path
        found = shutil.which("gh")
        if found:
            return found
        fallback = Path("C:/Program Files/GitHub CLI/gh.exe")
        if fallback.exists():
            return str(fallback)
        raise GitHubServiceError("GitHub CLI is not available")

    def _run(self, args: list[str], timeout: int = 30) -> Any:
        command = [self._gh(), *args]
        try:
            result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, check=False)
        except subprocess.TimeoutExpired as exc:
            raise GitHubServiceError("GitHub request timed out") from exc
        if result.returncode != 0:
            message = (result.stderr or result.stdout or "GitHub CLI command failed").strip()
            lowered = message.lower()
            if "not logged into" in lowered or "authentication" in lowered:
                raise GitHubAuthenticationError(message)
            if "not found" in lowered or "could not resolve" in lowered:
                raise GitHubNotFoundError(message)
            raise GitHubServiceError(message)
        output = result.stdout.strip()
        if not output:
            return None
        try:
            return json.loads(output)
        except json.JSONDecodeError as exc:
            raise GitHubServiceError("Malformed GitHub response") from exc

    def get_repository(self, full_name: str) -> dict[str, Any]:
        return self._run(
            [
                "repo",
                "view",
                full_name,
                "--json",
                "id,name,owner,nameWithOwner,description,url,defaultBranchRef,primaryLanguage,stargazerCount,createdAt,updatedAt",
            ]
        )

    def get_repository_issues(self, full_name: str, state: str = "all", limit: int = 100) -> list[dict[str, Any]]:
        return self._run(
            [
                "issue",
                "list",
                "--repo",
                full_name,
                "--state",
                state,
                "--limit",
                str(limit),
                "--json",
                "id,number,title,body,state,author,labels,url,createdAt,updatedAt,closedAt",
            ]
        ) or []

    def get_issue(self, full_name: str, number: int) -> dict[str, Any]:
        return self._run(
            [
                "issue",
                "view",
                str(number),
                "--repo",
                full_name,
                "--json",
                "id,number,title,body,state,author,labels,url,createdAt,updatedAt,closedAt",
            ]
        )

    def get_issue_comments(self, full_name: str, number: int) -> list[dict[str, Any]]:
        return self._run(
            [
                "api",
                f"repos/{full_name}/issues/{number}/comments",
                "--paginate",
                "--jq",
                "[.[] | {id, user: .user.login, body, html_url, created_at, updated_at}]",
            ]
        ) or []

    def get_label(self, full_name: str, label: str) -> dict[str, Any]:
        return self._run(["api", f"repos/{full_name}/labels/{label}"])

    def add_issue_label(self, full_name: str, number: int, label: str) -> dict[str, Any]:
        return self._run(
            [
                "api",
                f"repos/{full_name}/issues/{number}/labels",
                "-X",
                "POST",
                "-f",
                f"labels[]={label}",
            ]
        )

    def post_issue_comment(self, full_name: str, number: int, body: str) -> dict[str, Any]:
        return self._run(
            [
                "api",
                f"repos/{full_name}/issues/{number}/comments",
                "-f",
                f"body={body}",
                "--jq",
                "{id,html_url,body}",
            ]
        )

    def get_pull_requests(self, full_name: str, state: str = "all", limit: int = 100) -> list[dict[str, Any]]:
        return self._run(
            [
                "pr",
                "list",
                "--repo",
                full_name,
                "--state",
                state,
                "--limit",
                str(limit),
                "--json",
                "id,number,title,body,state,author,url,createdAt,updatedAt,mergedAt",
            ]
        ) or []

    def get_pull_request(self, full_name: str, number: int) -> dict[str, Any]:
        return self._run(
            [
                "pr",
                "view",
                str(number),
                "--repo",
                full_name,
                "--json",
                "id,number,title,body,state,author,url,createdAt,updatedAt,mergedAt",
            ]
        )

    def get_releases(self, full_name: str, limit: int = 30) -> list[dict[str, Any]]:
        releases = self._run(
            [
                "api",
                f"repos/{full_name}/releases?per_page={limit}",
                "--jq",
                "[.[] | {id, tagName: .tag_name, name, body, url: .html_url, publishedAt: .published_at}]",
            ]
        ) or []
        return releases[:limit]

    def search_issues(self, full_name: str, query: str, limit: int = 20) -> list[dict[str, Any]]:
        return self._run(
            [
                "search",
                "issues",
                f"{query} repo:{full_name} type:issue",
                "--limit",
                str(limit),
                "--json",
                "number,title,state,url,body,labels",
            ]
        ) or []

    def search_pull_requests(self, full_name: str, query: str, limit: int = 20) -> list[dict[str, Any]]:
        return self._run(
            [
                "search",
                "prs",
                f"{query} repo:{full_name}",
                "--limit",
                str(limit),
                "--json",
                "number,title,state,url,body",
            ]
        ) or []
