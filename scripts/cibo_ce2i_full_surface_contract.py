"""Emit the fail-closed CIBO CE2I 20/20 architecture contract."""

from __future__ import annotations

import json

from qore.infrastructure.cibo_ce2i_advanced_capital_tools import (
    advanced_ce2i_engine_codes,
)
from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
)
from qore.infrastructure.cibo_ce2i_tool_registry import (
    CE2I_TOOL_REGISTRY,
    ToolMaturity,
)


def main() -> None:
    canonical = tuple(f"T{index:02d}" for index in range(1, 21))
    registry = tuple(tool.code for tool in CE2I_TOOL_REGISTRY)
    advanced = advanced_ce2i_engine_codes()
    incomplete = tuple(
        tool.code
        for tool in CE2I_TOOL_REGISTRY
        if tool.maturity
        in {ToolMaturity.ARCHITECTURE_ONLY, ToolMaturity.REJECTED}
    )
    candidate = FROZEN_PHASE20_POLICY_CANDIDATE
    plan = FROZEN_PHASE20D_QUALIFICATION_PLAN

    assert registry == canonical
    assert not incomplete
    assert advanced == ("T02", "T03", "T04", "T08", "T10", "T16", "T17")
    assert candidate.active_ce2i_tools == canonical
    assert (
        "FULL_CE2I_TOOL_SURFACE_20_OF_20_IMPLEMENTED"
        in plan.hard_gates
    )
    assert (
        "ADVANCED_TOOL_EVIDENCE_COMPLETE_OR_EXPLICIT_ABSTENTION"
        in plan.hard_gates
    )

    print(
        json.dumps(
            {
                "status": "CIBO_CE2I_FULL_SURFACE_ARCHITECTURE_BOUND",
                "registry_count": len(registry),
                "registry_codes": list(registry),
                "advanced_engine_codes": list(advanced),
                "architecture_only_codes": list(incomplete),
                "phase20_candidate_id": candidate.candidate_id,
                "phase20_active_tool_count": len(candidate.active_ce2i_tools),
                "qualification_plan_id": plan.plan_id,
                "certification_claimed": False,
                "empirical_validation_still_required": True,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
