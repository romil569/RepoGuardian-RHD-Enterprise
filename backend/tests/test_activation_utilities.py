from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from app.api.routes import platform
from app.core.config import settings


ROOT = Path(__file__).resolve().parents[2]


def load_script(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_code_scan_path_policy_allows_configured_root(tmp_path, monkeypatch):
    allowed = tmp_path / "allowed"
    blocked = tmp_path / "blocked"
    allowed.mkdir()
    blocked.mkdir()
    monkeypatch.setattr(settings, "code_scan_allowed_roots", str(allowed))
    assert platform._code_path_allowed(allowed)
    assert platform._code_path_allowed(allowed / "nested")
    assert not platform._code_path_allowed(blocked)


def test_ml_dataset_builder_dry_run_uses_allow_list(tmp_path):
    config = tmp_path / "repos.json"
    config.write_text(json.dumps({"repositories": ["owner/repo"]}), encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build-ml-dataset.py"), "--allow-list", str(config), "--dry-run"],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["status"] == "DRY_RUN_OK"
    assert payload["repositories"] == ["owner/repo"]


def test_migration_tool_rejects_non_postgres_destination(tmp_path):
    source = tmp_path / "source.db"
    source.write_bytes(b"")
    module = load_script(ROOT / "scripts" / "migrate-sqlite-to-postgres.py")
    try:
        module.destination_engine("sqlite:///not-postgres.db")
    except SystemExit as exc:
        assert "PostgreSQL" in str(exc)
    else:
        raise AssertionError("expected non-PostgreSQL destination to be rejected")
