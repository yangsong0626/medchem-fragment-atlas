from fastapi.testclient import TestClient

from app.main import app


def test_health_smoke():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_fragment_detail_is_json_serializable_when_database_exists():
    client = TestClient(app)
    listing = client.get("/api/fragments?page_size=1")
    if listing.status_code == 503:
        return
    assert listing.status_code == 200
    items = listing.json()["items"]
    if not items:
        return
    detail = client.get(f"/api/fragments/{items[0]['fragment_id']}")
    assert detail.status_code == 200
    assert detail.json()["fragment_id"] == items[0]["fragment_id"]
