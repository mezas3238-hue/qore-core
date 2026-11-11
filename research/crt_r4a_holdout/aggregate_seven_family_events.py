"""Fail-closed consolidation of seven research CRT event streams on original M5."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from research.crt_r4a_holdout.runner import SYMBOLS
from research.crt_r4a_holdout.seven_family_contract import Family

ALIASES = {"NAS100": "USTEC", "SP500": "US500"}
ATLAS = frozenset({
    "AUDJPY", "GBPUSD", "GBPJPY", "XAUUSD", "USTEC", "US500",
    "US30", "AUDUSD", "USDCAD", "USDJPY", "EURUSD", "XAGUSD",
})
FAMILIES = tuple(f.value for f in Family)
A = (Family.TWO_C_MSS_C2.value, Family.TWO_C_MSS_C3.value)
B = Family.TRUE_3C.value
OWNED = (
    Family.INSIDE_RETURN.value,
    Family.MULTI4.value,
    Family.MULTIN.value,
)
RETEST = Family.M15_RETEST.value


def validate(row: dict[str, Any], path: Path) -> dict[str, Any]:
    raw = row.get("symbol")
    canonical = ALIASES.get(raw, raw)
    if (
        canonical not in SYMBOLS or canonical == "BTCUSD"
        or path.parent.name != f"qore-crt-r4a-seven-{raw}"
    ):
        raise ValueError("invalid original seven-family source identity")
    provider = (
        "ATLAS_DEMO_BROKER_UNVERIFIED" if canonical in ATLAS
        else "ICMARKETS_DEMO_CONFIRMED"
    )
    if row.get("provider_cohort") != provider:
        raise ValueError("broker/provenance mismatch")
    if (
        row.get("status") != "INTEGRATED_RESEARCH_DETECTOR_NOT_PINE_PARITY"
        or row.get("seven_families_registered") != 7
        or row.get("family_signals_integrated") != 7
    ):
        raise ValueError("not a seven-model experimental detector result")
    counts = row.get("seven_family_research_event_counts", {})
    if set(counts) != set(FAMILIES):
        raise ValueError("exactly seven family IDs required")
    if any(type(v) is not int or v < 0 for v in counts.values()):
        raise ValueError("invalid research event counts")
    if (
        counts[A[0]] + counts[A[1]] != row.get("events_a")
        or counts[B] != row.get("events_b")
        or row.get("events_total") != row["events_a"] + row["events_b"]
    ):
        raise ValueError("2C C2/C3 or TRUE3C source count mismatch")
    secondary = row.get("secondary_family_own_mss_audit", {})
    owned = secondary.get("family_events", {})
    if any(counts[key] != owned.get(key) for key in OWNED):
        raise ValueError("secondary MSS provenance mismatch")
    if sum(owned.values()) != secondary.get("total_extra_mss15_events"):
        raise ValueError("secondary owned MSS count does not balance")
    geometry = row.get("secondary_family_geometry_audit", {})
    retests = geometry.get("family_geometry_event_counts", {}).get(RETEST)
    if counts[RETEST] != retests:
        raise ValueError("retest not linked to same parent CRT MSS15")
    if (
        sum(counts.values()) != (
            row["events_total"] + secondary["total_extra_mss15_events"]
            + counts[RETEST]
        )
    ):
        raise ValueError("seven-model count reconciliation failed")
    for key in (
        "is_original_pine_f_engine", "holdout_certified",
        "trading_orders_permitted", "full_pine_f_engine_parity",
        "mss_with_exact_provider_phase_parity", "bid_ask_costs_included",
        "real_money_authorized",
    ):
        if row.get(key) is not False:
            raise ValueError("false economic/Pine certification: " + key)
    if (
        row.get("trades_executed") != 0
        or row.get("year_2024_2025_SHA256_verified") is not True
        or row.get("replay_period_used") != "2024_2025_ALREADY_RESEARCHED"
        or row.get("source_m5_rows") != row.get("stats", {}).get("m5_processed")
    ):
        raise ValueError("unverified historical source or broker-order claim")
    yearly = row.get("events_per_year_model", {})
    if (
        sum(yearly.values()) != row.get("events_total")
        or any(not k.startswith(("2024_", "2025_")) for k in yearly)
    ):
        raise ValueError("historical year reconciliation mismatch")
    row["canonical_symbol"] = canonical
    row["original_symbol"] = raw
    return row


def aggregate(root: Path) -> tuple[dict[str, Any], str]:
    paths = sorted(root.glob("qore-crt-r4a-seven-*/integrated.json"))
    if len(paths) != 33:
        raise ValueError("expected 33 independent original M5 event reports")
    rows = [
        validate(json.loads(p.read_text(encoding="utf-8")), p)
        for p in paths
    ]
    names = [r["canonical_symbol"] for r in rows]
    if set(names) != set(SYMBOLS) - {"BTCUSD"} or len(set(names)) != 33:
        raise ValueError("source market universe duplicate or incomplete")
    count_atlas = sum("ATLAS" in r["provider_cohort"] for r in rows)
    if count_atlas != 12:
        raise ValueError("12 Atlas source-provenance invariant broken")
    rows.sort(key=lambda r: r["canonical_symbol"])
    by_family = {
        fam: sum(r["seven_family_research_event_counts"][fam] for r in rows)
        for fam in FAMILIES
    }
    total_m5 = sum(r["source_m5_rows"] for r in rows)
    totals = {
        "markets": 33, "native_m5": total_m5,
        "family_counts_overlapping_not_trades": by_family,
        "family_event_sum_not_unique_trades": sum(by_family.values()),
        "atlas_not_ic_certified": count_atlas,
        "ic_markets_demo_original": 33 - count_atlas,
        "broker_orders_executed": 0,
    }
    report: dict[str, Any] = {
        "status": "SEVEN_FAMILY_REAL_M5_RESEARCH_ONLY_33",
        "period": "2024_2025_ALREADY_CONSUMED",
        "totals": totals, "by_symbol": rows,
        "broker_net_pnl": None, "broker_profit_factor": None,
        "full_pine_engine_parity_proven": False,
        "virgin_holdout": False, "real_trading_authorized": False,
    }
    lines = [
        "# Siete familias CRT — 33 fuentes originales M5 (2024–2025)",
        "",
        "**SOLO EVENTOS; NO OPERACIONES NI R/PF/DD. No certifica Pine.**",
        "",
        f"Mercados: 33/34, M5 reales: {total_m5:,}. BTCUSD falta.",
        f"Eventos de siete familias (se superponen): "
        f"{totals['family_event_sum_not_unique_trades']:,}.",
        "",
        "| Familia de investigación | Observaciones |",
        "|---|---:|",
    ]
    for family in FAMILIES:
        lines.append(f"| {family} | {by_family[family]:,} |")
    lines.extend([
        "",
        "## Todos los mercados",
        "",
        "| Símbolo | Fuente | M5 | " + " | ".join(FAMILIES) + " |",
        "|---|---|---:|" + "---:|" * len(FAMILIES),
    ])
    for row in rows:
        provider = (
            "Atlas no homologado IC" if "ATLAS" in row["provider_cohort"]
            else "IC Markets DEMO"
        )
        if row["canonical_symbol"] != row["original_symbol"]:
            provider += " (" + row["original_symbol"] + ")"
        numbers = " | ".join(
            str(row["seven_family_research_event_counts"][key])
            for key in FAMILIES
        )
        lines.append(
            f"| {row['canonical_symbol']} | {provider} | "
            f"{row['source_m5_rows']} | {numbers} |"
        )
    lines.extend([
        "",
        "Las familias tienen fuentes propias y confirmaciones de investigación, "
        "pero no paridad original f_engine, costos ni ejecuciones broker. "
        "Las tres categorías QA Pending/Expansion/Inside-Continuation "
        "siguen NO operables. El período 2024–2025 está CONSUMIDO.",
        "",
    ])
    return report, "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--outdir", type=Path, required=True)
    args = p.parse_args()
    report, md = aggregate(args.root)
    args.outdir.mkdir(parents=True, exist_ok=True)
    (args.outdir / "summary.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.outdir / "summary.md").write_text(md, encoding="utf-8")
    print(json.dumps(report["totals"], sort_keys=True))


if __name__ == "__main__":
    main()
