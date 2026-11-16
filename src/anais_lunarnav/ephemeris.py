"""Geometric Sun and Earth positions in the IAU lunar body-fixed frame."""

from dataclasses import dataclass
from math import isfinite
from typing import Literal, Tuple

import spiceypy

Body = Literal["SUN", "EARTH"]


@dataclass(frozen=True)
class BodyPosition:
    """Geometric Moon-center-to-body vector in IAU_MOON, in kilometers."""

    body: Body
    et_seconds: float
    position_km: Tuple[float, float, float]


def body_position(body: Body, et_seconds: float) -> BodyPosition:
    """Query geometric position at ET using the caller's loaded SPICE kernels."""
    if body not in ("SUN", "EARTH"):
        raise ValueError("Body must be SUN or EARTH")
    if not isfinite(et_seconds):
        raise ValueError("ET seconds must be finite")
    position, _ = spiceypy.spkpos(body, et_seconds, "IAU_MOON", "NONE", "MOON")
    return BodyPosition(
        body=body,
        et_seconds=float(et_seconds),
        position_km=(float(position[0]), float(position[1]), float(position[2])),
    )
