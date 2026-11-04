"""Filesystem locations shared by the pipeline scripts."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW_DIR = DATA / "raw"
WAREHOUSE = DATA / "warehouse.duckdb"
RESULTS = ROOT / "results"
