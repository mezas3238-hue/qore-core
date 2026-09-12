"""R3.9 causal-program projection after final VT-08 source adjudication.

R3.8 remains frozen historical evidence. This module projects that program onto
the final source contract without rewriting consumed artifacts or authorizing a
performance-driven methodology mutation.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import cast

from qore.infrastructure.trader_lab.vt08_b01_causal_h01_h04_r3_8 import (
    Vt08B01CausalProgramError,
)
from qore.infrastructure.trader_lab.vt08_b01_causal_h01_h04_r3_8 import (
    compile_vt08_b01_causal_program as compile_r38_causal_program,
)
from qore.infrastructure.traders.vt08_b01_source_contract_r3_9 import (
    FORBIDDEN_REUSE,
    source_contract_fingerprint,
    source_contract_payload,
)

_SCHEMA = "qore.trader_lab.vt08_b01_causal_h01_h04.r3.9.v1"


def _object(value: object, *, name: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise Vt08B01CausalProgramError(f"{name} must be an object")
    return cast(dict[str, object], value)


def _array(value: object, *, name: str) -> list[object]:
    if type(value) is not list:
        raise Vt08B01CausalProgramError(f"{name} must be an array")
    return cast(list[object], value)


def compile_vt08_b01_causal_program_r3_9(path: Path) -> dict[str, object]:
    payload = compile_r38_causal_program(path)
    tracks = _array(payload.get("tracks"), name="tracks")
    by_id: dict[str, dict[str, object]] = {}
    for raw in tracks:
        track = _object(raw, name="track")
        hypothesis_id = track.get("hypothesis_id")
        if type(hypothesis_id) is not str:
            raise Vt08B01CausalProgramError("track hypothesis_id must be text")
        by_id[hypothesis_id] = track

    h01 = by_id.get("VT08-R3.8-FF-H01")
    h03 = by_id.get("VT08-R3.8-FF-H03")
    if h01 is None or h03 is None:
        raise Vt08B01CausalProgramError("R3.9 requires H01 and H03 tracks")

    h01["status"] = "SOURCE_ADJUDICATED_NO_PERFORMANCE_MUTATION"
    h01["source_adjudication"] = {
        "protected_swing_core": "SOURCE_EXPLICIT",
        "cisd_level": "SOURCE_EXPLICIT",
        "cisd_confirmation": "SOURCE_EXPLICIT",
        "cisd_series_minimum": "SOURCE_SUPPORTED_FORMALIZATION",
        "multiple_ps_selection": "FUNDAMENTALLY_UNRESOLVED",
        "stop_offset": "FUNDAMENTALLY_UNRESOLVED",
        "body_stop": "OPTIONAL_CONTEXTUAL_REFINEMENT_NOT_CORE_B01",
        "methodology_mutation_authorized": False,
    }

    h03["source_boundary"] = [
        "source-authorized Forex entry anchors are exactly 01/05/09 New York",
        "13:00 is not a source-authorized Forex entry anchor",
        "01/05/09/13/17/21 may be used only as a QORE H4 reconstruction grid",
        "05:00 is not source-authorized as a privileged winner",
    ]
    h03["fresh_diagnostics"] = [
        "pre-registered 01/05/09 source-anchor stratification",
        "bias case, C2/C3 class, PS geometry and volatility by anchor",
        "OOS/Stress survival by anchor without choosing the best after results",
        "do not generate a 13:00 entry cohort from reconstruction-grid hours",
    ]
    h03["prohibited_inference"] = [
        "do not change the Trader to 05:00-only from the frozen campaign",
        "do not treat 13:00 reconstruction-grid hour as an entry anchor",
        "do not invent a session filter from weekday/hour P&L",
    ]

    contract = source_contract_payload()
    holdout = _object(contract.get("fresh_holdout_governance"), name="holdout")
    execution = _object(contract.get("execution_authority"), name="execution")

    payload["schema"] = _SCHEMA
    payload["source_contract_version"] = contract["contract_version"]
    payload["source_contract_fingerprint"] = source_contract_fingerprint()
    payload["source_contract_frozen"] = True
    payload["h01_source_status"] = "SOURCE_ADJUDICATED_NO_PERFORMANCE_MUTATION"
    payload["fresh_holdout_governance"] = dict(holdout)
    payload["execution_authority"] = dict(execution)
    payload["forbidden_reuse"] = FORBIDDEN_REUSE
    payload["methodology_mutation_authorized"] = False
    payload["demo_eligible"] = False
    return payload


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 1:
        print(
            "usage: vt08_b01_causal_h01_h04_r3_9 <failure-forensics.json>",
            file=sys.stderr,
        )
        return 2
    try:
        payload = compile_vt08_b01_causal_program_r3_9(Path(arguments[0]))
    except Vt08B01CausalProgramError as error:
        print(f"VT-08 R3.9 causal program failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
