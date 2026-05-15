#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))
from app.services.fragment_service import add_missing_descriptors

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute missing RDKit parent-molecule descriptors.")
    parser.add_argument("--input", type=Path, default=ROOT / "data/processed/molecules.parquet")
    parser.add_argument("--output", type=Path, default=ROOT / "data/derived/molecules_with_descriptors.parquet")
    args = parser.parse_args()

    molecules = pd.read_parquet(args.input)
    enriched = add_missing_descriptors(molecules)
    valid = enriched[enriched["descriptor_failure"].isna()].copy()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    valid.to_parquet(args.output, index=False)
    failures = enriched[enriched["descriptor_failure"].notna()]
    if not failures.empty:
        failures.to_csv(args.output.with_suffix(".failures.csv"), index=False)
    print(f"Wrote {len(valid):,} molecules with descriptors to {args.output}")


if __name__ == "__main__":
    main()
