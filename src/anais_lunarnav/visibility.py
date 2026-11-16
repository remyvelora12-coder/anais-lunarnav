"""Instantaneous point-target visibility above a spherical lunar surface."""

from dataclasses import dataclass
from math import acos, atan2, cos, degrees, hypot, isfinite, radians, sin
from typing import Optional, Tuple

from .coordinates import MOON_MEAN_RADIUS_KM, LunarCoordinates, selenographic_to_cartesian


@dataclass(frozen=True)
class Visibility:
    """Topocentric direction, distance, and mean-sphere occultation result."""

    elevation_deg: float
    azimuth_deg: Optional[float]
    distance_km: float
    horizon_elevation_deg: float
    visible: bool


def lunar_visibility(
    site: LunarCoordinates, target_km: Tuple[float, float, float]
) -> Visibility:
    """Assess a point target in the same Moon-fixed Cartesian frame as the site."""
    if site.altitude_km < 0:
        raise ValueError("Visibility requires a site on or above the mean sphere")
    if len(target_km) != 3 or not all(isfinite(value) for value in target_km):
        raise ValueError("Target must have three finite Cartesian components")
    target_radius = hypot(*target_km)
    if not isfinite(target_radius):
        raise ValueError("Target distance must be finite")
    if target_radius < MOON_MEAN_RADIUS_KM:
        raise ValueError("Target must be on or outside the mean sphere")

    origin = selenographic_to_cartesian(site)
    relative = tuple(target - observer for target, observer in zip(target_km, origin))
    distance = hypot(*relative)
    if not isfinite(distance):
        raise ValueError("Observer-to-target distance must be finite")
    if distance == 0:
        raise ValueError("Target and observer cannot coincide")
    direction = tuple(value / distance for value in relative)
    latitude = radians(site.latitude_deg)
    longitude = radians(site.longitude_deg)
    up = (cos(latitude) * cos(longitude), cos(latitude) * sin(longitude), sin(latitude))
    east = (-sin(longitude), cos(longitude), 0.0)
    north = (-sin(latitude) * cos(longitude), -sin(latitude) * sin(longitude), cos(latitude))
    vertical = sum(a * b for a, b in zip(direction, up))
    eastward = sum(a * b for a, b in zip(direction, east))
    northward = sum(a * b for a, b in zip(direction, north))
    horizontal = hypot(eastward, northward)
    elevation = degrees(atan2(vertical, horizontal))
    azimuth = None if horizontal < 1e-15 else degrees(atan2(eastward, northward)) % 360
    horizon = -degrees(acos(MOON_MEAN_RADIUS_KM / (MOON_MEAN_RADIUS_KM + site.altitude_km)))

    closest_distance = -sum(a * b for a, b in zip(origin, direction))
    if 0 < closest_distance < distance:
        closest_point = tuple(
            component + closest_distance * unit for component, unit in zip(origin, direction)
        )
        clearance = hypot(*closest_point) - MOON_MEAN_RADIUS_KM
        visible = clearance >= -1e-9
    else:
        visible = True
    return Visibility(elevation, azimuth, distance, horizon, visible)
