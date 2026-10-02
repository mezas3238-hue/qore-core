import json
from pathlib import Path

from qore.infrastructure.cibo_arch2_active_frontier_v2 import architect2_active_frontier_v2


_PACKAGE = Path("docs/research/CIBO-ARCH-2-ACTIVE-CLOSURE-PACKAGE-V2.json")


def test_active_closure_package_matches_executable_frontier() -> None:
    payload = json.loads(_PACKAGE.read_text(encoding="utf-8"))
    package_rows = {
        row["workstream_id"]: row
        for row in payload["fronts"]
    }
    frontier = architect2_active_frontier_v2()

    assert tuple(package_rows) == tuple(item.workstream_id for item in frontier)
    for item in frontier:
        row = package_rows[item.workstream_id]
        assert row["state"] == item.state.value
        if item.proposed_terminal_disposition is None:
            assert "proposed_terminal_disposition" not in row
        else:
            assert (
                row["proposed_terminal_disposition"]
                == item.proposed_terminal_disposition
            )


def test_active_package_summary_matches_frontier_counts() -> None:
    payload = json.loads(_PACKAGE.read_text(encoding="utf-8"))
    frontier = architect2_active_frontier_v2()
    terminal = tuple(
        item
        for item in frontier
        if item.proposed_terminal_disposition is not None
    )

    assert payload["summary"]["scope_count"] == len(frontier) == 8
    assert payload["summary"]["terminal_recommendation_ready"] == len(terminal)
    assert payload["summary"]["nonterminal_active_fronts"] == (
        len(frontier) - len(terminal)
    )
    assert payload["governance"]["canonical_ledger_modified"] is False
    assert payload["governance"]["phase22_v2_consumed"] is False
    assert payload["governance"]["integrator_branch_modified"] is False
    assert payload["governance"]["productive_authority"] is False
