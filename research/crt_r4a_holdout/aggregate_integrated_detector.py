"""Aggregate historical integrated CRT events from 33 ORIGINAL M5 artifacts.

No trades, PnL, broker quotes, new holdout, or exact original Pine parity.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from research.crt_r4a_holdout.runner import SYMBOLS

ALIASES = {"NAS100": "USTEC", "SP500": "US500"}
SOURCE_STATUS = "INTEGRATED_RESEARCH_DETECTOR_NOT_PINE_PARITY"


def aggregate(root: Path) -> tuple[dict[str, Any], str]:
    paths = sorted(root.glob("qore-crt-r4a-integrated-*/integrated.json"))
    if len(paths) != 33:
        raise ValueError(f"33 historical source reports required, found {len(paths)}")
    records: list[dict[str, Any]] = []
    symbols: set[str] = set()
    for path in paths:
        row = json.loads(path.read_text(encoding="utf-8"))
        original = row.get("symbol")
        canonical = ALIASES.get(original, original)
        if (
            canonical not in SYMBOLS or canonical == "BTCUSD"
            or canonical in symbols
            or path.parent.name != f"qore-crt-r4a-integrated-{original}"
        ):
            raise ValueError("unexpected, duplicated or misnamed original symbol")
        if row.get("status") != SOURCE_STATUS:
            raise ValueError("unsupported status")
        for field in (
            "is_original_pine_f_engine", "holdout_certified",
            "trading_orders_permitted", "full_pine_f_engine_parity",
            "mss_with_exact_provider_phase_parity", "bid_ask_costs_included",
            "real_money_authorized",
        ):
            if row.get(field) is not False:
                raise ValueError("false certification: " + field)
        if row.get("trades_executed") != 0:
            raise ValueError("unexpected claimed trading orders")
        if (
            row.get("year_2024_2025_SHA256_verified") is not True
            or row.get("replay_period_used") != "2024_2025_ALREADY_RESEARCHED"
        ):
            raise ValueError("SHA or burned research window mismatch")
        if (
            row["source_m5_rows"] != row["stats"]["m5_processed"]
            or row["events_total"] != row["events_a"] + row["events_b"]
        ):
            raise ValueError("unreconciled event counts")
        years = row["events_per_year_model"]
        if any(not k.startswith(("2024_", "2025_")) for k in years):
            raise ValueError("signal outside prior research period")
        if sum(years.values()) != row["events_total"]:
            raise ValueError("year/model event mismatch")
        if (
            canonical != original
            and row["provider_cohort"] != "ATLAS_DEMO_BROKER_UNVERIFIED"
        ):
            raise ValueError("IC provider alias impersonation")
        row["canonical_symbol"] = canonical
        row["original_source_symbol"] = original
        symbols.add(canonical)
        records.append(row)
    if symbols != set(SYMBOLS) - {"BTCUSD"}:
        raise ValueError("immutable 33 market universe does not match")
    atlas = sum(
        r["provider_cohort"] == "ATLAS_DEMO_BROKER_UNVERIFIED"
        for r in records
    )
    ic = sum(
        r["provider_cohort"] == "ICMARKETS_DEMO_CONFIRMED"
        for r in records
    )
    if (atlas, ic) != (12, 21):
        raise ValueError("provider attribution mismatch")
    records.sort(key=lambda x: x["canonical_symbol"])
    totals = {
        "symbols": 33, "original_m5": sum(r["source_m5_rows"] for r in records),
        "events_a_2c_mss15": sum(r["events_a"] for r in records),
        "events_b_true3c_mss5": sum(r["events_b"] for r in records),
        "events_total": sum(r["events_total"] for r in records),
        "atlas_not_ic_certified": atlas, "ic_demo": ic, "trades_executed": 0,
    }
    result: dict[str, Any] = {
        "status": "33_REAL_M5_CRT_MSS_INTEGRATED_RESEARCH_ONLY",
        "period": "2024_2025_ALREADY_CONSUMED",
        "totals": totals, "by_symbol": records,
        "exact_pine_event_parity": False, "broker_net_pnl_measured": False,
        "virgin_holdout": False, "live_trading_permitted": False,
    }
    lines = [
        "# R4-A CRT/MSS causal integrado: 33 instrumentos, 2024–2025",
        "",
        "**Solo eventos, sin operaciones ni rentabilidad neta. "
        "No hay paridad exacta con TradingView ni holdout virgen.**",
        "",
        f"- M5 originales: **{totals['original_m5']:,}**.",
        f"- A: **{totals['events_a_2c_mss15']:,}** eventos 2C+MSS15.",
        f"- B: **{totals['events_b_true3c_mss5']:,}** eventos TRUE3C+MSS5.",
        f"- Total: **{totals['events_total']:,}**; cero trades.",
        "- 21 fuentes IC Markets DEMO, 12 Atlas no homologadas; BTCUSD falta.",
        "",
        "| Mercado | Fuente | M5 | Modelo A | Modelo B | Total |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for r in records:
        cohort = "Atlas no IC" if "ATLAS" in r["provider_cohort"] else "IC DEMO"
        if r["original_source_symbol"] != r["canonical_symbol"]:
            cohort += " (" + r["original_source_symbol"] + ")"
        lines.append(
            f"| {r['canonical_symbol']} | {cohort} | "
            f"{r['source_m5_rows']} | {r['events_a']} | "
            f"{r['events_b']} | {r['events_total']} |"
        )
    lines.extend([
        "",
        "Estos resultados provienen del motor de investigación, no de una "
        "exportación verificada del motor Pine original. Faltan validación "
        "de pivotes empatados y de fase M5 por feed, toda la lógica de "
        "7 familias, BTCUSD, costos y paridad evento por evento.",
        "",
        "Los años 2024–2025 están CONSUMIDOS. No reutilizarlos como nuevo holdout.",
        "",
    ])
    return result, "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--outdir", type=Path, required=True)
    args = p.parse_args()
    result, md = aggregate(args.root)
    args.outdir.mkdir(parents=True, exist_ok=True)
    (args.outdir / "summary.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.outdir / "summary.md").write_text(md, encoding="utf-8")
    print(json.dumps(result["totals"], sort_keys=True))


if __name__ == "__main__":
    main()
