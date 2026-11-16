"""HTTP contract checks: geometry and unambiguous failure behavior."""
import pytest
from fastapi.testclient import TestClient
from anais_lunarnav.api import app

client = TestClient(app)
SITE = {"latitude_deg": -89.5, "longitude_deg": 0, "observer_height_m": 2}

def test_health_not_scientific_readiness(monkeypatch):
    monkeypatch.delenv("LUNARNAV_KERNEL_PATHS", raising=False)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["scientific_kernels_configured"] is False

def test_reference_cartesian():
    response = client.post("/v1/coordinates/cartesian", json={"latitude_deg": 0, "longitude_deg": 0, "observer_height_m": 0})
    assert response.status_code == 200
    assert response.json()["cartesian_km"] == pytest.approx([1737.4, 0, 0])

def test_round_trip():
    cart = client.post("/v1/coordinates/cartesian", json=SITE).json()["cartesian_km"]
    response = client.post("/v1/coordinates/surface", json=dict(zip(("x_km", "y_km", "z_km"), cart)))
    assert response.status_code == 200
    assert response.json()["latitude_deg"] == pytest.approx(SITE["latitude_deg"])
    assert response.json()["observer_height_m"] == pytest.approx(2, abs=1e-6)

def test_reject_invalid_coordinates():
    assert client.post("/v1/coordinates/cartesian", json={**SITE, "latitude_deg": 91}).status_code == 422
    assert client.post("/v1/coordinates/cartesian", json={**SITE, "latitude_deg": "NaN"}).status_code == 422
    assert client.post("/v1/coordinates/surface", json={"x_km": 0, "y_km": 0, "z_km": 0}).status_code == 422

def test_time_requires_timezone():
    response = client.post("/v1/analysis/instant", json={"site": SITE, "observation_utc": "2026-11-14T12:00:00"})
    assert response.status_code == 422

def test_missing_kernels_no_fabricated_data(monkeypatch):
    monkeypatch.delenv("LUNARNAV_KERNEL_PATHS", raising=False)
    payload = {"site": SITE, "observation_utc": "2026-11-14T12:00:00Z"}
    response = client.post("/v1/analysis/instant", json=payload)
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "KERNELS_NOT_CONFIGURED"
    assert "sites" not in response.json()

def test_comparison_requires_real_kernels(monkeypatch):
    monkeypatch.delenv("LUNARNAV_KERNEL_PATHS", raising=False)
    response = client.post("/v1/analysis/compare-instant", json={"site_alpha": SITE, "site_bravo": SITE, "observation_utc": "2026-11-14T12:00:00Z"})
    assert response.status_code == 503
