# ANAIS LunarNav — Engineering Change Control Review Packet
Document: ANAIS-LL-LNAV-021-CCR-001
Date: 2026-11-16 | Version 0.1 | Status: Committee review pending
Organization: Aegis Air Intelligence Systems LLC / ANAIS Technology LLC
Classification: Proprietary — Engineering Research

## Scope / change register
- Commit 4aecb963f39907da04d7c84fcc38e89f19173717: FastAPI scientific contract, validated coordinate endpoints, explicit failures without kernels, Python HTTP tests, JUnit-producing CI.
- This revision: kernel-backed, time-scoped Sun/Earth geometry checks (Nov 14–15, 2026); NAIF LSK, DE440s SPK, generic text PCK; automated JSON evidence with digests; review record.
- No terrain-aware analysis, observation-window aggregation, high-accuracy lunar frame conversion, navigation safety validation, UI or deployment is claimed.

## Review committee — proposed roles (not appointed)
- Science / ephemeris reviewer: verify SPK, lunar frame, model and independent references.
- Software reviewer: verify API boundaries, error contracts and deterministic behavior.
- QA reviewer: inspect run ID, evidence file, missing checks and reproducibility.
- Release authority: decide G1/G2/G3/API-021 based on reviewed evidence.

## Decision rules
A committee has **not convened**, no reviewers have signed, and no acceptance approval is implied by this packet.
- Existing GitHub API and scientific CI at baseline commit: PASS.
- Kernel-backed coverage sample run: PENDING until CI run completes and evidence is inspected.
- Numerical accuracy agreement to independent DE440 reference positions: NOT ASSESSED by this coverage workflow.
- MOON_ME high-accuracy frame conversion: NOT IMPLEMENTED. Existing IAU_MOON frame remains an approximate reference.
- API acceptance: HOLD. Conditional release can be considered only with documented research-only limitations.
- Later G4–G10: OPEN.

## Kernel and model assumptions
The NAIF generic kernel sources are:
https://naif.jpl.nasa.gov/pub/naif/generic_kernels/lsk/naif0012.tls
https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de440s.bsp
https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/pck00011.tpc

The workflow records hashes after downloading; these hashes are **not** independently pinned against a trusted expected checksum. Only sample timestamps and two selected locations are exercised. To certify uninterrupted ephemeris availability across every timestamp in an interval requires separate SPK segment coverage inspection and frame coverage verification. This workflow is a runtime smoke test, not complete scientific coverage proof.

NASA/JPL NAIF notes that IAU_MOON is not the preferred high-accuracy lunar orientation; MOON_ME requires compatible lunar binary PCK and FK. Future upgrade must explicitly separate these conventions and validate their transform.

## Acceptance record
Decision: HOLD — pending independent scientific verification and formal release review.
Approved by: NOBODY YET.
Date of approval: NOT APPLICABLE.

---
Property of Aegis Air Intelligence Systems LLC & ANAIS Technology LLC
Prepared under the direction of Edward Guillen Morejon, Founder & CEO
© 2025 Aegis Air Intelligence Systems LLC & ANAIS Technology LLC. All Rights Reserved.
Controlled Distribution • Access Logged • Unauthorized Disclosure Prohibited

Distribution and access-logging notices do not constitute proof of implemented controls.
