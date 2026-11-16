"""Kernel loading and content-addressed provenance for SPICE computations."""

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Iterator, Sequence, Tuple, Union

import spiceypy


@dataclass(frozen=True)
class KernelProvenance:
    """Absolute kernel path and SHA-256 digest for a loaded input file."""

    path: str
    sha256: str


@dataclass(frozen=True)
class SpiceProvenance:
    """SPICE toolkit version and ordered kernel inputs for a computation."""

    spiceypy_version: str
    kernels: Tuple[KernelProvenance, ...]


KernelPath = Union[str, Path]


def _describe_kernel(path: KernelPath) -> KernelProvenance:
    resolved = Path(path).expanduser().resolve(strict=True)
    if not resolved.is_file():
        raise ValueError("Kernel path must refer to a file: {}".format(resolved))
    digest = hashlib.sha256(resolved.read_bytes()).hexdigest()
    return KernelProvenance(path=str(resolved), sha256=digest)


def _is_loaded(path: str) -> bool:
    for index in range(spiceypy.ktotal("ALL")):
        loaded_path = spiceypy.kdata(index, "ALL")[0]
        if Path(loaded_path).resolve() == Path(path):
            return True
    return False


@contextmanager
def load_kernels(paths: Sequence[KernelPath]) -> Iterator[SpiceProvenance]:
    """Load kernels for a scoped operation and unload only those loaded here.

    SPICE's kernel pool is process-global. Callers must avoid overlapping kernel
    contexts across threads and must record the yielded provenance with results.
    """
    kernel_records = tuple(_describe_kernel(path) for path in paths)
    if not kernel_records:
        raise ValueError("At least one SPICE kernel is required")
    if len({record.path for record in kernel_records}) != len(kernel_records):
        raise ValueError("Kernel paths must be unique")
    already_loaded = [record.path for record in kernel_records if _is_loaded(record.path)]
    if already_loaded:
        raise ValueError(
            "Kernel is already loaded in the process-wide SPICE pool: {}".format(
                ", ".join(already_loaded)
            )
        )

    loaded_paths = []
    try:
        for record in kernel_records:
            spiceypy.furnsh(record.path)
            loaded_paths.append(record.path)
        yield SpiceProvenance(
            spiceypy_version=spiceypy.__version__,
            kernels=kernel_records,
        )
    finally:
        for path in reversed(loaded_paths):
            spiceypy.unload(path)
