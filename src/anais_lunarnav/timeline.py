"""Sampled visibility timeline summary; no interpolation or continuous-coverage claims."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence

@dataclass(frozen=True)
class Sample:
    utc: datetime
    solar_visible: Optional[bool]
    earth_visible: Optional[bool]

def sample_times(start: datetime, end: datetime, step_seconds: int):
    if not isinstance(step_seconds, int) or isinstance(step_seconds, bool) or not 900 <= step_seconds <= 21600:
        raise ValueError("sample interval must be an integer between 900 and 21600 seconds")
    if start.tzinfo is None or end.tzinfo is None or start.utcoffset() is None or end.utcoffset() is None:
        raise ValueError("observation window timestamps must be timezone aware")
    start, end = start.astimezone(timezone.utc), end.astimezone(timezone.utc)
    seconds = (end - start).total_seconds()
    if not 0 < seconds <= 172800:
        raise ValueError("observation window must be between 0 and 48 hours")
    if seconds / step_seconds > 240:
        raise ValueError("window exceeds maximum of 241 samples")
    times = [start]
    while times[-1] < end:
        times.append(min(end, times[-1] + timedelta(seconds=step_seconds)))
    return times

def summarize(samples: Sequence[Sample], field: str):
    if field not in ("solar_visible", "earth_visible"):
        raise ValueError("unknown visibility field")
    if not samples:
        raise ValueError("at least one sample required")
    times = [sample.utc for sample in samples]
    if any(b <= a for a,b in zip(times, times[1:])):
        raise ValueError("samples must be strictly chronological")
    observations = [getattr(sample, field) for sample in samples]
    if any(v is not None and type(v) is not bool for v in observations):
        raise ValueError("visibility must be True, False or None")
    valid = [v for v in observations if v is not None]
    brackets = [{"start_utc": left.utc.isoformat(), "end_utc": right.utc.isoformat(),
                 "from_visible": a, "to_visible": b}
                for left, right, a, b in zip(samples, samples[1:], observations, observations[1:])
                if a is not None and b is not None and a != b]
    return {
        "sample_count": len(observations),
        "known_sample_count": len(valid),
        "unknown_sample_count": len(observations) - len(valid),
        "visible_sample_count": sum(valid),
        "visible_sample_fraction": sum(valid) / len(valid) if valid else None,
        "transition_brackets": brackets,
        "continuous_visibility_duration_seconds": None,
        "sampling_notice": "Snapshot fractions are not time fractions. Transitions are bracketed, not solved; no continuous visibility is implied."
    }
