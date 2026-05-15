from app.services.fragment_service import decompose_brics, normalize_dummy_labels


def test_brics_decomposition_keeps_dummy_labels():
    fragments = decompose_brics("CC(=O)Oc1ccccc1C(=O)O")
    assert fragments
    assert any("*" in fragment.fragment_smiles for fragment in fragments)
    assert all(fragment.heavy_atom_count >= 3 for fragment in fragments)


def test_display_smiles_normalizes_brics_labels():
    assert normalize_dummy_labels("[16*]c1ccccc1[16*]") == "[*]c1ccccc1[*]"
