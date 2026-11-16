from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from anais_lunarnav.api import app
from anais_lunarnav.timeline import Sample, sample_times, summarize

BASE = datetime(2026, 11, 14, tzinfo=timezone.utc)
SITE = {"latitude_deg": -89.5, "longitude_deg": 0, "observer_height_m": 2}

def test_sampling_includes_exact_end_even_when_not_multiple():
    result = sample_times(BASE, BASE + timedelta(hours=2, minutes=5), 3600)
    assert len(result) == 4
    assert result[-1] == BASE + timedelta(hours=2, minutes=5)

@pytest.mark.parametrize("seconds", [0, 899, 21601, True])
def test_sampling_rejects_invalid_step(seconds):
    with pytest.raises(ValueError):
        sample_times(BASE, BASE + timedelta(hours=2), seconds)

def test_sampling_rejects_bad_window():
    for end in (BASE, BASE - timedelta(seconds=1), BASE + timedelta(days=3)):
        with pytest.raises(ValueError):
            sample_times(BASE, end, 3600)
    with pytest.raises(ValueError):
        sample_times(BASE.replace(tzinfo=None), BASE + timedelta(hours=1), 3600)

def test_summary_unknown_not_fabricated():
    values = [Sample(BASE, True, None), Sample(BASE + timedelta(hours=1), None, False)]
    x = summarize(values, "solar_visible")
    assert x["known_sample_count"] == 1
    assert x["unknown_sample_count"] == 1
    assert x["continuous_visibility_duration_seconds"] is None
    assert x["transition_brackets"] == []

def test_transition_is_bounded_not_interpolated():
    values = [Sample(BASE, True, True), Sample(BASE + timedelta(hours=1), False, True)]
    x = summarize(values, "solar_visible")
    assert x["visible_sample_fraction"] == 0.5
    assert len(x["transition_brackets"]) == 1
    assert x["transition_brackets"][0]["end_utc"] == values[1].utc.isoformat()

def test_comparison_fails_closed_without_kernels(monkeypatch):
    monkeypatch.delenv("LUNARNAV_KERNEL_PATHS", raising=False)
    client = TestClient(app)
    response = client.post("/v1/analysis/compare-window", json={
        "site_alpha": SITE, "site_bravo": SITE,
        "start_utc": "2026-11-14T00:00:00Z", "end_utc": "2026-11-15T00:00:00Z",
        "sample_interval_seconds": 3600
    })
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "KERNELS_UNAVAILABLE"

def test_comparison_rejects_naive_time():
    client = TestClient(app)
    response = client.post("/v1/analysis/compare-window", json={
        "site_alpha": SITE, "site_bravo": SITE,
        "start_utc": "2026-11-14T00:00:00", "end_utc": "2026-11-15T00:00:00Z",
        "sample_interval_seconds": 3600
    })
    assert response.status_code == 422
