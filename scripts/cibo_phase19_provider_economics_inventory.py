"""Build the sealed Phase-19 historical provider-economics evidence inventory.

This consumes the same seven immutable Phase-18 bound-trade ledgers as the
integrated chronology replay. It records exactly which broker-economic fields
are retained in those causal rows and keeps historical USD replay fail-closed
when they are absent.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from cibo_phase19_integrated_chronology_replay import (
    EXPECTED_SOURCE_ROWS,
    SOURCE_SPECS,
    _jsonl,
)
from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_chronological_replay import (
    ReplayEconomicsStatus,
)
from qore.infrastructure.cibo_ce2i_phase19_portfolio_replay import (
    PHASE19_REQUIRED_TRADERS,
    Phase19ProviderEconomicsEvidence,
    Phase19ReadinessStatus,
    Phase19TraderEvidence,
    ProviderEconomicsEvidenceClass,
    assess_phase19_readiness,
)
from qore.infrastructure.cibo_ce2i_phase19_provider_evidence_audit import (
    HISTORICAL_PROVIDER_ECONOMIC_FIELDS,
    HistoricalProviderEconomicsRowAudit,
    audit_historical_provider_economics_rows,
)

EXPECTED_ROW_ECONOMICS_STATUS = ("R_DENOMINATED_ONLY",)


def build_inventory(
    *,
    paths: dict[str, Path],
    output_path: Path,
) -> dict[str, Any]:
    if set(paths) != set(SOURCE_SPECS):
        raise ValueError("Phase 19 provider-evidence source set drift")

    audits: dict[TraderLineage, HistoricalProviderEconomicsRowAudit] = {}
    trader_evidence: list[Phase19TraderEvidence] = []
    for key, spec in SOURCE_SPECS.items():
        rows = _jsonl(paths[key])
        expected_rows = EXPECTED_SOURCE_ROWS[spec.trader_id]
        if len(rows) != expected_rows:
            raise ValueError(
                f"{spec.trader_id.value} provider audit source row-count drift"
            )

        audit = audit_historical_provider_economics_rows(rows)
        if audit.economics_status_values != EXPECTED_ROW_ECONOMICS_STATUS:
            raise ValueError(
                f"{spec.trader_id.value} historical economics status drift"
            )
        if audit.exact_historical_usd_replay_supported:
            raise ValueError(
                f"{spec.trader_id.value} unexpectedly supports exact USD replay"
            )
        if set(audit.missing_fields) != set(HISTORICAL_PROVIDER_ECONOMIC_FIELDS):
            raise ValueError(
                f"{spec.trader_id.value} provider-field retention changed"
            )
        audits[spec.trader_id] = audit

        missing = ProviderEconomicsEvidenceClass.MISSING
        provider_evidence = Phase19ProviderEconomicsEvidence(
            trader_id=spec.trader_id,
            provider_key="HISTORICAL_PROVIDER_UNBOUND",
            evidence_id=(
                f"github-actions:phase18:{spec.artifact_id}:"
                f"{spec.artifact_digest}:bound-row-audit"
            ),
            contract_terms=missing,
            tick_value=missing,
            spread=missing,
            commission=missing,
            slippage=missing,
            margin=missing,
        )
        trader_evidence.append(
            Phase19TraderEvidence(
                trader_id=spec.trader_id,
                evidence_id=provider_evidence.evidence_id,
                row_count=audit.row_count,
                economics_status=ReplayEconomicsStatus.R_DENOMINATED_ONLY,
                provider_economics=provider_evidence,
            )
        )

    readiness = assess_phase19_readiness(tuple(trader_evidence))
    if readiness.status is not Phase19ReadinessStatus.BLOCKED_PROVIDER_ECONOMICS:
        raise ValueError("Phase 19 provider-evidence blocker unexpectedly changed")
    if readiness.usd_portfolio_replay_authorized:
        raise ValueError("historical USD replay must remain fail-closed")
    if readiness.cross_trader_r_aggregation_authorized:
        raise ValueError("cross-Trader R aggregation must remain forbidden")

    inventory: dict[str, Any] = {
        "schema": "qore.cibo.phase19.provider_economics_evidence_inventory.v1",
        "identity": "CIBO_PHASE19_PROVIDER_ECONOMICS_EVIDENCE_INVENTORY_V1",
        "status": readiness.status.value,
        "audit_scope": (
            "sealed_phase18_bound_trade_rows_only_exact_field_retention"
        ),
        "required_exact_historical_fields": list(
            HISTORICAL_PROVIDER_ECONOMIC_FIELDS
        ),
        "traders": {
            trader.value: {
                "row_count": audits[trader].row_count,
                "row_economics_status_values": list(
                    audits[trader].economics_status_values
                ),
                "exact_historical_usd_replay_supported": (
                    audits[trader].exact_historical_usd_replay_supported
                ),
                "missing_exact_historical_fields": list(
                    audits[trader].missing_fields
                ),
                "evidence_classification": {
                    "contract_terms": "MISSING",
                    "tick_value": "MISSING",
                    "spread": "MISSING",
                    "commission": "MISSING",
                    "slippage": "MISSING",
                    "margin": "MISSING",
                },
            }
            for trader in PHASE19_REQUIRED_TRADERS
        },
        "readiness": {
            "phase18_population_complete": (
                readiness.phase18_population_complete
            ),
            "chronology_replay_authorized": (
                readiness.chronology_replay_authorized
            ),
            "usd_portfolio_replay_authorized": (
                readiness.usd_portfolio_replay_authorized
            ),
            "cross_trader_r_aggregation_authorized": (
                readiness.cross_trader_r_aggregation_authorized
            ),
            "provider_economics_incomplete": [
                trader.value
                for trader in readiness.provider_economics_incomplete
            ],
        },
        "source_evidence": {
            key: {
                "trader_id": spec.trader_id.value,
                "artifact_id": spec.artifact_id,
                "artifact_digest": spec.artifact_digest,
            }
            for key, spec in SOURCE_SPECS.items()
        },
        "governance": {
            "absence_promoted_to_estimated_value": False,
            "current_snapshot_promoted_to_history": False,
            "provider_economics_fabricated": False,
            "historical_usd_replay_authorized": False,
            "cross_trader_r_aggregation_performed": False,
            "demo_execution_authorized": False,
            "live_authorized": False,
            "real_capital_authorized": False,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(inventory, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return inventory


def main() -> None:
    parser = argparse.ArgumentParser()
    for key in SOURCE_SPECS:
        parser.add_argument(f"--{key}", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = {key: getattr(args, key) for key in SOURCE_SPECS}
    print(
        json.dumps(
            build_inventory(paths=paths, output_path=args.output),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
