from app.services.fragment_service import compute_descriptors


def test_compute_descriptors_for_aspirin():
    descriptors = compute_descriptors("CC(=O)Oc1ccccc1C(=O)O")
    assert 179 < descriptors["mw"] < 181
    assert descriptors["hbd"] == 1
    assert descriptors["hba"] >= 3
    assert descriptors["ring_count"] == 1
    assert 0 <= descriptors["qed"] <= 1
