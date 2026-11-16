# ANAIS LunarNav

## Scientific core (initial)

The installable `anais_lunarnav` package provides spherical selenographic
coordinate conversion, UTC/SPICE ephemeris-time conversion, geometric Sun and
Earth positions, and spherical lunar visibility. Install and run its focused
tests with:

```sh
python -m pip install -e ".[test]"
python -m pytest
```

Coordinate values use east-positive longitude in `[-180, 180]` degrees,
planetocentric latitude in `[-90, 90]` degrees, altitude in kilometers above a
sphere of radius 1737.4 km, and Moon-centered Cartesian kilometers. This is a
mean-sphere convention, not a lunar ellipsoid, terrain model, or complete
geodetic definition. The positive x-axis is longitude 0, the positive y-axis
is 90 degrees east, and the positive z-axis is the north pole. `transform_vector`
applies a SPICE frame rotation at ET without translating the vector; frame
definitions and any required kernels must be supplied by the caller.

UTC input is an aware `datetime` or an absolute ISO-8601 string with `Z`, `UTC`,
or a numeric offset. UTC/ET conversion requires an applicable loaded SPICE
leapseconds kernel. Use `load_kernels(paths)` as a context manager; its yielded
`SpiceProvenance` records the SpiceyPy version and the ordered kernel paths and
SHA-256 digests. The record covers only the supplied files, not preloaded
kernels, meta-kernel dependencies, or kernel pool assignments. For reproducible
results, start with an empty kernel pool, load each required kernel directly
in order, avoid pool modifications during the computation, and persist the
record alongside inputs, model conventions, and results. The SPICE kernel pool
is process-global, so kernel contexts must not overlap across threads.

`body_position("SUN" or "EARTH", et_seconds)` returns the geometric
Moon-center-to-body vector in the `IAU_MOON` frame at the supplied ET (seconds
past J2000 TDB). It requires a planetary SPK covering the requested bodies and
time and a lunar orientation PCK. No light-time or stellar-aberration
correction is applied. Use an applicable LSK to convert UTC to ET first.

`lunar_visibility(site, position.position_km)` treats the site as an
`IAU_MOON` mean-sphere coordinate and the target as a point in the same frame.
It returns topocentric distance, elevation above the local horizontal, azimuth
clockwise from north (undefined at zenith/nadir), the spherical horizon
elevation, and whether the finite line segment is unobstructed by the mean
sphere. Sites below the sphere are rejected. Tangency counts as visible, with
a 1e-9 km numerical clearance tolerance. This is a geometric center-point
calculation; it does not model terrain, body angular size, refraction,
illumination, or light-time. It is not suitable for operational decisions.

No production kernels are bundled. The UTC tests use NAIF's `naif0012.tls`
leapseconds kernel, sourced from
<https://naif.jpl.nasa.gov/pub/naif/generic_kernels/lsk/naif0012.tls>; this
fixture reflects leap seconds through 2017 and is not suitable as a current
operational kernel without checking for updates. Tests verify a known J2000
UTC-to-ET value and leap-second handling, deterministic spherical geometry, and
the SPICE ephemeris path using synthetic kernels.

Optional reference tests compare the computed Sun and Earth vectors at ET 0,
rotated back to J2000, to NASA/JPL Horizons DE441 geometric ICRF vectors for
2000-01-01 12:00:00 TDB (queried 2026-11-15; Moon center, KM-S, no aberration).
Run with the NAIF
[de432s.bsp](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de432s.bsp)
and [pck00011.tpc](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/pck00011.tpc)
files:

```sh
LUNARNAV_DE432S=/path/to/de432s.bsp LUNARNAV_PCK00011=/path/to/pck00011.tpc \
  python -m pytest tests/test_ephemeris.py
```

The tests pin the kernel hashes and allow 0.2 km for the Sun and 0.01 km for
Earth because the DE432s and DE441 ephemerides differ. These comparisons do
not independently validate lunar orientation, other dates, terrain,
visibility against real observations, or mission comparisons.