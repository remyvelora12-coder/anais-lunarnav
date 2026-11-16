"""Execute kernel-backed lunar visibility checks and write inspectable evidence."""
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from anais_lunarnav.api import app

SAMPLES = ("2026-11-14T00:00:00Z", "2026-11-14T12:00:00Z",
           "2026-11-15T00:00:00Z", "2026-11-15T23:59:00Z")
KERNELS = [Path(path) for path in os.environ.get("LUNARNAV_KERNEL_PATHS", "").split(os.pathsep) if path]

def main():
    if len(KERNELS) < 3 or not all(path.is_file() for path in KERNELS):
        raise SystemExit("FAIL: LSK, SPK and PCK kernel files are required.")
    client = TestClient(app)
    site_a = {"latitude_deg": -89.5, "longitude_deg": 0.0, "observer_height_m": 2.0}
    site_b = {"latitude_deg": -88.5, "longitude_deg": 45.0, "observer_height_m": 2.0}
    executions = []
    failures = []
    for timestamp in SAMPLES:
        response = client.post("/v1/analysis/compare-instant", json={
            "site_alpha": site_a, "site_bravo": site_b,
            "observation_utc": timestamp, "reference_frame": "IAU_MOON"
        })
        if response.status_code != 200:
            failures.append({"timestamp": timestamp, "http_status": response.status_code,
                             "error": response.json()})
            continue
        data = response.json()
        try:
            assert data["calculation_status"] == "EXECUTED"
            assert data["reference_frame"] == "IAU_MOON"
            assert data["aberration_correction"] == "NONE"
            for site in ("alpha", "bravo"):
                for body in ("sun", "earth"):
                    outcome = data["sites"][site][body]
                    assert -90 <= outcome["elevation_deg"] <= 90
                    assert outcome["range_km"] > 0
                    assert isinstance(outcome["visible_geometric_center"], bool)
            executions.append({"timestamp": timestamp, "status": "PASS",
                               "et_seconds": data["et_seconds_past_j2000_tdb"],
                               "sites": data["sites"]})
        except (AssertionError, KeyError, TypeError) as exc:
            failures.append({"timestamp": timestamp, "http_status": response.status_code,
                             "error": repr(exc)})
    evidence = {
        "schema_version": 1,
        "document_id": "ANAIS-LL-LNAV-021",
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_commit": os.environ.get("GITHUB_SHA"),
        "model": "IAU_MOON geometric / mean sphere",
        "sample_window_utc": [SAMPLES[0], SAMPLES[-1]],
        "checks": "Actual SPICE UTC-to-ET, Sun/Earth observer geometry, API two-site response; samples only",
        "independent_accuracy_validation": "NOT_PERFORMED",
        "terrain_validation": "NOT_PERFORMED",
        "kernels": [{"filename": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "bytes": path.stat().st_size} for path in KERNELS],
        "passed_samples": executions, "failed_samples": failures,
        "status": "PASS" if len(executions) == len(SAMPLES) and not failures else "FAIL"
    }
    output = Path("evidence/scientific/kernel-coverage-2026-11-14_15.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": evidence["status"], "samples_passed": len(executions),
                      "samples_failed": len(failures), "evidence": str(output)}))
    if evidence["status"] != "PASS":
        raise SystemExit(1)

if __name__ == "__main__":
    main()
