# ANAIS-LL-LNAV-021 — Evidence and Acceptance Register

Date: 2026-11-16. Version 0.2. Classification: Proprietary — Engineering Research.
Organization: Aegis Air Intelligence Systems LLC / ANAIS Technology LLC.

## Scope
Preserved the existing scientific Python core. Added a FastAPI contract for health, spherical coordinates, instantaneous geometric Sun/Earth visibility and two-site same-epoch comparison. Scientific calculations stay on the backend.

## Local use
```sh
python -m pip install -e '.[api,test]'
uvicorn anais_lunarnav.api:app --host 127.0.0.1 --port 8000
python -m pytest
```
Open /docs for the generated OpenAPI interface. Example POST /v1/analysis/instant:
```json
{"site":{"latitude_deg":-89.5,"longitude_deg":0,"observer_height_m":2},"observation_utc":"2026-11-14T12:00:00Z","reference_frame":"IAU_MOON"}
```
To execute scientific ephemerides, set LUNARNAV_KERNEL_PATHS to a platform-path-separated list of validated LSK, SPK and lunar PCK files. Only operator-controlled file paths are accepted; kernels are never silently downloaded. On missing inputs a structured 503 is returned, not fabricated measurements. Path existence does not prove ephemeris coverage.

## Scientific limitations
IAU_MOON is explicitly used; MOON_ME is not silently substituted. Mean-sphere (1737.4 km), planetocentric/east-positive geometry, no terrain ray tracing, finite-body disk, aberration correction or certification. Output is research-only and not suitable for navigation or landing decisions.

## Three mandatory deliverables
1. **Software:** implementation in src/anais_lunarnav/api.py, dependency manifest and automated CI workflow.
2. **Objective evidence:** tests/test_api.py plus existing scientific tests; GitHub Actions uploads JUnit XML when executed. Verify run ID, commit and tests before citing CI as proof.
3. **Acceptance decision:** G1, G2, G3, API-021 remain **OPEN** until actual CI, startup and independently verified scientific fixtures are reviewed. G4–G10 not assessed. Commit != acceptance.

## Release restrictions
Do not merge or call the system scientifically validated until tests run and reference tolerances are documented. Do not interpret a responsive /health as scientific readiness. There is no production hosting in this milestone.

---
Property of Aegis Air Intelligence Systems LLC & ANAIS Technology LLC
Prepared under the direction of Edward Guillen Morejon, Founder & CEO
© 2025 Aegis Air Intelligence Systems LLC & ANAIS Technology LLC. All Rights Reserved.
Controlled Distribution • Access Logged • Unauthorized Disclosure Prohibited

The controlled-distribution footer is a notice, not evidence of implemented access logging.
