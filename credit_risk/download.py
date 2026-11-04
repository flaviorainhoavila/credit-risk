"""Download the Lending Club accepted-loans file from Kaggle and record its checksum.

Source: Kaggle dataset ``wordsforthewise/lending-club`` (Nathan George), file
``accepted_2007_to_2018Q4.csv.gz``. Kaggle serves public datasets without an API
token, so no credentials are needed.

Usage::

    python -m credit_risk.download            # downloads into data/raw/
"""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

DATASET = "wordsforthewise/lending-club"
FILE = "accepted_2007_to_2018Q4.csv.gz"
URL = f"https://www.kaggle.com/api/v1/datasets/download/{DATASET}/{FILE}"
EXPECTED_BYTES = 392_582_231  # from the Kaggle file listing, 2026-11-04


def sha256(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def download(out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / FILE
    if not target.exists() or target.stat().st_size != EXPECTED_BYTES:
        tmp = target.with_suffix(".part")
        urllib.request.urlretrieve(URL, tmp)
        tmp.rename(target)
    size = target.stat().st_size
    if size != EXPECTED_BYTES:
        raise RuntimeError(f"{target}: {size} bytes, expected {EXPECTED_BYTES}")
    meta = {
        "source": f"https://www.kaggle.com/datasets/{DATASET}",
        "file": FILE,
        "bytes": size,
        "sha256": sha256(target),
        "downloaded_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    (out_dir / "manifest.json").write_text(json.dumps(meta, indent=2) + "\n")
    return meta


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("data/raw"))
    meta = download(parser.parse_args().out)
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
