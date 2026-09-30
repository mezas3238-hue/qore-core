"""Collect sanitized cTrader DEMO account-capability evidence read-only."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from qore.infrastructure.cibo_ctrader_demo_account_capability import (
    CTraderDemoAccountCapabilityObservation,
    collect_ctrader_demo_account_capability,
)
from qore.infrastructure.cibo_ctrader_demo_instrument_taxonomy import (
    CTraderDemoInstrumentTaxonomyObservation,
    collect_ctrader_demo_instrument_taxonomy,
)
from qore.infrastructure.ctrader_demo_free_sink import (
    credentials_from_environment,
)
from qore.infrastructure.ctrader_open_api_client import (
    SpotwareCTraderOpenApiClient,
)


def build_report(
    observation: CTraderDemoAccountCapabilityObservation,
    taxonomy: CTraderDemoInstrumentTaxonomyObservation | None = None,
) -> dict[str, object]:
    """Sanitize one account-bound observation without leaking account id."""

    account_fingerprint = hashlib.sha256(
        observation.account_ref.encode("utf-8")
    ).hexdigest()
    symbols = [
        {
            **asdict(item),
        }
        for item in observation.symbols
    ]
    if taxonomy is not None:
        if taxonomy.account_ref != observation.account_ref:
            raise ValueError("taxonomy/account capability binding mismatch")
        if taxonomy.symbol_catalog_sha256 != observation.catalog_sha256:
            raise ValueError("taxonomy/symbol catalog binding mismatch")
    taxonomy_asset_classes = (
        [] if taxonomy is None else [asdict(item) for item in taxonomy.asset_classes]
    )
    taxonomy_categories = (
        []
        if taxonomy is None
        else [asdict(item) for item in taxonomy.symbol_categories]
    )
    option_candidates = (
        [] if taxonomy is None else list(taxonomy.option_taxonomy_candidates)
    )
    taxonomy_complete = (
        False if taxonomy is None else taxonomy.catalog_binding_complete
    )
    taxonomy_sha256 = None if taxonomy is None else taxonomy.taxonomy_sha256

    return {
        "schema": "qore.cibo.ctrader_demo.account_capability_probe.v2",
        "provider_key": "ctrader-demo",
        "environment": "demo",
        "account_fingerprint_sha256": account_fingerprint,
        "observed_at": observation.observed_at.isoformat(),
        "account_type": observation.account_type.value,
        "account_type_field_present": (
            observation.account_type_field_present
        ),
        "same_symbol_opposite_positions_supported": (
            observation.same_symbol_opposite_positions_supported
        ),
        "symbol_count": len(observation.symbols),
        "enabled_symbol_count": observation.enabled_symbol_count,
        "catalog_sha256": observation.catalog_sha256,
        "symbols": symbols,
        "taxonomy_sha256": taxonomy_sha256,
        "taxonomy_binding_complete": taxonomy_complete,
        "asset_classes": taxonomy_asset_classes,
        "symbol_categories": taxonomy_categories,
        "option_taxonomy_candidates": option_candidates,
        "broker_mutation_performed": observation.broker_mutation_performed,
        "t16_hedge_instrument_certified": (
            observation.t16_hedge_instrument_certified
        ),
        "t17_option_structure_certified": (
            observation.t17_option_structure_certified
        ),
        "productive_authority": observation.productive_authority,
        "status": "ACCOUNT_MODE_OBSERVED_T16_T17_NOT_CERTIFIED",
        "blockers": [
            "T16_ECONOMIC_HEDGE_EVIDENCE_REQUIRED",
            *(
                []
                if taxonomy_complete
                else ["T17_ACCOUNT_TAXONOMY_BINDING_INCOMPLETE"]
            ),
            "T17_OPTION_OR_DEFINED_RISK_INSTRUMENT_NOT_PROVIDER_VERIFIED",
        ],
    }


def collect_report() -> dict[str, object]:
    client = SpotwareCTraderOpenApiClient(
        credentials=credentials_from_environment(),
    )
    try:
        observation = collect_ctrader_demo_account_capability(client)
        taxonomy = collect_ctrader_demo_instrument_taxonomy(
            client,
            capability=observation,
        )
    finally:
        client.close()
    return build_report(observation, taxonomy)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = collect_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
