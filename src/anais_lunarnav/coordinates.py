"""Spherical selenographic coordinates and SPICE frame-vector transforms."""

from dataclasses import dataclass
from math import asin, atan2, cos, degrees, isfinite, radians, sin, sqrt
from typing import Tuple

import spiceypy

MOON_MEAN_RADIUS_KM = 1737.4


@dataclass(frozen=True)
class LunarCoordinates:
    """East-positive, planetocentric selenographic coordinates in kilometers."""

    longitude_deg: float
    latitude_deg: float
    altitude_km: float = 0.0

    def __post_init__(self) -> None:
        values = (self.longitude_deg, self.latitude_deg, self.altitude_km)
        if not all(isfinite(value) for value in values):
            raise ValueError("Lunar coordinates must be finite")
        if not -180.0 <= self.longitude_deg <= 180.0:
            raise ValueError("Longitude must be in the range [-180, 180] degrees")
        if not -90.0 <= self.latitude_deg <= 90.0:
            raise ValueError("Latitude must be in the range [-90, 90] degrees")
        if self.altitude_km <= -MOON_MEAN_RADIUS_KM:
            raise ValueError("Altitude must leave a positive distance from the Moon's center")


def selenographic_to_cartesian(
    coordinates: LunarCoordinates,
) -> Tuple[float, float, float]:
    """Convert to Moon-centered Cartesian coordinates in the same body-fixed frame."""
    radius = MOON_MEAN_RADIUS_KM + coordinates.altitude_km
    longitude = radians(coordinates.longitude_deg)
    latitude = radians(coordinates.latitude_deg)
    latitude_cosine = cos(latitude)
    return (
        radius * latitude_cosine * cos(longitude),
        radius * latitude_cosine * sin(longitude),
        radius * sin(latitude),
    )


def cartesian_to_selenographic(
    vector_km: Tuple[float, float, float],
) -> LunarCoordinates:
    """Convert a nonzero Moon-centered Cartesian vector to spherical coordinates."""
    x, y, z = _finite_vector(vector_km)
    radius = sqrt(x * x + y * y + z * z)
    if radius == 0.0:
        raise ValueError("The zero vector has no selenographic coordinates")
    return LunarCoordinates(
        longitude_deg=degrees(atan2(y, x)),
        latitude_deg=degrees(asin(z / radius)),
        altitude_km=radius - MOON_MEAN_RADIUS_KM,
    )


def transform_vector(
    vector: Tuple[float, float, float],
    from_frame: str,
    to_frame: str,
    et_seconds: float,
) -> Tuple[float, float, float]:
    """Rotate a vector between SPICE frames at ET; no translation is applied."""
    components = _finite_vector(vector)
    if not from_frame or not to_frame:
        raise ValueError("Frame names must not be empty")
    if not isfinite(et_seconds):
        raise ValueError("ET seconds must be finite")
    matrix = spiceypy.pxform(from_frame, to_frame, et_seconds)
    return tuple(
        sum(float(matrix[row][column]) * components[column] for column in range(3))
        for row in range(3)
    )


def _finite_vector(vector: Tuple[float, float, float]) -> Tuple[float, float, float]:
    if len(vector) != 3:
        raise ValueError("A Cartesian vector must have exactly three components")
    components = (float(vector[0]), float(vector[1]), float(vector[2]))
    if not all(isfinite(component) for component in components):
        raise ValueError("Cartesian vector components must be finite")
    return components
