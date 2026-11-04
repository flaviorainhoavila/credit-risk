"""Write results/*.json with the metadata needed to reproduce them."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from credit_risk.paths import RAW_DIR, RESULTS, ROOT

OUTPUT_PATHS = ("results", "figures", "README.md")


def git_commit() -> str:
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = subprocess.run(
            # Generated outputs do not make the code dirty.
            ["git", "status", "--porcelain", "--untracked-files=no", "--", "."]
            + [f":!{p}" for p in OUTPUT_PATHS],
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


def command_line() -> str:
    """The command that is running, as typed: ``python -m pkg.mod args`` for modules."""
    main = sys.modules.get("__main__")
    spec = getattr(main, "__spec__", None)
    if spec is not None and spec.name:
        return " ".join(["python", "-m", spec.name, *sys.argv[1:]])
    return " ".join(["python", *sys.argv])


def write_result(
    name: str, payload: dict, config: dict | None = None, seed: int | None = None
) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    out = {
        "meta": {
            "command": command_line(),
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
