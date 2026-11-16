"""UTC and SPICE ephemeris-time conversion."""

from datetime import datetime, timezone
import re
from math import isfinite
from typing import Union

import spiceypy

_ISO_UTC_PATTERN = re.compile(
    r"^(?P<base>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})"
    r"(?P<fraction>\.\d+)?(?P<zone>Z| UTC|[+-]\d{2}:\d{2})$"
)


def utc_to_et(utc: Union[datetime, str]) -> float:
    """Convert an aware datetime or absolute timezone-qualified ISO string to ET."""
    if isinstance(utc, datetime):
        if utc.tzinfo is None or utc.utcoffset() is None:
            raise ValueError("Datetime input must include a timezone")
        normalized = utc.astimezone(timezone.utc)
        utc_string = normalized.isoformat(timespec="microseconds").replace("+00:00", "Z")
    elif isinstance(utc, str):
        match = _ISO_UTC_PATTERN.fullmatch(utc)
        if match is None:
            raise ValueError(
                "UTC input must be an aware datetime or an absolute ISO-8601 string "
                "with Z, UTC, or a numeric offset"
            )
        base = match.group("base")
        fraction = match.group("fraction") or ""
        zone = match.group("zone")
        if zone in ("Z", " UTC"):
            utc_string = base.replace("T", " ") + fraction + " UTC"
        elif base.endswith(":60"):
            raise ValueError("Leap-second strings must use Z or UTC, not a numeric offset")
        else:
            local_time = datetime.fromisoformat(base + zone)
            normalized = local_time.astimezone(timezone.utc)
            utc_string = normalized.strftime("%Y-%m-%d %H:%M:%S") + fraction + " UTC"
    else:
        raise ValueError(
            "UTC input must be an aware datetime or an absolute ISO-8601 string "
            "with Z, UTC, or a numeric offset"
        )
    return float(spiceypy.str2et(utc_string))


def et_to_utc(et_seconds: float, precision: int = 6) -> str:
    """Convert SPICE ET seconds past J2000 to an ISO UTC string ending in Z."""
    if not isfinite(et_seconds):
        raise ValueError("ET seconds must be finite")
    if (
        isinstance(precision, bool)
        or not isinstance(precision, int)
        or not 0 <= precision <= 14
    ):
        raise ValueError("Precision must be an integer from 0 through 14")
    return spiceypy.et2utc(et_seconds, "ISOC", precision) + "Z"
