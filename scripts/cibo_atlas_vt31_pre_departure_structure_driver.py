"""Compatibility driver for the VT-31 pre-departure structure lab.

The consumed sparse-reference research module intentionally does not export a
timezone constant. The lab requires an explicit America/New_York clock for its
reporting-only pivot minute. Bind that clock here without altering any market
selection, structure, path, or outcome semantics.
"""
from __future__ import annotations

from zoneinfo import ZoneInfo

import vt31_r8_sparse_reference_forensics as sparse
import cibo_atlas_vt31_pre_departure_structure_lab as lab


def main() -> None:
    setattr(sparse, "NY", ZoneInfo("America/New_York"))
    lab.main()


if __name__ == "__main__":
    main()
