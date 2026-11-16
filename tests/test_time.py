import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from anais_lunarnav import et_to_utc, load_kernels, utc_to_et

LSK_PATH = Path(__file__).parent / "fixtures" / "naif0012.tls"


def test_j2000_utc_reference_converts_to_spice_et():
    with load_kernels([LSK_PATH]) as provenance:
        et = utc_to_et("2000-01-01T12:00:00Z")

    assert et == pytest.approx(64.18392728473108, abs=1e-6)
    assert provenance.spiceypy_version
    assert len(provenance.kernels) == 1
    assert provenance.kernels[0].sha256 == hashlib.sha256(LSK_PATH.read_bytes()).hexdigest()


def test_et_round_trip_returns_utc_iso8601():
    with load_kernels([LSK_PATH]):
        et = utc_to_et("2000-01-01T12:00:00Z")
        utc = et_to_utc(et, precision=6)

    assert utc == "2000-01-01T12:00:00.000000Z"


def test_timezone_aware_datetime_is_normalized_to_utc():
    with load_kernels([LSK_PATH]):
        local_time = datetime(2000, 1, 1, 7, 0, tzinfo=timezone(timedelta(hours=-5)))
        utc_time = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)

        assert utc_to_et(local_time) == pytest.approx(utc_to_et(utc_time), abs=1e-9)


def test_timezone_offset_string_is_normalized_to_utc():
    with load_kernels([LSK_PATH]):
        offset_time = utc_to_et("2000-01-01T07:00:00.123456789-05:00")
        utc_time = utc_to_et("2000-01-01T12:00:00.123456789Z")
        utc_suffix_time = utc_to_et("2000-01-01T12:00:00.123456789 UTC")

    assert offset_time == pytest.approx(utc_time, abs=1e-9)
    assert utc_suffix_time == pytest.approx(utc_time, abs=1e-9)


def test_leap_second_is_distinct_from_following_utc_instant():
    with load_kernels([LSK_PATH]):
        leap_second_et = utc_to_et("2016-12-31T23:59:60Z")
        midnight_et = utc_to_et("2017-01-01T00:00:00Z")

    assert midnight_et - leap_second_et == pytest.approx(1.0, abs=1e-6)


def test_kernel_context_unloads_its_kernel():
    import spiceypy

    before = spiceypy.ktotal("ALL")
    with load_kernels([LSK_PATH]):
        assert spiceypy.ktotal("ALL") == before + 1
    assert spiceypy.ktotal("ALL") == before


def test_kernel_context_preserves_a_kernel_loaded_by_the_caller():
    import spiceypy

    path = str(LSK_PATH.resolve())
    spiceypy.furnsh(path)
    try:
        before = spiceypy.ktotal("ALL")
        with pytest.raises(ValueError, match="already loaded"):
            with load_kernels([LSK_PATH]):
                pass
        assert spiceypy.ktotal("ALL") == before
    finally:
        spiceypy.unload(path)


@pytest.mark.parametrize(
    "value",
    [
        datetime(2000, 1, 1, 12, 0),
        "2000-01-01T12:00:00",
        "tomorrow",
    ],
)
def test_utc_conversion_rejects_naive_or_non_absolute_input(value):
    with pytest.raises(ValueError):
        utc_to_et(value)


@pytest.mark.parametrize("precision", [-1, 15, 1.5])
def test_et_formatting_rejects_invalid_precision(precision):
    with pytest.raises(ValueError):
        et_to_utc(0.0, precision=precision)
