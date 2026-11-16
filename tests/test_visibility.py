from math import cos, radians, sin

import pytest

from anais_lunarnav import MOON_MEAN_RADIUS_KM, LunarCoordinates, lunar_visibility

RADIUS = MOON_MEAN_RADIUS_KM


def test_surface_site_zenith_horizon_and_occultation():
    site = LunarCoordinates(0, 0)
    zenith = lunar_visibility(site, (RADIUS + 1000, 0, 0))
    horizon = lunar_visibility(site, (RADIUS, 1000, 0))
    hidden = lunar_visibility(site, (-RADIUS - 1000, 0, 0))
    assert zenith.visible and zenith.elevation_deg == pytest.approx(90)
    assert zenith.azimuth_deg is None
    assert zenith.distance_km == pytest.approx(1000)
    assert horizon.visible and horizon.elevation_deg == pytest.approx(0, abs=1e-12)
    assert horizon.azimuth_deg == pytest.approx(90)
    assert not hidden.visible and hidden.elevation_deg == pytest.approx(-90)


def test_elevated_site_horizon_and_finite_target():
    site = LunarCoordinates(0, 0, 100)

    def distant_target(elevation):
        angle = radians(elevation)
        return (RADIUS + 100 + 10000 * sin(angle), 10000 * cos(angle), 0)

    above_horizon = lunar_visibility(site, distant_target(-10))
    below_horizon = lunar_visibility(site, distant_target(-30))
    nearby = lunar_visibility(site, (RADIUS + 50, 10, 0))
    assert above_horizon.horizon_elevation_deg == pytest.approx(-18.993213, abs=0.01)
    assert above_horizon.visible
    assert not below_horizon.visible
    assert nearby.elevation_deg < nearby.horizon_elevation_deg
    assert nearby.visible


def test_azimuth_is_clockwise_from_north():
    site = LunarCoordinates(0, 0)
    north = lunar_visibility(site, (RADIUS, 0, 100))
    west = lunar_visibility(site, (RADIUS, -100, 0))
    assert north.azimuth_deg == pytest.approx(0)
    assert west.azimuth_deg == pytest.approx(270)


@pytest.mark.parametrize(
    ("site", "target"),
    [
        (LunarCoordinates(0, 0, -1), (10000, 0, 0)),
        (LunarCoordinates(0, 0), (0, 0, 0)),
        (LunarCoordinates(0, 0), (RADIUS, 0, 0)),
        (LunarCoordinates(0, 0), (float("nan"), 0, 0)),
        (LunarCoordinates(0, 0), (1.79e308, 1.79e308, 1.79e308)),
        (LunarCoordinates(0, 0), (1, 2)),
    ],
)
def test_invalid_geometry_is_rejected(site, target):
    with pytest.raises(ValueError):
        lunar_visibility(site, target)
