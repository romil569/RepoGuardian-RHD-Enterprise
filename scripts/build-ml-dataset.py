#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ISSUE_FIELDS = "number,title,body,state,author,labels,createdAt,updatedAt,closedAt,url"
PR_FIELDS = "number,title,body,state,author,createdAt,updatedAt,mergedAt,additions,deletions,changedFiles,url"
RELEASE_FIELDS = "tagName,name,isDraft,isPrerelease,publishedAt,url"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build reproducible public RepoGuardian ML datasets from an allow-list.")
    parser.add_argument("--allow-list", required=True, help="JSON file with {\"repositories\": [\"owner/repo\"]}.")
    parser.add_argument("--output-dir", default="data/ml", help="Directory for JSONL outputs and manifest.")
    parser.add_argument("--limit", type=int, default=200, help="Maximum issues/PRs/releases per repository.")
    parser.add_argument("--dry-run", action="store_true", help="Validate configuration without calling GitHub.")
    return parser.parse_args()


def gh_json(args: list[str]) -> list[dict[str, Any]]:
    completed = subprocess.run(["gh", *args], check=True, capture_output=True, text=True)
    data = json.loads(completed.stdout or "[]")
    return data if isinstance(data, list) else [data]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def repo_rows(repository: str, limit: int) -> dict[str, list[dict[str, Any]]]:
    issues = gh_json(["issue", "list", "--repo", repository, "--state", "all", "--limit", str(limit), "--json", ISSUE_FIELDS])
    prs = gh_json(["pr", "list", "--repo", repository, "--state", "all", "--limit", str(limit), "--json", PR_FIELDS])
    releases = gh_json(["release", "list", "--repo", repository, "--limit", str(limit), "--json", RELEASE_FIELDS])
    for collection, kind in [(issues, "issue"), (prs, "pull_request"), (releases, "release")]:
        for row in collection:
            row["repository"] = repository
            row["record_type"] = kind
            row["collection_basis"] = "public GitHub API via gh CLI"
    return {"issues": issues, "pull_requests": prs, "releases": releases}


def main() -> None:
    args = parse_args()
    config_path = Path(args.allow_list)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    repositories = config.get("repositories", [])
    if not repositories or not all(isinstance(item, str) and "/" in item for item in repositories):
        raise SystemExit("Allow-list must contain owner/repo entries.")
    if args.dry_run:
        print(json.dumps({"status": "DRY_RUN_OK", "repositories": repositories, "limit": args.limit}, indent=2))
        return

    output = Path(args.output_dir)
    manifest: dict[str, Any] = {
        "dataset_version": datetime.now(UTC).strftime("public-github-%Y%m%dT%H%M%SZ"),
        "collection_timestamp": datetime.now(UTC).isoformat(),
        "allow_list": repositories,
        "rows": {},
        "quality_rules": [
            "Only configured public repositories are collected.",
            "Temporal splits are required before training.",
            "Repository-specific label semantics must be documented before priority training.",
            "Weak PR risk labels must keep risk_label_source.",
        ],
    }
    all_rows = {"issues": [], "pull_requests": [], "releases": []}
    for repository in repositories:
        rows = repo_rows(repository, args.limit)
        manifest["rows"][repository] = {name: len(values) for name, values in rows.items()}
        for name, values in rows.items():
            all_rows[name].extend(values)

    for name, rows in all_rows.items():
        write_jsonl(output / f"{name}.jsonl", rows)
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": "DATASET_COLLECTED", "manifest": str(output / "manifest.json"), "rows": manifest["rows"]}, indent=2))


if __name__ == "__main__":
    main()
