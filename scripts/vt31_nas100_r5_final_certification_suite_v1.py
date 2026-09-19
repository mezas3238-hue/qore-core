"""Final certification suite for frozen VT31_NAS100_R5.

Consumes exactly one previously sealed two-year fresh holdout and evaluates only
the already frozen economic identity.  No parameter search, ranking, retuning,
or alternative policy comparison is permitted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_r5_certification_candidate as candidate

SCHEMA = "qore.vt31.nas100.r5.final_certification_suite.v1"
IDENTITY = "VT31_NAS100_R5_FINAL_CERTIFICATION_SUITE_V1"
EXTRA_COSTS = (
    Decimal("0.01"),
    Decimal("0.02"),
    Decimal("0.05"),
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _stress_rows(
    rows: list[dict[str, object]],
    *,
    extra_source_cost_r: Decimal,
) -> list[dict[str, object]]:
    stressed: list[dict[str, object]] = []
    for row in rows:
        requested_risk = _d(row["requested_risk_r"])
        net = _d(row["capital_weighted_net_r"])
        updated = dict(row)
        updated["capital_weighted_net_r"] = format(
            net - requested_risk * extra_source_cost_r,
            "f",
        )
        updated["extra_source_cost_r"] = format(
            extra_source_cost_r,
            "f",
        )
        stressed.append(updated)
    return stressed


def _annual_blocks(
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    boundaries = (
        (date(2022, 7, 18), date(2023, 7, 18)),
        (date(2023, 7, 18), date(2024, 7, 18)),
    )
    result: list[dict[str, object]] = []
    for index, (start, end) in enumerate(boundaries, start=1):
        selected = [
            row
            for row in rows
            if start
            <= date.fromisoformat(cast(str, row["local_date"]))
            < end
        ]
        metrics = candidate.engine._capital_metrics(selected)
        result.append(
            {
                "year_block": index,
                "start_date": start.isoformat(),
                "end_exclusive_date": end.isoformat(),
                "trade_count": len(selected),
                "metrics": metrics,
                "positive": (
                    len(selected) > 0
                    and _d(metrics["total_r"]) > 0
                    and _d(metrics["mean_r"]) > 0
                ),
            }
        )
    return result


def _validate_evidence_contract(
    payload: dict[str, object],
) -> None:
    expected = {
        "evidence_purpose": candidate.FINAL_HOLDOUT_ID,
        "candidate_id": candidate.CANDIDATE_ID,
        "candidate_contract_fingerprint": candidate.contract_fingerprint(),
        "market": candidate.MARKET,
        "final_holdout_start_at": candidate.FINAL_HOLDOUT_START,
        "final_holdout_end_exclusive": (
            candidate.FINAL_HOLDOUT_END_EXCLUSIVE
        ),
        "selected_before_open": True,
        "overlaps_consumed_vt31_cibo_evidence": False,
        "opened_once": True,
        "fresh_before_this_acquisition": True,
        "may_be_called_fresh_again": False,
        "retuning_on_same_interval_allowed": False,
        "coverage_sufficient": True,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise ValueError(
                f"final holdout evidence contract mismatch: {key}"
            )


def certify(evidence_path: Path) -> dict[str, object]:
    evidence_raw = json.loads(evidence_path.read_text(encoding="utf-8"))
    if not isinstance(evidence_raw, dict):
        raise ValueError("final holdout payload must be an object")
    evidence = cast(dict[str, object], evidence_raw)
    _validate_evidence_contract(evidence)

    replay = candidate.replay(evidence_path)
    if replay["candidate_frozen"] is not True:
        raise ValueError("candidate is not frozen")
    if replay["reference_variant"] != candidate.REFERENCE_VARIANT:
        raise ValueError("certification replay variant drift")

    result = cast(dict[str, object], replay["result"])
    rows = cast(list[dict[str, object]], result["trade_rows"])
    if len(rows) != int(cast(int, result["trade_count"])):
        raise ValueError("certification trade-row count drift")

    metrics = cast(dict[str, object], result["metrics"])
    mc = cast(dict[str, object], result["monte_carlo"])
    annual = _annual_blocks(rows)

    stress: dict[str, dict[str, object]] = {}
    for cost in EXTRA_COSTS:
        tag = format(cost, "f")
        stressed_rows = _stress_rows(
            rows,
            extra_source_cost_r=cost,
        )
        stress[tag] = {
            "extra_source_cost_r": tag,
            "metrics": candidate.engine._capital_metrics(stressed_rows),
            "monte_carlo": candidate.engine._monte_carlo(
                stressed_rows,
                variant=f"{candidate.CANDIDATE_ID}:stress:{tag}",
            ),
        }

    gates = candidate.FINAL_CERTIFICATION_GATES
    trade_count = len(rows)
    pf = metrics["profit_factor"]
    stress_001 = cast(dict[str, object], stress["0.01"]["metrics"])
    stress_002 = cast(dict[str, object], stress["0.02"]["metrics"])
    stress_005 = cast(dict[str, object], stress["0.05"]["metrics"])

    certification_gates = {
        "frozen_identity_exact": (
            replay["candidate_id"] == candidate.CANDIDATE_ID
            and replay["contract_fingerprint"]
            == candidate.contract_fingerprint()
        ),
        "only_preselected_variant_evaluated": (
            replay["reference_variant"] == candidate.REFERENCE_VARIANT
            and replay["engine_governance"].get(
                "fixed_activity_profile"
            )
            == "ACTIVITY_L"
            and replay["engine_governance"].get(
                "fixed_global_risk_scalar"
            )
            == "0.60"
        ),
        "sample_min": trade_count >= int(
            cast(int, gates["terminal_sample_min"])
        ),
        "sample_max": trade_count <= int(
            cast(int, gates["terminal_sample_max"])
        ),
        "profit_factor_min": (
            pf is not None
            and _d(pf) >= _d(gates["profit_factor_min"])
        ),
        "mean_positive": (
            _d(metrics["mean_r"])
            > _d(gates["mean_r_min_exclusive"])
        ),
        "total_positive": (
            _d(metrics["total_r"])
            > _d(gates["total_r_min_exclusive"])
        ),
        "observed_dd_at_most_6r": (
            _d(metrics["max_drawdown_r"])
            <= _d(gates["observed_max_drawdown_r_max"])
        ),
        "all_two_annual_blocks_positive": (
            len(annual) == 2
            and all(bool(block["positive"]) for block in annual)
        ),
        "mc_positive_terminal_min": (
            _d(mc["positive_terminal_probability"])
            >= _d(
                gates["mc_positive_terminal_probability_min"]
            )
        ),
        "mc_p95_dd_max": (
            _d(mc["p95_max_drawdown_r"])
            <= _d(gates["mc_p95_max_drawdown_r_max"])
        ),
        "stress_001_positive_pf_1_40_dd_6_5": (
            _d(stress_001["total_r"]) > 0
            and stress_001["profit_factor"] is not None
            and _d(stress_001["profit_factor"]) >= Decimal("1.40")
            and _d(stress_001["max_drawdown_r"]) <= Decimal("6.50")
        ),
        "stress_002_positive_pf_1_30_dd_7": (
            _d(stress_002["total_r"]) > 0
            and stress_002["profit_factor"] is not None
            and _d(stress_002["profit_factor"]) >= Decimal("1.30")
            and _d(stress_002["max_drawdown_r"]) <= Decimal("7.00")
        ),
        "stress_005_remains_positive": (
            _d(stress_005["total_r"]) > 0
            and stress_005["profit_factor"] is not None
            and _d(stress_005["profit_factor"]) > Decimal("1.00")
        ),
    }
    certified = all(certification_gates.values())

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "candidate_id": candidate.CANDIDATE_ID,
        "candidate_contract_fingerprint": candidate.contract_fingerprint(),
        "reference_variant": candidate.REFERENCE_VARIANT,
        "holdout": {
            "id": candidate.FINAL_HOLDOUT_ID,
            "start_at": candidate.FINAL_HOLDOUT_START,
            "end_exclusive": candidate.FINAL_HOLDOUT_END_EXCLUSIVE,
            "evidence_sha256": hashlib.sha256(
                evidence_path.read_bytes()
            ).hexdigest(),
            "status_after_run": (
                "CONSUMED_FINAL_CERTIFICATION_HOLDOUT"
            ),
            "fresh_reuse_allowed": False,
        },
        "result": {
            "trade_count": trade_count,
            "base_trade_count": result["base_trade_count"],
            "rearm_trade_count": result["rearm_trade_count"],
            "metrics": metrics,
            "monte_carlo": mc,
            "annual_blocks": annual,
            "stress": stress,
        },
        "certification_gates": certification_gates,
        "trader_certified": certified,
        "certification_decision": (
            "TRADER_CERTIFIED" if certified else "REJECTED_FINAL_HOLDOUT"
        ),
        "development_binding": {
            "five_year_run_id": candidate.DEVELOPMENT_5Y_RUN_ID,
            "five_year_artifact_id": candidate.DEVELOPMENT_5Y_ARTIFACT_ID,
            "five_year_artifact_zip_sha256": (
                candidate.DEVELOPMENT_5Y_ARTIFACT_ZIP_SHA256
            ),
        },
        "governance": {
            "parameter_scan_on_holdout": False,
            "retuning_after_holdout_open": False,
            "holdout_consumed_permanently": True,
            "certification_may_authorize_runtime_integration": certified,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
            "order_submission_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = certify(args.evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "candidate_id": payload["candidate_id"],
                "holdout": payload["holdout"],
                "result": payload["result"],
                "certification_gates": payload["certification_gates"],
                "trader_certified": payload["trader_certified"],
                "certification_decision": payload[
                    "certification_decision"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
