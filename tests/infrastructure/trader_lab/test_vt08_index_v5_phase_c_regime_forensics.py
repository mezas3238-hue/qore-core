from __future__ import annotations

import csv
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab.vt08_index_v5_phase_c_regime_forensics import run


def test_phase_c_rejects_nonfrozen_sample(tmp_path: Path) -> None:
    p = tmp_path / "c.csv"
    with p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["window_id", "label_r"])
        w.writeheader(); w.writerow({"window_id": "2022_23", "label_r": "1"})
    with pytest.raises(ValueError, match="183-row"):
        run(p, tmp_path / "out.json")
