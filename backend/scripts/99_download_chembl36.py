#!/usr/bin/env python
from __future__ import annotations

import argparse
import shutil
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHEMBL36_URL = "https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_36/chembl_36_sqlite.tar.gz"


def main() -> None:
    parser = argparse.ArgumentParser(description="Download and unpack the official ChEMBL 36 SQLite release.")
    parser.add_argument("--url", default=CHEMBL36_URL)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/raw/chembl_36")
    parser.add_argument("--link-path", type=Path, default=ROOT / "data/raw/chembl_36/chembl_36.db")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    archive = args.output_dir / "chembl_36_sqlite.tar.gz"
    if not archive.exists():
        with urllib.request.urlopen(args.url) as response, archive.open("wb") as handle:
            shutil.copyfileobj(response, handle)
    with tarfile.open(archive) as tar:
        tar.extractall(args.output_dir, filter="data")

    sqlite_paths = sorted(args.output_dir.rglob("chembl_36_sqlite/chembl_36.db")) or sorted(args.output_dir.rglob("*.db"))
    if not sqlite_paths:
        raise FileNotFoundError(f"No ChEMBL SQLite database found under {args.output_dir}")
    db_path = sqlite_paths[0]
    if args.link_path.exists() or args.link_path.is_symlink():
        args.link_path.unlink()
    args.link_path.symlink_to(db_path)
    print(args.link_path)


if __name__ == "__main__":
    main()
