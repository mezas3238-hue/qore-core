"""Aggregate 33 genuine broker M5 proxy summaries; no exact Pine parity or costs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from research.crt_r4a_holdout.runner import SYMBOLS

MODELS = ("A_2C_MSS15_PROXY", "B_TRUE3C_MSS5_PROXY")
SOURCE_RUN = 43094233453
# Only hypothetical price-equivalent costs expressed as R per closed trade.
# These are NOT broker spreads/commission/slippage or a net backtest.
COST_STRESS_R = (0.0, 0.02, 0.05, 0.10, 0.20)


def fmt(x: float | None, n: int = 2) -> str:
    return "—" if x is None else f"{x:.{n}f}"


def aggregate(root: Path) -> tuple[dict[str, Any], str]:
    paths = sorted(root.glob("crt-r4a-proxy-summary-*/crt-proxy-summary.json"))
    if len(paths) != 33:
        raise ValueError(f"expected 33 archives, got {len(paths)}")
    rows: list[dict[str, Any]] = []
    for path in paths:
        r = json.loads(path.read_text(encoding="utf-8"))
        if r.get("symbol") not in SYMBOLS or r.get("symbol") == "BTCUSD":
            raise ValueError("unexpected non-IC-market or missing symbol")
        if path.parent.name != f"crt-r4a-proxy-summary-{r['symbol']}":
            raise ValueError("artifact name does not match source symbol")
        if r.get("period") != "2024-01-01/2025-12-31":
            raise ValueError("unsupported research period")
        if r.get("native_M5_rows", 0) < 50_000:
            raise ValueError("insufficient two-year native M5 source")
        if r["status"] != "REAL_OHLC_EXPLORATORY_PROXY_ONLY":
            raise ValueError("unsupported source status")
        for key in ("is_Pine_parity_100pct", "costs_included",
                    "holdout_certified", "portfolio_certified"):
            if r[key] is not False:
                raise ValueError(f"false certification: {key}")
        if r["source_sha256"] != "2024_AND_2025_VERIFIED":
            raise ValueError("missing archive integrity")
        if set(r["two_hypotheses"]) != set(MODELS):
            raise ValueError("model missing")
        rows.append(r)
    rows.sort(key=lambda r: r["symbol"])
    syms = [r["symbol"] for r in rows]
    if set(syms) != set(SYMBOLS) - {"BTCUSD"}:
        raise ValueError("incorrect full 33-symbol source universe")
    atlas = sum("ATLAS" in r["cohort"] for r in rows)
    ic = sum(r["cohort"] == "ICMARKETS_DEMO_CONFIRMED" for r in rows)
    if atlas != 12 or ic != 21:
        raise ValueError("provenance cohorts mismatch")
    pooled: dict[str, Any] = {}
    for model in MODELS:
        sub = [r["two_hypotheses"][model] for r in rows]
        trades = sum(x["closed_trades"] for x in sub)
        gross_r = sum(x["gross_net_R_unscaled"] for x in sub)
        wins = sum(
            x["closed_trades"] * (x["gross_win_rate"] or 0) for x in sub
        )
        pooled[model] = {
            "trades": trades,
            "gross_r_sum_not_portfolio": gross_r,
            "gross_mean_r": gross_r / trades if trades else None,
            "gross_win_rate": wins / trades if trades else None,
            "markets_positive": sum(x["gross_net_R_unscaled"] > 0 for x in sub),
            "markets_negative": sum(x["gross_net_R_unscaled"] < 0 for x in sub),
            "markets_no_trades": sum(x["closed_trades"] == 0 for x in sub),
            "gross_break_even_cost_R_per_closed_trade": (
                max(0.0, gross_r / trades) if trades else None
            ),
            "hypothetical_cost_stress_not_broker_net": {
                f"{cost:.2f}R": {
                    "hypothetical_mean_R": gross_r / trades - cost if trades else None,
                    "hypothetical_sum_R_not_capital": gross_r - trades * cost,
                }
                for cost in COST_STRESS_R
            },
        }
    totals = {
        "native_M5": sum(r["native_M5_rows"] for r in rows),
        "closed_H4": sum(r["closed_H4"] for r in rows),
        "2C_structural_proxy": sum(
            r["signals"].get("A_2C_STRUCTURAL", 0) for r in rows
        ),
        "A_MSS15_proxy": sum(
            r["signals"].get("A_MSS15_PROXY_CONFIRMED", 0) for r in rows
        ),
        "TRUE3C_structural_proxy": sum(
            r["signals"].get("B_TRUE3C_STRUCTURAL", 0) for r in rows
        ),
        "B_MSS5_proxy": sum(
            r["signals"].get("B_MSS5_PROXY_CONFIRMED", 0) for r in rows
        ),
    }
    report: dict[str, Any] = {
        "source_action_run": SOURCE_RUN,
        "source_commit": "74092c66710449baed2ebcbbee8e7448e5ca54e3",
        "period": "2024-01-01_to_2026-01-01_exclusive",
        "status": "33_MARKET_REAL_M5_EXPLORATORY_PROXY_ONLY",
        "certified_holdout": False,
        "certified_pine_parity": False,
        "costs_included": False,
        "engine": "INDEPENDENT_APPROXIMATION_NOT_PINNED_R4_A",
        "unseen_holdout_proven": False,
        "sources": {"atlas_broker_unverified": atlas, "ic_demo": ic},
        "totals": totals,
        "pooled": pooled,
        "cost_sensitivity_is_hypothetical_only": True,
        "cost_stress_R_per_trade": COST_STRESS_R,
        "by_symbol": rows,
    }
    notes = [
        "# QORE CRT Trader 2024–2025 — historial real, proxy NO certificado",
        "",
        "33/33 M5 históricos de los artefactos originales de QORE GitHub "
        "Actions; run #" + str(SOURCE_RUN) + ".",
        "",
        "**No es el detector Pine exacto, no incluye costos ni BTCUSD, "
        "no es un holdout virgen certificado ni una curva de capital.**",
        "",
        f"Velas M5: {totals['native_M5']:,}; H4: {totals['closed_H4']:,}.",
        f"2C: {totals['2C_structural_proxy']:,}; MSS15 proxy: "
        f"{totals['A_MSS15_proxy']:,}.",
        f"TRUE3C: {totals['TRUE3C_structural_proxy']:,}; MSS5 proxy: "
        f"{totals['B_MSS5_proxy']:,}.",
        "",
        "| Modelo | Trades cerrados | WR bruto | Expectativa bruta | "
        "Total R sin dimensionar | Mercados positivos/negativos |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for model in MODELS:
        a = pooled[model]
        notes.append(
            f"| {model} | {a['trades']} | "
            f"{fmt(a['gross_win_rate'] * 100 if a['gross_win_rate'] is not None else None)}% | "
            f"{fmt(a['gross_mean_r'], 4)} R | "
            f"{fmt(a['gross_r_sum_not_portfolio'])} R | "
            f"{a['markets_positive']}/{a['markets_negative']} |"
        )
    notes.extend([
        "",
        "## Falsación por costos hipotéticos (NO cotizaciones broker)",
        "",
        "Esta prueba resta 0.02R, 0.05R, 0.10R o 0.20R por operación "
        "cerrada. No afirma que estos sean costos reales ni representa "
        "un backtest neto. Los resultados brutos ya usan OHLC mid/proxy.",
        "",
        "| Modelo | Media bruta R | Media con -0.02R | "
        "Media con -0.05R | Media con -0.10R | Coste máximo bruto para empate |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for model in MODELS:
        a = pooled[model]
        stress = a["hypothetical_cost_stress_not_broker_net"]
        notes.append(
            f"| {model} | {fmt(a['gross_mean_r'], 4)} | "
            f"{fmt(stress['0.02R']['hypothetical_mean_R'], 4)} | "
            f"{fmt(stress['0.05R']['hypothetical_mean_R'], 4)} | "
            f"{fmt(stress['0.10R']['hypothetical_mean_R'], 4)} | "
            f"{fmt(a['gross_break_even_cost_R_per_closed_trade'], 4)} |"
        )
    notes.extend([
        "",
        "## Todos los mercados (sin selección por rentabilidad)",
        "",
        "| Mercado | Origen | A trades | A PF bruto | A suma R | "
        "B trades | B PF bruto | B suma R |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ])
    for r in rows:
        a, b = (r["two_hypotheses"][model] for model in MODELS)
        cohort = "Atlas unverified" if "ATLAS" in r["cohort"] else "IC DEMO"
        notes.append(
            f"| {r['symbol']} | {cohort} | {a['closed_trades']} | "
            f"{fmt(a['gross_profit_factor'])} | {fmt(a['gross_net_R_unscaled'])} | "
            f"{b['closed_trades']} | {fmt(b['gross_profit_factor'])} | "
            f"{fmt(b['gross_net_R_unscaled'])} |"
        )
    notes.extend([
        "",
        "**Limitaciones que invalidan una certificación de rentabilidad:** "
        "sin paridad del motor Pine R4-A, sin bid/ask/spread/slippage/commission/swap, "
        "fuentes Atlas no homologadas con IC Markets, BTCUSD ausente, "
        "sin riesgo agregado ni sizing; posible exposición previa del período.",
        "",
        "Veredicto: 33/34 prueba retrospectiva exploratoria completada; "
        "holdout económico del indicador de 34 mercados NO CERTIFICABLE.",
        "",
    ])
    return report, "\n".join(notes)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--outdir", type=Path, required=True)
    args = p.parse_args()
    report, markdown = aggregate(args.root)
    args.outdir.mkdir(parents=True, exist_ok=True)
    (args.outdir / "summary.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.outdir / "summary.md").write_text(markdown, encoding="utf-8")
    print(json.dumps({
        "status": report["status"], "symbols": len(report["by_symbol"]),
        "totals": report["totals"], "pooled": report["pooled"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
