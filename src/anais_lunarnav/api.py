"""HTTP interface to existing ANAIS LunarNav science functions (research only)."""
from datetime import datetime
import os
from pathlib import Path
from threading import Lock
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .coordinates import MOON_MEAN_RADIUS_KM, LunarCoordinates, cartesian_to_selenographic, selenographic_to_cartesian
from .ephemeris import body_position
from .provenance import load_kernels
from .time import utc_to_et
from .visibility import lunar_visibility

FRAME = "IAU_MOON"
_SPICE_LOCK = Lock()

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

class Site(StrictModel):
    latitude_deg: float = Field(ge=-90, le=90)
    longitude_deg: float = Field(ge=-180, le=180)
    observer_height_m: float = Field(ge=0, le=100000)

    def location(self):
        return LunarCoordinates(longitude_deg=self.longitude_deg, latitude_deg=self.latitude_deg, altitude_km=self.observer_height_m / 1000)

class Cartesian(StrictModel):
    x_km: float
    y_km: float
    z_km: float

class InstantRequest(StrictModel):
    site: Site
    observation_utc: datetime
    reference_frame: Literal["IAU_MOON"] = FRAME

    @field_validator("observation_utc")
    @classmethod
    def require_zone(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observation_utc must include a timezone")
        return value

class CompareRequest(StrictModel):
    site_alpha: Site
    site_bravo: Site
    observation_utc: datetime
    reference_frame: Literal["IAU_MOON"] = FRAME

    @field_validator("observation_utc")
    @classmethod
    def require_zone(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observation_utc must include a timezone")
        return value

def configured_kernels():
    return [p for p in os.environ.get("LUNARNAV_KERNEL_PATHS", "").split(os.pathsep) if p]

def _site_geometry(site, et):
    result = {}
    for body in ("SUN", "EARTH"):
        position = body_position(body, et)
        visibility = lunar_visibility(site.location(), position.position_km)
        result[body.lower()] = {
            "azimuth_deg": visibility.azimuth_deg,
            "elevation_deg": visibility.elevation_deg,
            "range_km": visibility.distance_km,
            "horizon_elevation_deg": visibility.horizon_elevation_deg,
            "visible_geometric_center": visibility.visible,
        }
    return result

def _execute(sites, observation_utc):
    paths = configured_kernels()
    if not paths:
        raise HTTPException(503, detail={"code": "KERNELS_NOT_CONFIGURED", "message": "Operator must configure vetted LSK, SPK and PCK; no scientific results calculated."})
    if any(not Path(path).is_file() for path in paths):
        raise HTTPException(503, detail={"code": "KERNEL_FILE_MISSING", "message": "A configured kernel file is missing."})
    if not _SPICE_LOCK.acquire(blocking=False):
        raise HTTPException(503, detail={"code": "SPICE_BUSY", "message": "Scientific engine busy."})
    try:
        import spiceypy
        if spiceypy.ktotal("ALL") != 0:
            raise HTTPException(503, detail={"code": "KERNEL_POOL_NOT_EMPTY", "message": "Unrecorded process-wide SPICE state."})
        try:
            with load_kernels(paths) as provenance:
                et = utc_to_et(observation_utc)
                values = {key: _site_geometry(site, et) for key, site in sites.items()}
                return {
                    "calculation_status": "EXECUTED",
                    "model": "MEAN_SPHERE_GEOMETRIC_POINT_TARGET",
                    "reference_frame": FRAME,
                    "mean_radius_km": MOON_MEAN_RADIUS_KM,
                    "aberration_correction": "NONE",
                    "observation_utc": observation_utc.isoformat(),
                    "et_seconds_past_j2000_tdb": et,
                    "sites": values,
                    "provenance": {"spiceypy_version": provenance.spiceypy_version, "kernels": [{"filename": Path(k.path).name, "sha256": k.sha256} for k in provenance.kernels]},
                    "warnings": ["Geometric center-point visibility only; no terrain obstruction, finite-body disk, or landing-safety certification.", "Ephemeris/frame/kernel coverage must be validated against independent references."],
                }
        except (ValueError, OSError, spiceypy.utils.exceptions.SpiceyError) as exc:
            raise HTTPException(422, detail={"code": "SCIENTIFIC_CALCULATION_FAILED", "message": str(exc)[:400]}) from exc
    finally:
        _SPICE_LOCK.release()

app = FastAPI(title="ANAIS LunarNav Scientific API", version="0.2.0", description="Geometric lunar research prototype; not operational flight guidance.")

@app.get("/health")
def health():
    paths = configured_kernels()
    return {"service": "anais-lunarnav", "status": "ok", "scientific_kernels_configured": bool(paths), "scientific_kernels_present": bool(paths) and all(Path(p).is_file() for p in paths)}

@app.post("/v1/coordinates/cartesian")
def coordinates_cartesian(site: Site):
    return {"reference_frame": FRAME, "mean_radius_km": MOON_MEAN_RADIUS_KM, "cartesian_km": selenographic_to_cartesian(site.location())}

@app.post("/v1/coordinates/surface")
def coordinates_surface(vector: Cartesian):
    try:
        surface = cartesian_to_selenographic((vector.x_km, vector.y_km, vector.z_km))
    except ValueError as exc:
        raise HTTPException(422, detail={"code": "INVALID_CARTESIAN", "message": str(exc)}) from exc
    return {"reference_frame": FRAME, "longitude_deg": surface.longitude_deg, "latitude_deg": surface.latitude_deg, "observer_height_m": surface.altitude_km * 1000}

@app.post("/v1/analysis/instant")
def analyze_instant(request: InstantRequest):
    return _execute({"site": request.site}, request.observation_utc)

@app.post("/v1/analysis/compare-instant")
def analyze_compare_instant(request: CompareRequest):
    """Compare two sites at one epoch, not an observation window."""
    return _execute({"alpha": request.site_alpha, "bravo": request.site_bravo}, request.observation_utc)
