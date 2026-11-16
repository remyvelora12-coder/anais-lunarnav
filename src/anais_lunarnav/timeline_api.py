"""Bounded sample-based two-site comparison API (no terrain, no interval certification)."""
from datetime import datetime
from pathlib import Path
from typing import Literal

from fastapi import HTTPException
from pydantic import Field, model_validator
from .api import StrictModel, Site, FRAME, app, configured_kernels, _SPICE_LOCK, _site_geometry
from .provenance import load_kernels
from .time import utc_to_et
from .timeline import Sample, sample_times, summarize

class WindowRequest(StrictModel):
    site_alpha: Site
    site_bravo: Site
    start_utc: datetime
    end_utc: datetime
    sample_interval_seconds: int = Field(default=3600, ge=900, le=21600)
    reference_frame: Literal["IAU_MOON"] = FRAME

    @model_validator(mode="after")
    def validate_window(self):
        sample_times(self.start_utc, self.end_utc, self.sample_interval_seconds)
        return self

@app.post("/v1/analysis/compare-window")
def compare_window(request: WindowRequest):
    """Scientific SPICE snapshots; no inferred visibility intervals or durations."""
    paths = configured_kernels()
    if len(paths) < 3 or not all(Path(p).is_file() for p in paths):
        raise HTTPException(503, detail={"code": "KERNELS_UNAVAILABLE", "message": "Provide validated LSK, SPK and lunar orientation kernels."})
    if not _SPICE_LOCK.acquire(blocking=False):
        raise HTTPException(503, detail={"code": "SPICE_BUSY", "message": "Another analysis is executing."})
    try:
        import spiceypy
        if spiceypy.ktotal("ALL"):
            raise HTTPException(503, detail={"code": "KERNEL_POOL_NOT_EMPTY", "message": "Unrecorded SPICE state."})
        timestamps = sample_times(request.start_utc, request.end_utc, request.sample_interval_seconds)
        output = {"alpha": [], "bravo": []}
        try:
            with load_kernels(paths) as provenance:
                for when in timestamps:
                    et = utc_to_et(when)
                    for key, site in (("alpha", request.site_alpha), ("bravo", request.site_bravo)):
                        geometry = _site_geometry(site, et)
                        output[key].append({"utc": when.isoformat(), "sun": geometry["sun"], "earth": geometry["earth"]})
                provenance_data = {"spiceypy_version": provenance.spiceypy_version,
                    "kernels": [{"filename": Path(k.path).name, "sha256": k.sha256} for k in provenance.kernels]}
        except (ValueError, OSError, spiceypy.utils.exceptions.SpiceyError) as exc:
            raise HTTPException(422, detail={"code": "SCIENTIFIC_CALCULATION_FAILED", "message": str(exc)[:300]}) from exc
        sites = {}
        for key in ("alpha", "bravo"):
            samples = [Sample(datetime.fromisoformat(row["utc"]),
                              row["sun"]["visible_geometric_center"], row["earth"]["visible_geometric_center"])
                       for row in output[key]]
            sites[key] = {"snapshots": output[key], "solar_summary": summarize(samples, "solar_visible"),
                          "earth_summary": summarize(samples, "earth_visible")}
        return {"calculation_status": "EXECUTED", "model": "IAU_MOON_MEAN_SPHERE_POINT_TARGET_SAMPLED",
                "scientific_acceptance": "NOT_VALIDATED", "reference_frame": FRAME,
                "start_utc": timestamps[0].isoformat(), "end_utc": timestamps[-1].isoformat(),
                "sample_interval_seconds": request.sample_interval_seconds, "sites": sites,
                "provenance": provenance_data,
                "warnings": ["Sampling does not validate continuous visibility or transition instants.",
                             "No terrain, target disk, or independent accuracy certification. Not for landing operations."]}
    finally:
        _SPICE_LOCK.release()
