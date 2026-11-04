"""Write results/*.json with the metadata needed to reproduce them."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from credit_risk.paths import RAW_DIR, RESULTS, ROOT


def git_commit() -> str:
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return sha + ("-dirty" if dirty else "")


def data_snapshot() -> dict:
    manifest = RAW_DIR / "manifest.json"
    if not manifest.exists():
        return {}
    meta = json.loads(manifest.read_text())
    return {"file": meta["file"], "sha256": meta["sha256"]}


def write_result(
    name: str, payload: dict, config: dict | None = None, seed: int | None = None
) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    out = {
        "meta": {
            "command": " ".join([Path(sys.executable).name, *sys.argv]),
            "git_commit": git_commit(),
            "data_snapshot": data_snapshot(),
            "seed": seed,
            "config": config or {},
            "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        },
        **payload,
    }
    path = RESULTS / f"{name}.json"
    path.write_text(json.dumps(out, indent=2, default=str) + "\n")
    return path
