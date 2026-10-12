"""QORE Native E3: POSTHOC 33x7 grouped method inference and block sensitivity.

Consumes ONLY the original 33 signed E1 event-result witnesses; no price bars,
no new strategy specifications, no trader orders. 7 tests + 28 descriptive
strata + 231 DESCRIPTIVE empirical-Bayes-like shrinkage scores, NOT edge proof.
"""
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from qore.infrastructure.trader_lab import qore_native_e2_33x7_holm_synchronized_weeks_v1 as parent
from qore.infrastructure.trader_lab import qore_native_e2_posthoc_bh_sensitivity_v1 as fdr
from qore.infrastructure.trader_lab import qore_native_existing12_m5_g0_v1 as g0
from qore.infrastructure.trader_lab import qore_native_market33_source_census_v1 as census

IDENTITY = "QORE_NATIVE_E3_POSTHOC_SEVEN_METHOD_MULTIWEEK_SHRINKAGE_V1"
ORIGINAL_E1_RUN = 38257207836
ORIGINAL_E1_CODE_SHA = fdr.PARENT_CODE_SHA
E3_SPEC_SHA = "2a053e762268c2f4f22238d200599a7adf4726f7"
LENGTHS = (1, 2, 4)
BOOTSTRAP = 4000
SEED = 20261012
FAMILIES = tuple(census.FAMILIES.keys())
RATE = (0.05, 0.10)
COST_STRESS_RT_BPS = (0, 1, 3, 5)
PERIODS = ("development", "temporal_diagnostic")


def original_event_witnesses(root: Path) -> dict[str, list[dict[str, Any]]]:
    """Same code SHA in all signed per-market files; E2 verifies each ledger."""
    files = sorted(root.rglob("qore-native-e1-seven-*.json"))
    if len(files) != 33:
        raise ValueError("E3 requires all 33 exact original signed E1 event ledgers")
    for p in files:
        witness = p.with_name("exact-code-head-sha.txt")
        if not witness.is_file() or witness.read_text(encoding="utf-8").strip() != ORIGINAL_E1_CODE_SHA:
            raise ValueError("E1 original tested code SHA changed/mixed")
    return parent.load_signed_observations(root)


def build_week_tensors(
    docs: dict[str, list[dict[str, Any]]], period: str,
) -> tuple[list[str], np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    if period not in PERIODS or set(docs) != set(parent.SYMBOLS):
        raise ValueError("period or 33-market universe changed")
    rows: dict[str, list[dict[str, Any]]] = {}
    weeks: set[str] = set()
    for method in parent.METHODS:
        for symbol in parent.SYMBOLS:
            cell = f"{method}__{symbol}"
            source = next((r for r in docs[symbol] if r["method_id"] == method), None)
            if source is None:
                raise ValueError("a method was removed from original data")
            events = []
            for row in source["paired_events"]:
                at = datetime.fromisoformat(row["reference_entry_utc"]).astimezone(UTC)
                is_dev = at < parent.e1.DEV_CUTOFF
                if is_dev == (period == "development"):
                    events.append(row)
                    weeks.add(row["iso_week"])
            rows[cell] = events
    dates = sorted(weeks)
    if not dates:
        raise ValueError("no original calendar weeks: unavailable evidence")
    mapping = {w:i for i,w in enumerate(dates)}
    n = len(parent.CELLS)
    counts = np.zeros((len(dates), n), dtype=np.float64)
    delta = np.zeros_like(counts)
    gross = np.zeros_like(counts)
    for j, key in enumerate(parent.CELLS):
        for event in rows[key]:
            i = mapping[event["iso_week"]]
            counts[i, j] += 1
            delta[i, j] += event["paired_delta_bps"]
            gross[i, j] += event["strategy_gross_bps"]
    details = {
        key: {
            "n": len(rows[key]),
            "weeks_with_events": len({r["iso_week"] for r in rows[key]}),
            "prior_exposure": parent.registry.cell_prior(
                key.split("__")[0], key.split("__")[1]
            )["status"],
        } for key in parent.CELLS
    }
    return dates, counts, delta, gross, details


def circular_block_week_counts(
    weeks: int, length: int, replicates: int, seed: int,
) -> np.ndarray:
    """One shared ISO-week sequence for ALL 231 outcomes; circular moving blocks."""
    if weeks <= 0 or length < 1 or length > weeks or replicates < 1:
        raise ValueError("invalid fixed E3 calendar-block dimensions")
    rng = np.random.default_rng(seed)
    segments = (weeks + length - 1) // length
    starts = rng.integers(0, weeks, size=(replicates, segments))
    offsets = np.arange(length, dtype=np.int64)
    indices = ((starts[:, :, None] + offsets) % weeks).reshape(replicates, -1)[:, :weeks]
    offsets_for_bincount = np.arange(replicates, dtype=np.int64)[:, None] * weeks
    weights = np.bincount(
        (indices + offsets_for_bincount).ravel(),
        minlength=replicates * weeks,
    ).reshape(replicates, weeks)
    if not np.all(weights.sum(axis=1) == weeks):
        raise ValueError("bootstrap reused wrong number of shared calendar weeks")
    return weights.astype(np.float64)


def panel_mean(cell_mean: np.ndarray, market_indices: list[int]) -> np.ndarray:
    """Equal-market weight. If ANY market is unavailable, fail-closed as nan."""
    selected = cell_mean[..., market_indices]
    return np.where(
        np.all(np.isfinite(selected), axis=-1),
        np.mean(selected, axis=-1),
        np.nan,
    )


def summarize_bootstrap(
    samples: np.ndarray, observed: float, expected_replicates: int,
) -> dict[str, Any]:
    valid = np.isfinite(samples)
    invalid = int(expected_replicates - int(np.count_nonzero(valid)))
    if invalid:
        return {
            "ci95_descriptive_bps": None,
            "p_two_sided_null_centered_exploratory": 1.0,
            "valid_draws": int(np.count_nonzero(valid)),
            "invalid_draws": invalid,
            "SE_bps": None,
            "passed_bootstrap_data_gate": False,
        }
    centered = samples - observed
    p = (1 + int(np.count_nonzero(np.abs(centered) >= abs(observed)))) / (expected_replicates + 1)
    return {
        "ci95_descriptive_bps": [
            float(np.quantile(samples, 0.025)),
            float(np.quantile(samples, 0.975)),
        ],
        "p_two_sided_null_centered_exploratory": float(p),
        "valid_draws": expected_replicates,
        "invalid_draws": 0,
        "SE_bps": float(np.std(samples, ddof=1)) if expected_replicates > 1 else None,
        "passed_bootstrap_data_gate": True,
    }


def shrinkage_by_method(
    method: str,
    cell_deltas: np.ndarray,
    cell_SE: np.ndarray,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Uncalibrated method-of-moments proxy, NOT an independent-market posterior."""
    if len(cell_deltas) != 33 or len(cell_SE) != 33:
        raise ValueError("shrinkage needs exact frozen 33 cells")
    if not np.all(np.isfinite(cell_deltas)) or not np.all(np.isfinite(cell_SE)):
        return {"method_id":method, "status":"INVALID_MISSING_SE_OR_EVENT"}, []
    if np.any(cell_SE < 0):
        raise ValueError("negative SE impossible")
    mu = float(np.mean(cell_deltas))
    between = float(np.var(cell_deltas, ddof=1))
    noise = float(np.mean(cell_SE**2))
    tau2 = max(0.0, between - noise)
    weights = np.divide(
        tau2, tau2 + cell_SE**2,
        out=np.zeros(33, dtype=np.float64),
        where=(tau2 + cell_SE**2) > 0,
    )
    scores = mu + weights * (cell_deltas-mu)
    return (
        {
            "method_id":method,
            "status":"DESCRIPTIVE_SHRINKAGE_NOT_CALIBRATED_HIERARCHICAL_POSTERIOR",
            "equal_market_mean_delta_bps":mu,
            "between_market_var_bps2":between,
            "mean_week_bootstrap_noise_var_bps2":noise,
            "tau2_nonnegative_moments_proxy_bps2":tau2,
            "same_currency_factor_correlation_not_removed":True,
        },
        [{
            "cell_id":f"{method}__{symbol}",
            "raw_delta_bps":float(cell_deltas[i]),
            "cell_SE_L4_bps":float(cell_SE[i]),
            "shrink_weight":float(weights[i]),
            "shrunken_delta_descriptive_bps":float(scores[i]),
            "source_family":parent.registry.family_for(symbol),
            "score_not_independent_out_of_sample":True,
        } for i, symbol in enumerate(parent.SYMBOLS)]
    )


def analyze_period(
    docs: dict[str, list[dict[str, Any]]], period: str,
    replicates: int = BOOTSTRAP,
) -> dict[str, Any]:
    weeks, counts, delta, gross, cells = build_week_tensors(docs, period)
    den = counts.sum(axis=0)
    if np.any(den == 0):
        raise ValueError("E3 policy requires all 231 source cells: zero-event cell blocks panel estimates")
    dmean = delta.sum(axis=0) / den
    gmean = gross.sum(axis=0) / den
    nmethods, nsymbols = 7, 33
    dmat = dmean.reshape(nmethods, nsymbols)
    gmat = gmean.reshape(nmethods, nsymbols)
    results: dict[str, Any] = {}
    shrink: dict[str, Any] = {}
    shrink_cells: list[dict[str, Any]] = []
    se_L4: np.ndarray | None = None
    for length in LENGTHS:
        draw = circular_block_week_counts(
            len(weeks), length, replicates,
            SEED + (0 if period == "development" else 100) + length,
        )
        bs_den = draw @ counts
        bs_delta = np.divide(
            draw @ delta, bs_den,
            out=np.full(bs_den.shape, np.nan, dtype=np.float64),
            where=bs_den > 0,
        )
        block_methods: list[dict[str, Any]] = []
        block_pvals: list[float] = []
        for k, method in enumerate(parent.METHODS):
            start = k*33
            obs = float(np.mean(dmat[k]))
            samples = panel_mean(bs_delta, list(range(start, start+33)))
            stats = summarize_bootstrap(samples, obs, replicates)
            block_pvals.append(stats["p_two_sided_null_centered_exploratory"])
            gross_obs = float(np.mean(gmat[k]))
            block_methods.append({
                "method_id":method,
                "market_count":33,
                "n_paired_events_sum_not_independent":int(den[start:start+33].sum()),
                "gross_equal_market_bps":gross_obs,
                "paired_delta_equal_market_bps":obs,
                "hypothetical_gross_minus_RT_bps_not_broker": {
                    str(c):gross_obs-c for c in COST_STRESS_RT_BPS
                },
                **stats,
            })
        bh = fdr.bh(block_pvals)
        holm = parent.holm_adjusted(block_pvals)
        for k, row in enumerate(block_methods):
            row["BH_q_7_methods_posthoc"] = float(bh[k])
            row["Holm_p_7_methods_posthoc"] = float(holm[k])
            row["BH_positive_at_10pct_not_certified"] = bool(
                row["paired_delta_equal_market_bps"]>0
                and row["gross_equal_market_bps"]>0
                and row["BH_q_7_methods_posthoc"]<=0.10
                and row["passed_bootstrap_data_gate"]
            )
        stratified: list[dict[str, Any]] = []
        for method_i, method in enumerate(parent.METHODS):
            for family in FAMILIES:
                members = [method_i*33 + i for i, sym in enumerate(parent.SYMBOLS)
                           if sym in census.FAMILIES[family]]
                stratified.append({
                    "method_id":method, "market_family":family,
                    "market_count":len(members),
                    "gross_equal_market_bps_descriptive":float(np.mean(gmean[members])),
                    "delta_equal_market_bps_descriptive":float(np.mean(dmean[members])),
                    "not_separately_significance_tested":True,
                })
        if length == 4:
            se_L4 = np.std(bs_delta, axis=0, ddof=1)
        results[str(length)] = {
            "block_length_weeks":length,
            "common_week_calendar_across_231":True,
            "replicates":replicates,
            "seven_methods":block_methods,
            "four_families_by_method_descriptive":stratified,
            "BH_positive_method_count":sum(x["BH_positive_at_10pct_not_certified"]
                                            for x in block_methods),
        }
    if se_L4 is None:
        raise ValueError("required L=4 shrinkage absent")
    for k, method in enumerate(parent.METHODS):
        sl = slice(k*33, (k+1)*33)
        summary, rows = shrinkage_by_method(method, dmean[sl], se_L4[sl])
        shrink[method] = summary
        shrink_cells.extend(rows)
    if len(shrink_cells) != 231:
        raise ValueError("all 231 shrinkage scores must be present")
    return {
        "period":period,
        "calendar_week_count":len(weeks),
        "total_paired_events_sum_not_independent":int(den.sum()),
        "methods":7,
        "markets":33,
        "cell_count":231,
        "block_sensitivities":results,
        "uncalibrated_method_of_moments_shrinkage":shrink,
        "all_231_market_shrinkage_descriptors":shrink_cells,
        "bidask_broker_cost_certified":False,
        "macro_news_asof_verified":False,
    }


def analyze(signed_root: Path) -> dict[str, Any]:
    docs = original_event_witnesses(signed_root)
    dev = analyze_period(docs, "development")
    diag = analyze_period(docs, "temporal_diagnostic")
    if (dev["cell_count"] != 231 or diag["cell_count"] != 231
            or dev["markets"] != 33 or diag["markets"] != 33):
        raise ValueError("incomplete signed full 231 source results")
    stable = []
    for k, method in enumerate(parent.METHODS):
        dr = [dev["block_sensitivities"][str(L)]["seven_methods"][k] for L in LENGTHS]
        vr = [diag["block_sensitivities"][str(L)]["seven_methods"][k] for L in LENGTHS]
        positive_sign = all(z["gross_equal_market_bps"] > 0
                            and z["paired_delta_equal_market_bps"] > 0
                            for z in dr + vr)
        stable.append({
            "method_id":method,
            "positive_gross_and_delta_both_periods_all_L":positive_sign,
            "BH_q_below_10pct_both_periods_all_L":all(
                z["BH_positive_at_10pct_not_certified"] for z in dr + vr
            ),
            "followup_worthy_unconfirmed":positive_sign and all(
                z["passed_bootstrap_data_gate"] for z in dr + vr
            ),
            "edge_certified":False,
        })
    return {
        "identity":IDENTITY,
        "status":"E3_POSTHOC_SEVEN_METHOD_MULTIWEEK_SHRINKAGE_NO_NEW_PRICES",
        "source_actions_run":ORIGINAL_E1_RUN,
        "source_e1_code_head":ORIGINAL_E1_CODE_SHA,
        "source_g0_manifest_sha":parent.e1.SOURCE_33_SHA,
        "fixed_e3_design_commit":E3_SPEC_SHA,
        "source_33_signed_market_witnesses":33,
        "source_7_methods_per_market":7,
        "total_cells_source":231,
        "original_2024_plus_OHLC_unopened":True,
        "already_exposed_dev_and_diagnostic_posthoc":True,
        "no_new_raw_provider_prices_downloaded":True,
        "bootstrap_config":{"B":BOOTSTRAP,"seed":SEED,"L_weeks":list(LENGTHS)},
        "development":dev,
        "temporal_diagnostic":diag,
        "cross_period_seven_method_descriptive_screen":stable,
        "shrinkage_posteriors_are_not_calibrated":True,
        "net_PF_Sharpe_Sortino_DD_not_available":True,
        "traders_certified":0,
        "VPS_MT5_Shared_CIBO_QDLE_LIVE_untouched":True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("signed_original_e1_33",type=Path)
    parser.add_argument("output_dir",type=Path)
    args = parser.parse_args()
    report = analyze(args.signed_original_e1_33)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    dest = args.output_dir / "qore-native-e3-seven-method-block-shrinkage-posthoc.json"
    dest.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    dest.with_name(dest.name+".sha256").write_text(
        g0.sha256(dest)+"  "+dest.name+"\n",encoding="utf-8",
    )
    headline = {
        "status":report["status"],
        "dev_week_clusters":report["development"]["calendar_week_count"],
        "diag_week_clusters":report["temporal_diagnostic"]["calendar_week_count"],
        "stable_positive_methods":[x["method_id"] for x in report["cross_period_seven_method_descriptive_screen"]
                                   if x["positive_gross_and_delta_both_periods_all_L"]],
        "BH_positive_both_L1_L2_L4":[x["method_id"]
                                    for x in report["cross_period_seven_method_descriptive_screen"]
                                    if x["BH_q_below_10pct_both_periods_all_L"]],
        "traders_certified":0,
    }
    print(json.dumps(headline,sort_keys=True))


if __name__=="__main__":
    main()
