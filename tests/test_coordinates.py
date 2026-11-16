import math

import pytest

from anais_lunarnav import (
    MOON_MEAN_RADIUS_KM,
    LunarCoordinates,
    cartesian_to_selenographic,
    selenographic_to_cartesian,
    transform_vector,
)


def test_selenographic_axes_match_spherical_reference_values():
    assert selenographic_to_cartesian(LunarCoordinates(0.0, 0.0)) == pytest.approx(
        (MOON_MEAN_RADIUS_KM, 0.0, 0.0), abs=1e-12
    )
    assert selenographic_to_cartesian(LunarCoordinates(90.0, 0.0)) == pytest.approx(
        (0.0, MOON_MEAN_RADIUS_KM, 0.0), abs=1e-12
    )
    assert selenographic_to_cartesian(LunarCoordinates(0.0, 90.0)) == pytest.approx(
        (0.0, 0.0, MOON_MEAN_RADIUS_KM), abs=1e-12
    )


def test_selenographic_round_trip_preserves_location_and_altitude():
    original = LunarCoordinates(longitude_deg=-47.25, latitude_deg=23.5, altitude_km=1.2)

    result = cartesian_to_selenographic(selenographic_to_cartesian(original))

    assert result.longitude_deg == pytest.approx(original.longitude_deg)
    assert result.latitude_deg == pytest.approx(original.latitude_deg)
    assert result.altitude_km == pytest.approx(original.altitude_km)


@pytest.mark.parametrize(
    "coordinates",
    [
        (181.0, 0.0, 0.0),
        (0.0, 91.0, 0.0),
        (0.0, 0.0, -MOON_MEAN_RADIUS_KM),
        (math.inf, 0.0, 0.0),
    ],
)
def test_invalid_selenographic_coordinates_are_rejected(coordinates):
    with pytest.raises(ValueError):
        LunarCoordinates(*coordinates)


def test_cartesian_origin_has_no_selenographic_coordinates():
    with pytest.raises(ValueError, match="zero vector"):
        cartesian_to_selenographic((0.0, 0.0, 0.0))


def test_same_frame_transform_is_identity_without_kernels():
    vector = (1.0, -2.0, 3.0)

    assert transform_vector(vector, "J2000", "J2000", 0.0) == pytest.approx(vector)
