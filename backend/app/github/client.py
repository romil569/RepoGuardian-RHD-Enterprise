from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

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


@dataclass(frozen=True)
class GitHubRestService:
    api_base: str = "https://api.github.com"

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "RepoGuardian-RHD"}
        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token}"
        return headers

    def _request(self, path: str, timeout: int = 30) -> Any:
        request = Request(f"{self.api_base.rstrip('/')}{path}", headers=self._headers())
        try:
            with urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code in {401, 403}:
                raise GitHubAuthenticationError("GitHub API authentication or rate limit blocked the request") from exc
            if exc.code == 404:
                raise GitHubNotFoundError("Repository not found")
            raise GitHubServiceError(f"GitHub API failed with HTTP {exc.code}") from exc
        except (URLError, TimeoutError) as exc:
            raise GitHubServiceError("GitHub API request failed") from exc

    def get_repository(self, full_name: str) -> dict[str, Any]:
        item = self._request(f"/repos/{quote(full_name, safe='/')}")
        return {
            "id": item.get("id"),
            "owner": {"login": (item.get("owner") or {}).get("login")},
            "name": item.get("name"),
            "nameWithOwner": item.get("full_name"),
            "description": item.get("description"),
            "url": item.get("html_url"),
            "defaultBranchRef": {"name": item.get("default_branch")},
            "primaryLanguage": {"name": item.get("language")} if item.get("language") else None,
            "stargazerCount": item.get("stargazers_count") or 0,
            "createdAt": item.get("created_at"),
            "updatedAt": item.get("updated_at"),
        }

    def get_repository_issues(self, full_name: str, state: str = "all", limit: int = 100) -> list[dict[str, Any]]:
        rows = self._request(f"/repos/{quote(full_name, safe='/')}/issues?state={state}&per_page={min(limit, 100)}") or []
        return [
            {
                "id": item.get("id"),
                "number": item.get("number"),
                "title": item.get("title"),
                "body": item.get("body"),
                "state": str(item.get("state", "")).upper(),
                "author": {"login": (item.get("user") or {}).get("login")},
                "labels": [{"name": label.get("name")} for label in item.get("labels", [])],
                "url": item.get("html_url"),
                "createdAt": item.get("created_at"),
                "updatedAt": item.get("updated_at"),
                "closedAt": item.get("closed_at"),
            }
            for item in rows
            if "pull_request" not in item
        ]

    def get_issue_comments(self, full_name: str, number: int) -> list[dict[str, Any]]:
        rows = self._request(f"/repos/{quote(full_name, safe='/')}/issues/{number}/comments?per_page=30") or []
        return [
            {
                "id": item.get("id"),
                "user": (item.get("user") or {}).get("login"),
                "body": item.get("body"),
                "html_url": item.get("html_url"),
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
            }
            for item in rows
        ]

    def get_pull_requests(self, full_name: str, state: str = "all", limit: int = 100) -> list[dict[str, Any]]:
        rows = self._request(f"/repos/{quote(full_name, safe='/')}/pulls?state={state}&per_page={min(limit, 100)}") or []
        return [
            {
                "id": item.get("id"),
                "number": item.get("number"),
                "title": item.get("title"),
                "body": item.get("body"),
                "state": str(item.get("state", "")).upper(),
                "author": {"login": (item.get("user") or {}).get("login")},
                "url": item.get("html_url"),
                "createdAt": item.get("created_at"),
                "updatedAt": item.get("updated_at"),
                "mergedAt": item.get("merged_at"),
            }
            for item in rows
        ]

    def get_releases(self, full_name: str, limit: int = 30) -> list[dict[str, Any]]:
        rows = self._request(f"/repos/{quote(full_name, safe='/')}/releases?per_page={min(limit, 100)}") or []
        return [
            {
                "id": item.get("id"),
                "tagName": item.get("tag_name"),
                "name": item.get("name"),
                "body": item.get("body"),
                "url": item.get("html_url"),
                "publishedAt": item.get("published_at"),
            }
            for item in rows[:limit]
        ]

    def get_issue(self, full_name: str, number: int) -> dict[str, Any]:
        item = self._request(f"/repos/{quote(full_name, safe='/')}/issues/{number}")
        return {
            "id": item.get("id"),
            "number": item.get("number"),
            "title": item.get("title"),
            "body": item.get("body"),
            "state": str(item.get("state", "")).upper(),
            "author": {"login": (item.get("user") or {}).get("login")},
            "labels": [{"name": label.get("name")} for label in item.get("labels", [])],
            "url": item.get("html_url"),
            "createdAt": item.get("created_at"),
            "updatedAt": item.get("updated_at"),
            "closedAt": item.get("closed_at"),
        }

    def get_pull_request(self, full_name: str, number: int) -> dict[str, Any]:
        rows = [item for item in self.get_pull_requests(full_name, limit=100) if int(item.get("number", 0)) == number]
        if not rows:
            raise GitHubNotFoundError("Pull request not found")
        return rows[0]

    def get_label(self, full_name: str, label: str) -> dict[str, Any]:
        return self._request(f"/repos/{quote(full_name, safe='/')}/labels/{quote(label, safe='')}")

    def add_issue_label(self, full_name: str, number: int, label: str) -> dict[str, Any]:
        raise GitHubServiceError("REST public analysis client does not execute write actions")

    def post_issue_comment(self, full_name: str, number: int, body: str) -> dict[str, Any]:
        raise GitHubServiceError("REST public analysis client does not execute write actions")


def github_service() -> GitHubCliService | GitHubRestService:
    if settings.public_analysis_mode:
        return GitHubRestService()
    try:
        GitHubCliService()._gh()
        return GitHubCliService()
    except GitHubServiceError:
        return GitHubRestService()
