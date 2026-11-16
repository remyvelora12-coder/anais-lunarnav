import math
import os
from pathlib import Path

import pytest
import spiceypy

from anais_lunarnav import (
    LunarCoordinates,
    body_position,
    load_kernels,
    lunar_visibility,
    transform_vector,
)


@pytest.fixture
def synthetic_kernels(tmp_path):
    pck = tmp_path / "moon.tpc"
    pck.write_text(
        "KPL/PCK\n\n"
        "\\begindata\n"
        "BODY301_POLE_RA = ( 270 0 0 )\n"
        "BODY301_POLE_DEC = ( 90 0 0 )\n"
        "BODY301_PM = ( 90 0 0 )\n"
        "\\begintext\n"
    )
    spk = tmp_path / "positions.bsp"
    handle = spiceypy.spkopn(str(spk), "Synthetic test positions", 0)
    try:
        for body, position in [(10, (10000.0, 0.0, 0.0)), (399, (0.0, 10000.0, 0.0))]:
            states = [(*position, 0.0, 0.0, 0.0)] * 2
            spiceypy.spkw08(
                handle, body, 301, "J2000", -100.0, 100.0,
                "synthetic {}".format(body), 1, 2, states, -100.0, 200.0,
            )
    finally:
        spiceypy.spkcls(handle)
    return [pck, spk]


@pytest.mark.parametrize(
    ("body", "position"),
    [("SUN", (0.0, -10000.0, 0.0)), ("EARTH", (10000.0, 0.0, 0.0))],
)
def test_synthetic_spk_and_lunar_frame_position(synthetic_kernels, body, position):
    with load_kernels(synthetic_kernels):
        result = body_position(body, 0.0)
    assert result.body == body
    assert result.et_seconds == 0.0
    assert result.position_km == pytest.approx(position, abs=1e-8)


def test_ephemeris_integrates_with_site_visibility(synthetic_kernels):
    with load_kernels(synthetic_kernels):
        sun = body_position("SUN", 0.0)
        observation = lunar_visibility(LunarCoordinates(-90.0, 0.0), sun.position_km)
    assert observation.visible
    assert observation.elevation_deg == pytest.approx(90.0)
    assert observation.azimuth_deg is None


def test_missing_coverage_raises_spice_error(synthetic_kernels):
    with load_kernels(synthetic_kernels):
        with pytest.raises(spiceypy.utils.exceptions.SpiceyError):
            body_position("SUN", 101.0)


@pytest.mark.parametrize(("body", "et"), [("MARS", 0), ("SUN", math.inf)])
def test_invalid_ephemeris_request_is_rejected(body, et):
    with pytest.raises(ValueError):
        body_position(body, et)


@pytest.mark.parametrize(
    ("body", "reference", "tolerance_km"),
    [
        ("SUN", (26790642.06161821, -132490700.504491, -57480615.98323413), 0.2),
        ("EARTH", (291608.3841877129, 266716.8338540655, 76102.48730658794), 0.01),
    ],
)
def test_real_kernels_against_horizons_de441(body, reference, tolerance_km):
    spk_path = os.environ.get("LUNARNAV_DE432S")
    pck_path = os.environ.get("LUNARNAV_PCK00011")
    if not spk_path and not pck_path:
        pytest.skip("Set LUNARNAV_DE432S and LUNARNAV_PCK00011 for the reference test")
    if not spk_path or not pck_path:
        pytest.fail("Both LUNARNAV_DE432S and LUNARNAV_PCK00011 must be set")

    with load_kernels([Path(spk_path), Path(pck_path)]) as provenance:
        assert [kernel.sha256 for kernel in provenance.kernels] == [
            "363f32e14f5255359ac32c4d38080cf28ab55564a5e16696a75f63394b666e9b",
            "3dff7b1dbeceaa01f25467767d3fa25816051c85d162d1edf04acb310ee28bb1",
        ]
        position = body_position(body, 0.0)
        inertial = transform_vector(position.position_km, "IAU_MOON", "J2000", 0.0)

    assert math.dist(inertial, reference) < tolerance_km
