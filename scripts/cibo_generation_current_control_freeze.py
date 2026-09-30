"""Generate the immutable pre-C8 CIBO current-generation control manifest.

The exact control Git SHA is intentionally older than this generator: the
generator exists in N+1 research tooling and seals the already-selected N
identity. It cannot silently move the control forward.

No broker/runtime action is performed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_generation_current_control import (
    CIBO_CURRENT_CONTROL_ID,
    seal_current_generation_control,
)

BASELINE_GIT_SHA = "87d98ced8d56b275823c4472392923ba6a11d769"
SEALED_AT = datetime(2026, 9, 30, 0, 30, tzinfo=UTC)
EXPECTED_REQUIRED_RUN_COUNT = 26

CI_EVIDENCE_PATH = Path(
    "docs/research/CIBO-GENERATION-CURRENT-CONTROL-CI-EVIDENCE-V1.json"
)
OUTPUT_PATH = Path("artifacts/cibo_generation_current_control_v1.json")

TRADER_SURFACE_PATHS = (
    "src/qore/infrastructure/cibo_trader_opportunity_adapter.py",
    "src/qore/infrastructure/r34_xauusd_live.py",
    "src/qore/infrastructure/r38_eurusd_live.py",
    "src/qore/infrastructure/r43_gbpusd_live.py",
    "src/qore/infrastructure/r38_gbpjpy_live.py",
    "src/qore/infrastructure/r42_audjpy_live.py",
    "src/qore/infrastructure/vt31_nas100_live.py",
    "src/qore/infrastructure/ctrader_demo_vt08_sizing.py",
)

PROVIDER_CAPABILITY_PATHS = (
    "src/qore/infrastructure/cibo_provider_economic_normalization.py",
    "src/qore/infrastructure/cibo_instrument_capability_registry.py",
    "src/qore/infrastructure/cibo_ctrader_demo_provider_economics.py",
    "src/qore/infrastructure/cibo_fundednext_provider.py",
)

CAPITAL_STATE_PATHS = (
    "src/qore/infrastructure/cibo_capital_source_ledger.py",
    "src/qore/infrastructure/cibo_capital_source_ledger_store.py",
    "src/qore/infrastructure/cibo_compound_capital.py",
    "src/qore/infrastructure/cibo_compound_portfolio_ledger.py",
    "src/qore/infrastructure/cibo_compound_portfolio_store.py",
    "src/qore/infrastructure/cibo_compound_floor.py",
    "src/qore/infrastructure/cibo_compound_floor_store.py",
    "src/qore/infrastructure/cibo_core_compound_portfolio.py",
)

CAPITAL_UTILIZATION_PATHS = (
    "src/qore/infrastructure/cibo_ce2i_phase20_forward_snapshots.py",
    "src/qore/infrastructure/cibo_ce2i_portfolio_allocation_ledger.py",
    "src/qore/infrastructure/cibo_ce2i_portfolio_allocation_store.py",
    "src/qore/infrastructure/cibo_t20_capital_release_evidence.py",
    "src/qore/infrastructure/cibo_internal_capital_market.py",
    "src/qore/infrastructure/cibo_internal_capital_market_population.py",
)

MISSION_PATH = (
    "docs/research/"
    "CIBO-SOVEREIGN-CAPITAL-AMPLIFICATION-WORLD-CUP-MISSION-V1.md"
)
GAP_MATRIX_PATH = (
    "docs/research/"
    "CIBO-WORLD-CUP-SOVEREIGN-CAPITAL-AMPLIFICATION-GAP-MATRIX-V1.md"
)


def _sha256_payload(value: object) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _surface_identity(paths: tuple[str, ...]) -> str:
    """Bind exact path set to exact baseline commit without reading N+1 files."""

    return _sha256_payload(
        {
            "git_sha": BASELINE_GIT_SHA,
            "paths": sorted(paths),
        }
    )


def _load_ci_evidence() -> tuple[str, dict[str, object]]:
    try:
        payload = json.loads(CI_EVIDENCE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CiboCompoundCapitalError(
            "current control CI evidence is unreadable"
        ) from error
    if not isinstance(payload, dict):
        raise CiboCompoundCapitalError(
            "current control CI evidence must be object"
        )
    if payload.get("schema") != (
        "CIBO_GENERATION_CURRENT_CONTROL_CI_EVIDENCE_V1"
    ):
        raise CiboCompoundCapitalError(
            "current control CI evidence schema mismatch"
        )
    if payload.get("control_id") != CIBO_CURRENT_CONTROL_ID:
        raise CiboCompoundCapitalError(
            "current control CI evidence identity drift"
        )
    if payload.get("git_sha") != BASELINE_GIT_SHA:
        raise CiboCompoundCapitalError(
            "current control CI evidence Git SHA drift"
        )
    if payload.get("required_run_count") != EXPECTED_REQUIRED_RUN_COUNT:
        raise CiboCompoundCapitalError(
            "current control CI required run count drift"
        )
    if payload.get("all_required_ci_green") is not True:
        raise CiboCompoundCapitalError(
            "current control CI evidence is not all green"
        )
    workflows = payload.get("workflows")
    if not isinstance(workflows, list):
        raise CiboCompoundCapitalError(
            "current control CI workflow evidence must be list"
        )
    if len(workflows) != EXPECTED_REQUIRED_RUN_COUNT:
        raise CiboCompoundCapitalError(
            "current control CI workflow evidence count drift"
        )
    ids: list[int] = []
    names: list[str] = []
    canonical_rows: list[dict[str, object]] = []
    for row in workflows:
        if not isinstance(row, dict):
            raise CiboCompoundCapitalError(
                "current control CI workflow row invalid"
            )
        run_id = row.get("id")
        name = row.get("name")
        if (
            not isinstance(run_id, int)
            or isinstance(run_id, bool)
            or run_id <= 0
            or not isinstance(name, str)
            or not name
        ):
            raise CiboCompoundCapitalError(
                "current control CI workflow identity invalid"
            )
        if (
            row.get("status") != "completed"
            or row.get("conclusion") != "success"
        ):
            raise CiboCompoundCapitalError(
                "current control CI workflow is not successful"
            )
        ids.append(run_id)
        names.append(name)
        canonical_rows.append(
            {
                "id": run_id,
                "name": name,
                "status": "completed",
                "conclusion": "success",
            }
        )
    if len(ids) != len(set(ids)) or len(names) != len(set(names)):
        raise CiboCompoundCapitalError(
            "current control CI workflow identities must be unique"
        )
    canonical = {
        "git_sha": BASELINE_GIT_SHA,
        "workflows": sorted(
            canonical_rows,
            key=lambda item: str(item["name"]),
        ),
    }
    typed_payload: dict[str, object] = {
        str(key): value for key, value in payload.items()
    }
    return _sha256_payload(canonical), typed_payload


def build_current_control_payload() -> dict[str, object]:
    workflow_sha, ci_payload = _load_ci_evidence()
    manifest = seal_current_generation_control(
        git_sha=BASELINE_GIT_SHA,
        sealed_at=SEALED_AT,
        trader_surface_sha256=_surface_identity(TRADER_SURFACE_PATHS),
        provider_capability_snapshot_sha256=_surface_identity(
            PROVIDER_CAPABILITY_PATHS
        ),
        capital_state_snapshot_sha256=_surface_identity(
            CAPITAL_STATE_PATHS
        ),
        capital_utilization_snapshot_sha256=_surface_identity(
            CAPITAL_UTILIZATION_PATHS
        ),
        workflow_evidence_sha256=workflow_sha,
        world_cup_mission_sha256=_surface_identity((MISSION_PATH,)),
        world_cup_gap_matrix_sha256=_surface_identity((GAP_MATRIX_PATH,)),
        all_required_ci_green=True,
        holdout_2017h1_untouched=True,
        economic_baseline_measurement_bound=False,
        economic_baseline_measurement_blockers=(
            "FRESH_AS_IS_ECONOMIC_POPULATION_REQUIRED",
        ),
    )
    manifest_payload = asdict(manifest)
    for name in (
        "sealed_at",
        "genc5_frozen_at",
        "genc6_frozen_at",
        "genc7_frozen_at",
    ):
        manifest_payload[name] = getattr(manifest, name).isoformat()
    manifest_payload["economic_baseline_measurement_blockers"] = list(
        manifest.economic_baseline_measurement_blockers
    )
    return {
        "schema": "CIBO_GENERATION_CURRENT_CONTROL_SEAL_V1",
        "manifest": manifest_payload,
        "manifest_sha256": manifest.fingerprint(),
        "surface_identity_semantics": (
            "sha256({git_sha, sorted path set}); Git SHA fixes exact content"
        ),
        "surface_paths": {
            "trader_surface": list(TRADER_SURFACE_PATHS),
            "provider_capability": list(PROVIDER_CAPABILITY_PATHS),
            "capital_state": list(CAPITAL_STATE_PATHS),
            "capital_utilization": list(CAPITAL_UTILIZATION_PATHS),
            "world_cup_mission": [MISSION_PATH],
            "world_cup_gap_matrix": [GAP_MATRIX_PATH],
        },
        "ci_evidence": ci_payload,
        "economic_baseline_measurement": {
            "bound": False,
            "blockers": [
                "FRESH_AS_IS_ECONOMIC_POPULATION_REQUIRED",
            ],
            "synthetic_measurement_used": False,
        },
        "n_plus_one_quarantine": {
            "genc8_or_later_may_engineer_in_shadow": True,
            "economic_value_claim_before_baseline_binding": False,
            "promotion_before_baseline_binding": False,
        },
    }


def main() -> int:
    payload = build_current_control_payload()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
