"""QORE Native source-only NAS100 vs USTEC IC Markets DEMO alias catalog probe.

A broker name is NOT a contract-equivalence proof. No market quote download,
order, OAuth refresh, PnL or production action is permitted.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.qore_native_icmarkets_bidask_source_pilot_v1 import (
    ReadOnlyTickPilot,
    SourceBlock,
)
from qore.infrastructure.trader_lab.qore_native_icmarkets_catalog_preflight_v1 import probe_catalog
from qore.infrastructure.trader_lab.qore_native_icmarkets_missing_m1_capture_v1 import _credentials
from qore.infrastructure.trader_lab.qore_native_universe_33_source_registry_v1 import (
    CANONICAL_ALIAS_HINTS,
)
from qore.kernel.result import Failure

IDENTITY = "QORE_NATIVE_G1_NAS100_USTEC_READONLY_BROKER_ALIAS_PREFLIGHT_V1"
ALLOWED = frozenset({"NAS100", "USTEC"})
if CANONICAL_ALIAS_HINTS.get("NAS100") != "USTEC":
    raise RuntimeError("HISTORICAL_PROVIDER_ALIAS_HINT_WITNESS_CHANGED")


def classify(entries: tuple[object, ...]) -> dict[str, Any]:
    """Only two names, with no missing-symbol inference from other CFDs."""
    found: dict[str, int] = {}
    for e in entries:
        name = getattr(e, "symbolName", None)
        if name not in ALLOWED:
            continue
        if name in found:
            raise SourceBlock("AMBIGUOUS_DUPLICATE_PROVIDER_NAMES")
        symid = getattr(e, "symbolId", None)
        if type(symid) is not int or symid <= 0:
            raise SourceBlock("INVALID_PROVIDER_SYMBOL_ID")
        if getattr(e, "enabled", None) is True:
            found[name] = symid
    if len(found) == 2:
        status = "BOTH_NAMES_ENABLED_AMBIGUOUS_NEEDS_CONTRACT_AUDIT"
    elif "NAS100" in found:
        status = "EXACT_NAS100_ENABLED_CONTRACT_STILL_UNVERIFIED"
    elif "USTEC" in found:
        status = "USTEC_ALIAS_CANDIDATE_NEEDS_CONTRACT_EQUIVALENCE"
    else:
        status = "NAS100_USTEC_NOT_ENABLED_OR_ABSENT"
    return {
        "status": status,
        "catalog_exact_candidates": found,
        "alias_historical_hint_only": "USTEC",
        "alias_equivalence_verified": False,
        "historical_execution_contract_verified": False,
    }


def _details(client: ReadOnlyTickPilot, symid: int) -> dict[str, Any]:
    result = client.request(
        "ProtoOASymbolByIdReq",
        {"ctidTraderAccountId": client.account_id, "symbolId": [symid]},
        client_msg_id="qore-native-identity-only-provider-symbol-detail",
        timeout_seconds=35.0,
    )
    if isinstance(result, Failure):
        raise SourceBlock("BROKER_SYMBOL_DETAILS_UNAVAILABLE")
    symbols = tuple(getattr(result.value, "symbol", ()))
    matching = [x for x in symbols if getattr(x, "symbolId", None) == symid]
    if len(matching) != 1:
        raise SourceBlock("BROKER_SYMBOL_DETAILS_AMBIGUOUS")
    detail = matching[0]
    witness: dict[str, Any] = {"symbol_id": symid}
    for attr in ("digits", "pipPosition", "lotSize", "minVolume", "stepVolume"):
        value = getattr(detail, attr, None)
        if type(value) is int and value >= 0:
            witness[attr] = value
    # These are source quote specs for the *current* DEMO contract only.
    witness["historical_original_CIBO_contract_equivalence_proven"] = False
    return witness


def inspect() -> dict[str, Any]:
    result: dict[str, Any] = {
        "identity": IDENTITY, "status": "SOURCE_PREFLIGHT_BLOCKED",
        "source": "ICMARKETS_CTRADER_DEMO", "read_only": True,
        "historical_alias_hint": "USTEC",
        "canonical": "NAS100",
        "alias_equivalence_verified": False, "NET_authorized": False,
        "native_bidask_fetched": False, "trade_orders_submitted": 0,
        "token_refresh_attempts": 0, "certified_traders": 0,
    }
    client: ReadOnlyTickPilot | None = None
    try:
        base = probe_catalog()
        if base.get("status") != "ICMARKETS_DEMO_CATALOG_VERIFIED":
            raise SourceBlock("ICMARKETS_DEMO_BROKER_UNVERIFIED")
        account = base.get("_ephemeral_account_id")
        if type(account) is not int or account <= 0 or base.get("account_is_live") is not False:
            raise SourceBlock("DEMO_ACCOUNT_UNVERIFIED")
        os.environ["QORE_CTRADER_DEMO_ACCOUNT_ID"] = str(account)
        os.environ.pop("QORE_CTRADER_ACCOUNT_ID", None)
        client = ReadOnlyTickPilot(credentials=_credentials(), request_timeout_seconds=35.0)
        conn = client.connect_and_authenticate()
        if isinstance(conn, Failure) or client.account_id != account:
            raise SourceBlock("DEMO_ACCOUNT_REAUTH_FAILURE")
        response = client.request(
            "ProtoOASymbolsListReq",
            {"ctidTraderAccountId": account, "includeArchivedSymbols": False},
            client_msg_id="qore-native-alias-only-symbol-catalog",
            timeout_seconds=35.0,
        )
        if isinstance(response, Failure):
            raise SourceBlock("BROKER_CATALOG_QUERY_FAILED")
        classified = classify(tuple(getattr(response.value, "symbol", ())))
        result.update(classified)
        details = {}
        for name, symid in classified["catalog_exact_candidates"].items():
            details[name] = _details(client, symid)
        result["current_demo_symbol_metadata"] = details
    except (SourceBlock, ValueError, RuntimeError, TypeError, OSError) as exc:
        fixed = {
            "ICMARKETS_DEMO_BROKER_UNVERIFIED", "DEMO_ACCOUNT_UNVERIFIED",
            "DEMO_ACCOUNT_REAUTH_FAILURE", "BROKER_CATALOG_QUERY_FAILED",
            "BROKER_SYMBOL_DETAILS_UNAVAILABLE", "BROKER_SYMBOL_DETAILS_AMBIGUOUS",
            "AMBIGUOUS_DUPLICATE_PROVIDER_NAMES", "INVALID_PROVIDER_SYMBOL_ID",
        }
        result["safe_blocker"] = str(exc) if type(exc) is SourceBlock and str(exc) in fixed else "ALIAS_PREFLIGHT_UNAVAILABLE"
    finally:
        if client is not None:
            client.close()
    return result


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("output", type=Path)
    args = p.parse_args()
    result = inspect()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "candidate_symbols": list(result.get("catalog_exact_candidates", {})),
        "NET_authorized": False, "certified_traders": 0,
        "safe_blocker": result.get("safe_blocker"),
    }, sort_keys=True))
    if result["status"] == "SOURCE_PREFLIGHT_BLOCKED":
        raise SystemExit(4)


if __name__ == "__main__":
    main()
