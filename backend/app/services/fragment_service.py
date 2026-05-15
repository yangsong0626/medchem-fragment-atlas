from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from statistics import median
from typing import Any

import pandas as pd
from rdkit import Chem
from rdkit.Chem import BRICS, Crippen, Descriptors, Lipinski, QED, rdMolDescriptors

PROPERTY_COLUMNS = ["mw", "clogp", "tpsa", "hbd", "hba", "rotb", "ring_count", "aromatic_ring_count", "fsp3", "qed"]


@dataclass(frozen=True)
class FragmentRecord:
    fragment_id: str
    fragment_smiles: str
    display_smiles: str
    heavy_atom_count: int
    mw: float
    clogp: float
    tpsa: float
    hbd: int
    hba: int
    rotb: int
    ring_count: int
    aromatic_ring_count: int
    fsp3: float
    qed: float


def stable_id(value: str, prefix: str) -> str:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def mol_from_smiles(smiles: str) -> Chem.Mol:
    mol = Chem.MolFromSmiles(smiles, sanitize=True)
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles}")
    Chem.SanitizeMol(mol)
    return mol


def canonicalize_smiles(smiles: str, keep_dummy_labels: bool = True) -> str:
    mol = mol_from_smiles(smiles)
    if keep_dummy_labels:
        return Chem.MolToSmiles(mol, canonical=True, isomericSmiles=True)
    for atom in mol.GetAtoms():
        if atom.GetAtomicNum() == 0:
            atom.SetIsotope(0)
            atom.SetAtomMapNum(0)
    return Chem.MolToSmiles(mol, canonical=True, isomericSmiles=True)


def normalize_dummy_labels(smiles: str) -> str:
    """Normalize BRICS dummy labels for display while preserving attachment sites."""
    return re.sub(r"\[(?:\d+\*)\]", "[*]", smiles)


def compute_descriptors(smiles: str) -> dict[str, float | int]:
    mol = mol_from_smiles(smiles)
    return {
        "mw": float(Descriptors.MolWt(mol)),
        "clogp": float(Crippen.MolLogP(mol)),
        "tpsa": float(rdMolDescriptors.CalcTPSA(mol)),
        "hbd": int(Lipinski.NumHDonors(mol)),
        "hba": int(Lipinski.NumHAcceptors(mol)),
        "rotb": int(Lipinski.NumRotatableBonds(mol)),
        "ring_count": int(rdMolDescriptors.CalcNumRings(mol)),
        "aromatic_ring_count": int(rdMolDescriptors.CalcNumAromaticRings(mol)),
        "fsp3": float(rdMolDescriptors.CalcFractionCSP3(mol)),
        "qed": float(QED.qed(mol)),
    }


def decompose_brics(smiles: str, min_heavy_atoms: int = 3) -> list[FragmentRecord]:
    mol = mol_from_smiles(smiles)
    raw_fragments = BRICS.BRICSDecompose(mol, returnMols=False, keepNonLeafNodes=False)
    records: list[FragmentRecord] = []
    for raw in raw_fragments:
        fragment_smiles = canonicalize_smiles(raw, keep_dummy_labels=True)
        frag_mol = mol_from_smiles(fragment_smiles)
        heavy_atoms = int(frag_mol.GetNumHeavyAtoms())
        if heavy_atoms < min_heavy_atoms:
            continue
        descriptors = compute_descriptors(fragment_smiles)
        records.append(
            FragmentRecord(
                fragment_id=stable_id(fragment_smiles, "frag"),
                fragment_smiles=fragment_smiles,
                display_smiles=normalize_dummy_labels(fragment_smiles),
                heavy_atom_count=heavy_atoms,
                **descriptors,
            )
        )
    return sorted({record.fragment_smiles: record for record in records}.values(), key=lambda r: r.fragment_smiles)


def add_missing_descriptors(df: pd.DataFrame, smiles_col: str = "canonical_smiles") -> pd.DataFrame:
    out = df.copy()
    for col in PROPERTY_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA

    rows: list[dict[str, Any]] = []
    failures: list[str | None] = []
    for _, row in out.iterrows():
        values = row.to_dict()
        try:
            descriptors = compute_descriptors(str(row[smiles_col]))
            for col, value in descriptors.items():
                if pd.isna(values.get(col)):
                    values[col] = value
            failures.append(None)
        except Exception as exc:
            failures.append(str(exc))
        rows.append(values)
    result = pd.DataFrame(rows)
    result["descriptor_failure"] = failures
    return result


def aggregate_property(values: pd.Series) -> dict[str, float | None]:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if clean.empty:
        return {"mean": None, "median": None, "std": None, "p10": None, "p90": None}
    return {
        "mean": float(clean.mean()),
        "median": float(median(clean.tolist())),
        "std": float(clean.std(ddof=0)),
        "p10": float(clean.quantile(0.10)),
        "p90": float(clean.quantile(0.90)),
    }
