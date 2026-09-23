"""Governed CIBO Market Memory for VT08 Forex Cognitive V1.

The memory is market-specific and anchor-specific. It stores only aggregate
consumed-evidence priors derived from the exact R3.15 market artifacts. These
priors are association-only context: they cannot promote rules, select a market,
select a direction, or override VT08 methodology/QORE Risk.
"""
# ruff: noqa: E501
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from functools import lru_cache
from typing import Final, cast

from qore.infrastructure.traders.vt08_forex import AUTHORIZED_MARKETS
from qore.infrastructure.traders.vt08_source_kernel_r3_2 import OWNER_FOREX_ANCHORS

SCHEMA: Final = "qore.vt08.forex.cognitive.cibo_market_memory.v1"
SOURCE_RUN_ID: Final = 34759027136
SOURCE_HEAD_SHA: Final = "64bc2ab4809c39e4a2b2c72aa8c0e8ec1c709222"
HOLDOUT_ID: Final = "VT08_R3_15_FINAL_INDEPENDENT_2020_2022"
WINDOW_START: Final = "2020-07-01T00:00:00+00:00"
WINDOW_END_EXCLUSIVE: Final = "2022-07-01T00:00:00+00:00"

SOURCE_ARTIFACTS: Final[dict[str, dict[str, object]]] = {
    "AUDJPY": {"artifact_id": 10318258071, "digest": "sha256:ca9d9268b806f766441550ba8e7ba2edf6fc88b4e2933968ea9661f3478fa5ea"},
    "AUDUSD": {"artifact_id": 10317419979, "digest": "sha256:f3c50abde4308c79df9f3dd392bad605125c821aceec53ad4888c3f07eea9242"},
    "EURUSD": {"artifact_id": 10317944717, "digest": "sha256:407df5cdf14fad433572c6a15d75d13112a35b2492efb8240667c867505ad652"},
    "GBPJPY": {"artifact_id": 10317794998, "digest": "sha256:82416f8a815fcb948581beb99c1bfef671bb74343df1ba9074230938b31dd762"},
    "GBPUSD": {"artifact_id": 10318835914, "digest": "sha256:b213e91945601a88875cf72a9caf6b4c6858700c3ed458098fcb1a816a246044"},
    "USDCAD": {"artifact_id": 10318398127, "digest": "sha256:ca9c81bff7e7559c6ace39499a4edd8a019937cf1c20fcb71aec5f05c5dae69e"},
    "USDJPY": {"artifact_id": 10319210071, "digest": "sha256:e0e1b8c53b6716d0c8b14191f409dec9dd10dc107ff002df475e99d4f25d80af"},
}

_MARKET_ANCHOR_PRIORS: Final[dict[str, dict[str, dict[str, object]]]] = cast(
    dict[str, dict[str, dict[str, object]]],
    json.loads(r'''{"AUDJPY":{"1":{"body_fraction_median":"0.444444","bullish_close_rate":"0.541426","close_location_median":"0.537549","lower_wick_fraction_median":"0.248394","range_bps_median":"38.627527","range_bps_p25":"29.709174","range_bps_p75":"52.414861","sample":519,"upper_wick_fraction_median":"0.227119"},"5":{"body_fraction_median":"0.472492","bullish_close_rate":"0.536538","close_location_median":"0.553361","lower_wick_fraction_median":"0.237221","range_bps_median":"35.376645","range_bps_p25":"26.021489","range_bps_p75":"46.242440","sample":520,"upper_wick_fraction_median":"0.221744"},"9":{"body_fraction_median":"0.459734","bullish_close_rate":"0.536538","close_location_median":"0.571657","lower_wick_fraction_median":"0.263555","range_bps_median":"43.082901","range_bps_p25":"31.974100","range_bps_p75":"56.194373","sample":520,"upper_wick_fraction_median":"0.192343"}},"AUDUSD":{"1":{"body_fraction_median":"0.449045","bullish_close_rate":"0.558767","close_location_median":"0.556485","lower_wick_fraction_median":"0.240838","range_bps_median":"37.767086","range_bps_p25":"29.910064","range_bps_p75":"48.817466","sample":519,"upper_wick_fraction_median":"0.236301"},"5":{"body_fraction_median":"0.480369","bullish_close_rate":"0.519231","close_location_median":"0.538648","lower_wick_fraction_median":"0.216715","range_bps_median":"36.507481","range_bps_p25":"28.010148","range_bps_p75":"47.400542","sample":520,"upper_wick_fraction_median":"0.216970"},"9":{"body_fraction_median":"0.486961","bullish_close_rate":"0.521154","close_location_median":"0.522839","lower_wick_fraction_median":"0.234948","range_bps_median":"45.238560","range_bps_p25":"35.057536","range_bps_p75":"60.294783","sample":520,"upper_wick_fraction_median":"0.212931"}},"EURUSD":{"1":{"body_fraction_median":"0.467181","bullish_close_rate":"0.527938","close_location_median":"0.532663","lower_wick_fraction_median":"0.232143","range_bps_median":"26.605474","range_bps_p25":"20.172831","range_bps_p75":"34.905713","sample":519,"upper_wick_fraction_median":"0.223684"},"5":{"body_fraction_median":"0.456684","bullish_close_rate":"0.475000","close_location_median":"0.493552","lower_wick_fraction_median":"0.234365","range_bps_median":"28.185757","range_bps_p25":"21.415738","range_bps_p75":"37.740298","sample":520,"upper_wick_fraction_median":"0.213939"},"9":{"body_fraction_median":"0.454560","bullish_close_rate":"0.480769","close_location_median":"0.448583","lower_wick_fraction_median":"0.216096","range_bps_median":"31.590672","range_bps_p25":"23.584501","range_bps_p75":"43.564358","sample":520,"upper_wick_fraction_median":"0.220204"}},"GBPJPY":{"1":{"body_fraction_median":"0.464706","bullish_close_rate":"0.518304","close_location_median":"0.549467","lower_wick_fraction_median":"0.221333","range_bps_median":"35.453340","range_bps_p25":"27.036548","range_bps_p75":"47.065261","sample":519,"upper_wick_fraction_median":"0.224872"},"5":{"body_fraction_median":"0.438842","bullish_close_rate":"0.526923","close_location_median":"0.553994","lower_wick_fraction_median":"0.241728","range_bps_median":"35.103170","range_bps_p25":"25.896043","range_bps_p75":"47.404844","sample":520,"upper_wick_fraction_median":"0.221801"},"9":{"body_fraction_median":"0.474531","bullish_close_rate":"0.532692","close_location_median":"0.581147","lower_wick_fraction_median":"0.261531","range_bps_median":"37.829007","range_bps_p25":"28.356370","range_bps_p75":"48.940423","sample":520,"upper_wick_fraction_median":"0.195822"}},"GBPUSD":{"1":{"body_fraction_median":"0.469349","bullish_close_rate":"0.508671","close_location_median":"0.552381","lower_wick_fraction_median":"0.235294","range_bps_median":"33.111850","range_bps_p25":"26.374091","range_bps_p75":"41.866551","sample":519,"upper_wick_fraction_median":"0.223790"},"5":{"body_fraction_median":"0.473905","bullish_close_rate":"0.521154","close_location_median":"0.515447","lower_wick_fraction_median":"0.216844","range_bps_median":"35.551289","range_bps_p25":"27.089389","range_bps_p75":"46.001369","sample":520,"upper_wick_fraction_median":"0.214872"},"9":{"body_fraction_median":"0.484865","bullish_close_rate":"0.494231","close_location_median":"0.504291","lower_wick_fraction_median":"0.208055","range_bps_median":"37.259987","range_bps_p25":"29.462179","range_bps_p75":"50.386829","sample":520,"upper_wick_fraction_median":"0.205247"}},"USDCAD":{"1":{"body_fraction_median":"0.452941","bullish_close_rate":"0.462428","close_location_median":"0.421538","lower_wick_fraction_median":"0.215311","range_bps_median":"23.398268","range_bps_p25":"19.115652","range_bps_p75":"29.747733","sample":519,"upper_wick_fraction_median":"0.233766"},"5":{"body_fraction_median":"0.436621","bullish_close_rate":"0.505769","close_location_median":"0.497484","lower_wick_fraction_median":"0.238887","range_bps_median":"26.123140","range_bps_p25":"20.303824","range_bps_p75":"34.170441","sample":520,"upper_wick_fraction_median":"0.218344"},"9":{"body_fraction_median":"0.503360","bullish_close_rate":"0.478846","close_location_median":"0.433675","lower_wick_fraction_median":"0.223489","range_bps_median":"38.757402","range_bps_p25":"28.992865","range_bps_p75":"48.099559","sample":520,"upper_wick_fraction_median":"0.232405"}},"USDJPY":{"1":{"body_fraction_median":"0.480769","bullish_close_rate":"0.531792","close_location_median":"0.518900","lower_wick_fraction_median":"0.227273","range_bps_median":"22.404244","range_bps_p25":"16.290099","range_bps_p75":"30.346113","sample":519,"upper_wick_fraction_median":"0.221733"},"5":{"body_fraction_median":"0.480775","bullish_close_rate":"0.525000","close_location_median":"0.560458","lower_wick_fraction_median":"0.232310","range_bps_median":"24.661770","range_bps_p25":"17.521262","range_bps_p75":"32.420825","sample":520,"upper_wick_fraction_median":"0.221664"},"9":{"body_fraction_median":"0.445160","bullish_close_rate":"0.521154","close_location_median":"0.534959","lower_wick_fraction_median":"0.253563","range_bps_median":"26.028755","range_bps_p25":"19.502988","range_bps_p75":"37.156275","sample":520,"upper_wick_fraction_median":"0.210260"}}}'''),
)


def market_anchor_prior(market: str, anchor_hour_ny: int) -> dict[str, object]:
    if market not in AUTHORIZED_MARKETS:
        raise ValueError("VT08 CIBO market memory requested outside Forex authority")
    if anchor_hour_ny not in OWNER_FOREX_ANCHORS:
        raise ValueError("VT08 CIBO market memory anchor outside 01/05/09 NY")
    return deepcopy(_MARKET_ANCHOR_PRIORS[market][str(anchor_hour_ny)])


@lru_cache(maxsize=1)
def _payload_cached() -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "memory_class": "CIBO_MARKET_SPECIALIST",
        "markets": tuple(AUTHORIZED_MARKETS),
        "anchors_ny": tuple(OWNER_FOREX_ANCHORS),
        "source": {
            "run_id": SOURCE_RUN_ID,
            "head_sha": SOURCE_HEAD_SHA,
            "holdout_id": HOLDOUT_ID,
            "window_start": WINDOW_START,
            "window_end_exclusive": WINDOW_END_EXCLUSIVE,
            "artifacts": SOURCE_ARTIFACTS,
            "derivation": (
                "complete 4h windows reconstructed from closed M15 evidence "
                "at 01/05/09 America/New_York"
            ),
        },
        "market_anchor_priors": _MARKET_ANCHOR_PRIORS,
        "field_semantics": {
            "range_bps": "(high-low)/open*10000",
            "body_fraction": "abs(close-open)/(high-low)",
            "close_location": "(close-low)/(high-low)",
            "wick_fraction": "wick/(high-low)",
            "bullish_close_rate": "historical aggregate only",
        },
        "limitations": (
            "association-only",
            "consumed-evidence",
            "no-date-level-runtime-lookup",
            "no-rule-promotion",
            "no-market-ranking-authority",
            "no-direction-authority",
            "no-execution-authority",
            "no-capital-authority",
        ),
        "governance": {
            "runtime_self_training_allowed": False,
            "future_bar_runtime_lookup_allowed": False,
            "post_outcome_date_oracle_allowed": False,
            "may_rewrite_strategy_identity": False,
            "may_issue_execute_or_abstain": False,
            "qore_risk_final_capital_authority": True,
        },
    }


def cibo_market_memory_payload() -> dict[str, object]:
    return deepcopy(_payload_cached())


def cibo_market_memory_runtime_view() -> dict[str, object]:
    return _payload_cached()


@lru_cache(maxsize=1)
def cibo_market_memory_fingerprint() -> str:
    encoded = json.dumps(
        _payload_cached(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_cibo_market_memory() -> None:
    assert set(_MARKET_ANCHOR_PRIORS) == set(AUTHORIZED_MARKETS)
    for market in AUTHORIZED_MARKETS:
        assert set(_MARKET_ANCHOR_PRIORS[market]) == {"1", "5", "9"}
        for anchor in OWNER_FOREX_ANCHORS:
            cell = _MARKET_ANCHOR_PRIORS[market][str(anchor)]
            assert int(cell["sample"]) >= 500
    payload = _payload_cached()
    governance = cast(dict[str, object], payload["governance"])
    assert governance["runtime_self_training_allowed"] is False
    assert governance["future_bar_runtime_lookup_allowed"] is False
    assert governance["post_outcome_date_oracle_allowed"] is False
    assert governance["may_rewrite_strategy_identity"] is False
    assert governance["may_issue_execute_or_abstain"] is False
    assert len(cibo_market_memory_fingerprint()) == 64
