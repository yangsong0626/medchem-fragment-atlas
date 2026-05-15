from __future__ import annotations

from rdkit import Chem
from rdkit.Chem import Draw


def smiles_to_svg(smiles: str, width: int = 260, height: int = 180) -> str:
    mol = Chem.MolFromSmiles(smiles, sanitize=True)
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles}")
    drawer = Draw.MolDraw2DSVG(width, height)
    options = drawer.drawOptions()
    options.addAtomIndices = False
    options.bondLineWidth = 1.6
    Draw.rdMolDraw2D.PrepareAndDrawMolecule(drawer, mol)
    drawer.FinishDrawing()
    return drawer.GetDrawingText()
