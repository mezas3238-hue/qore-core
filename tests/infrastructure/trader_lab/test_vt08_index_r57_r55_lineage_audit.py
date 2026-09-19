from __future__ import annotations

from qore.infrastructure.trader_lab import (
    vt08_index_r57_r55_lineage_audit as r57,
)


def test_r57_is_audit_only() -> None:
    assert r57.IDENTITY == "VT08_INDEX_R57_R55_LINEAGE_AUDIT_001"
