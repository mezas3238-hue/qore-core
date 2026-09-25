from __future__ import annotations

import csv
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab.vt08_index_v5_phase_c_regime_forensics import run


# Regression guard: keep CSV writes on separate lines so Ruff E702 remains satisfied.
def test_phase_c_rejects_nonfrozen_sample(tmp_path: Path) -> None:
    path = tmp_path / "c.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["window_id", "label_r"])
        writer.writeheader()
        writer.writerow({"window_id": "2022_23", "label_r": "1"})
    with pytest.raises(ValueError, match="183-row"):
        run(path, tmp_path / "out.json")
