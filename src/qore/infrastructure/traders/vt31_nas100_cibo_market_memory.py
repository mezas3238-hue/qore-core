"""Governed CIBO Market Memory embedded inside VT31_NAS100.

This is the NAS100 analogue of the Turtle Soup XAUUSD dossier bridge.

The full consumed NAS100 CIBO dossier is retained as LONG_TERM_ARCHIVE inside
CiboMemoryStore. Its decomposed sections are additionally registered as MARKET
or RESEARCH memories with provenance, freshness, evidence references and
association-only limitations.

Runtime reasoning reads this in-process governed memory. It does not call an
external CIBO service and it never performs date-level historical outcome
lookups.
"""
# ruff: noqa: E501
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any, cast
from uuid import NAMESPACE_URL, uuid5

from qore.infrastructure.cibo_executive_memory import (
    CiboMemoryFreshness,
    CiboMemoryFreshnessState,
    CiboMemoryItem,
    CiboMemoryKind,
    CiboMemoryProvenance,
    CiboMemorySourceRef,
    CiboMemoryStore,
)
from qore.kernel.result import Success
from qore.modules.cibo.cognitive_contracts import CiboCognitiveEvidenceRef

IDENTITY = "VT31_NAS100_CIBO_MARKET_MEMORY_V1"
DOSSIER_IDENTITY = "CIBO_NAS100_MARKET_INTELLIGENCE_DOSSIER_V1"
SOURCE_RUN_ID = 35175782935
SOURCE_ARTIFACT_ID = 10478487667
SOURCE_ARTIFACT_DIGEST = (
    "sha256:17c8d1909152d87ed67a05cd986fa9cca39b2ac92598d36822c38e8afccde192"
)
DOSSIER_FINGERPRINT = (
    "fe17bf07c005b5b63ac5b77074d97c08aeff5b5ccc9adaa9c74b4d85ebecafdd"
)
EFFECTIVE_AT = datetime(2026, 9, 18, 0, 0, tzinfo=UTC)
RECORDED_AT = datetime(2026, 9, 18, 1, 20, tzinfo=UTC)

_DOSSIER_JSON = r'''{"by_partition":{"r5":{"both_sides_by_11_rate":"0.08752327746741154562383612663","both_sides_by_16_rate":"0.3594040968342644320297951583","date_end":"2022-07-15","date_start":"2020-06-17","days":537,"first_breach":{"both-same-bar":1,"high":264,"low":230,"none":42},"lifecycle_range_ref_median":"1.839622641509433962264150943","objective_hit_by_16_rate":"0.3370577281191806331471135940","reference_width_median":"95.4","regimes":{"inside-reference":24,"lateral-compression-proxy":97,"one-sided-expansion":234,"reversal-completion":181,"two-sided-expansion":1}},"r6":{"both_sides_by_11_rate":"0.06628787878787878787878787879","both_sides_by_16_rate":"0.3560606060606060606060606061","date_end":"2020-06-16","date_start":"2018-05-21","days":528,"first_breach":{"high":255,"low":212,"none":61},"lifecycle_range_ref_median":"1.840230667877428200060538076","objective_hit_by_16_rate":"0.3409090909090909090909090909","reference_width_median":"42.8","regimes":{"inside-reference":29,"lateral-compression-proxy":105,"one-sided-expansion":214,"reversal-completion":180}},"r8_fresh":{"both_sides_by_11_rate":"0.1064638783269961977186311787","both_sides_by_16_rate":"0.3688212927756653992395437262","date_end":"2018-05-18","date_start":"2016-04-19","days":526,"first_breach":{"high":262,"low":203,"none":61},"lifecycle_range_ref_median":"1.769754927385892116182572614","objective_hit_by_16_rate":"0.3536121673003802281368821293","reference_width_median":"21.0","regimes":{"inside-reference":28,"lateral-compression-proxy":111,"one-sided-expansion":201,"reversal-completion":186}}},"by_weekday":{"Friday":{"both_sides_by_11_rate":"0.07594936708860759493670886076","both_sides_by_16_rate":"0.3164556962025316455696202532","days":316,"first_breach":{"both-same-bar":1,"high":140,"low":140,"none":35},"lifecycle_range_ref_median":"1.793150249536767788793161746","objective_hit_by_16_rate":"0.2943037974683544303797468354","reference_width_median":"44.95","regimes":{"inside-reference":17,"lateral-compression-proxy":70,"one-sided-expansion":135,"reversal-completion":93,"two-sided-expansion":1}},"Monday":{"both_sides_by_11_rate":"0.05111821086261980830670926518","both_sides_by_16_rate":"0.3067092651757188498402555911","days":313,"first_breach":{"high":168,"low":112,"none":33},"lifecycle_range_ref_median":"1.651331719128329297820823245","objective_hit_by_16_rate":"0.2939297124600638977635782748","reference_width_median":"45.1","regimes":{"inside-reference":14,"lateral-compression-proxy":76,"one-sided-expansion":131,"reversal-completion":92}},"Thursday":{"both_sides_by_11_rate":"0.1090342679127725856697819315","both_sides_by_16_rate":"0.4143302180685358255451713396","days":321,"first_breach":{"high":157,"low":136,"none":28},"lifecycle_range_ref_median":"1.886850152905198776758409786","objective_hit_by_16_rate":"0.4018691588785046728971962617","reference_width_median":"45.5","regimes":{"inside-reference":16,"lateral-compression-proxy":52,"one-sided-expansion":124,"reversal-completion":129}},"Tuesday":{"both_sides_by_11_rate":"0.09597523219814241486068111455","both_sides_by_16_rate":"0.3622291021671826625386996904","days":323,"first_breach":{"high":156,"low":132,"none":35},"lifecycle_range_ref_median":"1.776169802219006271104679209","objective_hit_by_16_rate":"0.3467492260061919504643962848","reference_width_median":"47.1","regimes":{"inside-reference":15,"lateral-compression-proxy":64,"one-sided-expansion":132,"reversal-completion":112}},"Wednesday":{"both_sides_by_11_rate":"0.1006289308176100628930817610","both_sides_by_16_rate":"0.4056603773584905660377358491","days":318,"first_breach":{"high":160,"low":125,"none":33},"lifecycle_range_ref_median":"1.965736802160368533455707150","objective_hit_by_16_rate":"0.3805031446540880503144654088","reference_width_median":"43.05","regimes":{"inside-reference":19,"lateral-compression-proxy":51,"one-sided-expansion":127,"reversal-completion":121}}},"cross_index_context_memory":{"breach_lead_lag_minutes":{"p25":"1.00","p50":"6.00","p75":"19.00","p90":"34.00"},"breach_leader_counts":{"NAS100":837,"SP500":370,"US30":351},"days":1594,"departure_lead_lag_minutes":{"p25":"0.00","p50":"1.00","p75":"46.50","p90":"152.00"},"departure_leader_counts":{"NAS100":351,"SP500":262,"US30":278},"direction_state_counts":{"incomplete-or-nondirectional":527,"three-market-divergence":267,"unanimous-high":421,"unanimous-low":379},"role":"context_only_not_individual_memory_replacement"},"dossier_fingerprint_sha256":"fe17bf07c005b5b63ac5b77074d97c08aeff5b5ccc9adaa9c74b4d85ebecafdd","evidence_tier":"E1_ASSOCIATION_ONLY","governance":{"consumed_evidence":true,"date_level_runtime_lookup_allowed":false,"fresh_holdout_opened":false,"future_bar_lookup_allowed":false,"live_authorized":false,"post_outcome_runtime_lookup_allowed":false,"production_authorized":false,"research_only":true,"rule_promotion_allowed":false},"identity":"CIBO_NAS100_MARKET_INTELLIGENCE_DOSSIER_V1","journey_memory":{"completed_reversal_episodes":547,"departure_15m_bucket_counts":{"10:00":13,"10:15":36,"10:30":60,"10:45":44,"11:00":42,"11:15":41,"11:30":38,"11:45":29,"12:00":22,"12:15":25,"12:30":9,"12:45":17,"13:00":14,"13:15":12,"13:30":13,"13:45":23,"14:00":22,"14:15":12,"14:30":9,"14:45":17,"15:00":10,"15:15":13,"15:30":17,"15:45":9},"last_structure_before_departure_counts":{"breaker":13,"fair-value-gap":19,"local-liquidity-sweep":431,"none":1,"order-block":4,"reference-liquidity-sweep":79},"minutes_breach_to_departure":{"p25":"45.50","p50":"93.00","p75":"200.00","p90":"280.40"},"minutes_departure_to_objective":{"p25":"4.00","p50":"5.00","p75":"8.00","p90":"11.00"},"minutes_last_structure_touch_to_departure":{"p25":"1.00","p50":"6.00","p75":"12.75","p90":"20.00"}},"limitations":["association-only","consumed-research-evidence","no-rule-promotion","post-outcome-aggregate-sections-must-not-be-used-as-date-level-runtime-oracle","cross-index-memory-is-context-only","holdout-2015-04-19..2016-04-19-remains-sealed"],"market":"NAS100","market_overall":{"both_sides_by_11_rate":"0.08673790069138906348208673790","both_sides_by_16_rate":"0.3614079195474544311753614079","days":1591,"first_breach":{"both-same-bar":1,"high":781,"low":645,"none":164},"lifecycle_range_ref_median":"1.815384615384615384615384615","objective_hit_by_16_rate":"0.3438089252042740414833438089","reference_width_median":"45.1","regimes":{"inside-reference":81,"lateral-compression-proxy":313,"one-sided-expansion":649,"reversal-completion":547,"two-sided-expansion":1}},"pre_departure_sequence_memory":{"episodes":547,"event_counts_pre_departure":{"departure_pivot":547,"displacement:bearish":4624,"displacement:bullish":4563,"first_breach":547,"source_confirmation":406,"touch:breaker":220,"touch:fair-value-gap":398,"touch:local-liquidity-sweep":7242,"touch:order-block":91,"touch:reference-liquidity-sweep":3149},"last_predeparture_event_counts":{"displacement:bearish":156,"displacement:bullish":124,"first_breach":1,"touch:fair-value-gap":1,"touch:local-liquidity-sweep":224,"touch:reference-liquidity-sweep":41},"sequence_length_quantiles":{"p25":"15.00","p50":"30.00","p75":"61.00","p90":"82.00"}},"provider":"USTEC","schema":"qore.cibo.vt31.nas100.market-intelligence-dossier.v1","source":{"artifact_digest":"sha256:17c8d1909152d87ed67a05cd986fa9cca39b2ac92598d36822c38e8afccde192","artifact_id":10478487667,"cibo_bundle_schema":"qore.cibo_atlas.vt31.eight_ledger_bundle.v1","consumed_date_end":"2022-07-15","consumed_date_start":"2016-04-19","ledger_sha256":{"CIBO_ATLAS_VT31_EIGHT_LEDGER_SUMMARY.json":"72f6bdd93fc9dd00423b002969fd4e0b616bd26f1f681acd86ec21e1b50ed4ae","CROSS_INDEX_JOURNEY_LEDGER.jsonl":"1cc32b3ae8d49b289c93d0de5fa537137d52ebc6e3e200398df6546192a4f2d8","DAILY_PATH_LEDGER.jsonl":"d10538c7c3b72a34581bc86fc1832835183e0f59abf64c4d4b79f4f99b8eca4b","DEPARTURE_TIMING_LEDGER.jsonl":"e69cbd673c89c5427627ba13cd1faf3150cc6479075cb6a5b2e3ad3e1660fa26","MARKET_JOURNEY_LEDGER.jsonl":"fbaf31c8336516ac8bba15b5d8786260a056e4f1cf036eb9c758485fef6e7db1","PRE_DEPARTURE_SEQUENCE_LEDGER.jsonl":"ddf55d8f371da3718f202df4bc29cecd0cefb0f2dd9c103739be9893bdf8be8b","STRUCTURE_TOUCH_LEDGER.jsonl":"b7607728679841ac2e0a41f53ad16f1e1f617cf84abd78a58a65ce30ba29d660","TARGET_DESTINATION_LEDGER.jsonl":"93c726bb0b09192c05659cfe1255d1deae7a17931115506fad82403397625367","TRADER_MARKET_SYNC_LEDGER.jsonl":"46032b6880a53fca758934ab2c8f006e24686b75f02443d7b1c8de60cf28b3c0","attribution-artifact-digest.txt":"8f76c32ac12402c6c70619d85675540f3cabdf8301e16bbb4a4c5856d0cd5b8f","attribution-artifact-id.txt":"a01499b9f2f63577b86a9fc34a44d6e3ba0f39a99500a23e21a5f6e7545d07a9","forensics-artifact-digest.txt":"74337b2eea5dfd8df1e2125c01d7b5846adfeb4f33f91c8e8ecd2d182705a8ec","forensics-artifact-id.txt":"735d009638b9297d5bd46e7570275d8a043b3de9e2ea503605f52f041d6f452c","git-sha.txt":"2db6cb822e2fd711d1937512ab5a08e4e607b7480d256b40118d6d6d5ec4a822"},"partitions":{"r5":{"both_sides_by_11_rate":"0.08752327746741154562383612663","both_sides_by_16_rate":"0.3594040968342644320297951583","date_end":"2022-07-15","date_start":"2020-06-17","days":537,"first_breach":{"both-same-bar":1,"high":264,"low":230,"none":42},"lifecycle_range_ref_median":"1.839622641509433962264150943","objective_hit_by_16_rate":"0.3370577281191806331471135940","reference_width_median":"95.4","regimes":{"inside-reference":24,"lateral-compression-proxy":97,"one-sided-expansion":234,"reversal-completion":181,"two-sided-expansion":1}},"r6":{"both_sides_by_11_rate":"0.06628787878787878787878787879","both_sides_by_16_rate":"0.3560606060606060606060606061","date_end":"2020-06-16","date_start":"2018-05-21","days":528,"first_breach":{"high":255,"low":212,"none":61},"lifecycle_range_ref_median":"1.840230667877428200060538076","objective_hit_by_16_rate":"0.3409090909090909090909090909","reference_width_median":"42.8","regimes":{"inside-reference":29,"lateral-compression-proxy":105,"one-sided-expansion":214,"reversal-completion":180}},"r8_fresh":{"both_sides_by_11_rate":"0.1064638783269961977186311787","both_sides_by_16_rate":"0.3688212927756653992395437262","date_end":"2018-05-18","date_start":"2016-04-19","days":526,"first_breach":{"high":262,"low":203,"none":61},"lifecycle_range_ref_median":"1.769754927385892116182572614","objective_hit_by_16_rate":"0.3536121673003802281368821293","reference_width_median":"21.0","regimes":{"inside-reference":28,"lateral-compression-proxy":111,"one-sided-expansion":201,"reversal-completion":186}}},"run_id":35175782935,"source_git_sha":"6dc334723de5b7dca187e12b3a8ff531f4f1045e"},"structure_memory":{"family_counts":{"breaker":675,"fair-value-gap":1234,"local-liquidity-sweep":45739,"order-block":271,"reference-liquidity-sweep":11891},"rows":59810},"target_destination_memory":{"episodes":1591,"hit_rate_given_available":"0.3835904628330995792426367461","minutes_breach_to_opposite":{"p25":"51.00","p50":"99.00","p75":"208.00","p90":"288.00"},"opposite_boundary_available":1426,"opposite_boundary_hit_by_16":547,"post_boundary_extension_rate_given_hit":{"1":"0.3382084095063985374771480804","2":"0.1243144424131627056672760512","0.25":"0.7934186471663619744058500914","0.5":"0.5850091407678244972577696527","1.5":"0.1937842778793418647166361974"}},"timezone":"America/New_York","trader_overlay_research_source":{"entry_family_counts":{"breaker":97,"breaker+order-block":37,"fair-value-gap":45,"order-block":29},"pre_entry_behavior_proxy_counts":{"directional-build-proxy":15,"mixed-build-proxy":52,"rotation-compression-proxy":141},"roots":208,"runtime_rule_promotion_allowed":false,"side_counts":{"long":110,"short":98},"stopped_before_eventual_source_objective_count":51,"terminal_family_counts":{"initial_stop":87,"protected_stop":68,"target":53},"timing_class":"MIXED_PRE_ENTRY_AND_POST_OUTCOME_RESEARCH"}}'''

_MARKET_SECTIONS = (
    "market_overall",
    "by_partition",
    "by_weekday",
    "journey_memory",
    "structure_memory",
    "target_destination_memory",
    "pre_departure_sequence_memory",
    "cross_index_context_memory",
)
_RESEARCH_SECTIONS = ("trader_overlay_research_source",)


@lru_cache(maxsize=1)
def _dossier_cached() -> dict[str, Any]:
    dossier = json.loads(_DOSSIER_JSON)
    if dossier.get("identity") != DOSSIER_IDENTITY:
        raise ValueError("unexpected NAS100 CIBO dossier identity")
    if dossier.get("market") != "NAS100":
        raise ValueError("unexpected NAS100 CIBO dossier market")
    if dossier.get("evidence_tier") != "E1_ASSOCIATION_ONLY":
        raise ValueError("unexpected NAS100 CIBO evidence tier")
    if dossier.get("dossier_fingerprint_sha256") != DOSSIER_FINGERPRINT:
        raise ValueError("NAS100 dossier fingerprint binding drift")
    source = dossier.get("source")
    if not isinstance(source, dict):
        raise ValueError("NAS100 CIBO dossier source missing")
    if source.get("artifact_id") != SOURCE_ARTIFACT_ID:
        raise ValueError("NAS100 CIBO artifact binding drift")
    if source.get("artifact_digest") != SOURCE_ARTIFACT_DIGEST:
        raise ValueError("NAS100 CIBO digest binding drift")
    governance = dossier.get("governance")
    if not isinstance(governance, dict):
        raise ValueError("NAS100 CIBO governance missing")
    if governance.get("rule_promotion_allowed") is not False:
        raise ValueError("NAS100 dossier cannot promote rules")
    if governance.get("fresh_holdout_opened") is not False:
        raise ValueError("NAS100 fresh holdout unexpectedly opened")
    return cast(dict[str, Any], dossier)


def dossier_payload() -> dict[str, Any]:
    """Return a defensive copy for artifact/governance consumers."""
    return deepcopy(_dossier_cached())


def dossier_runtime_view() -> dict[str, Any]:
    """Read-only-by-contract internal view of immutable CIBO dossier."""
    return _dossier_cached()


def _subject(section: str) -> str:
    return "nas100.market." + section.replace("_", "-")


def _memory_item(
    *,
    section: str,
    value: Any,
    kind: CiboMemoryKind,
    evidence_ref: CiboCognitiveEvidenceRef,
) -> CiboMemoryItem:
    return CiboMemoryItem(
        item_id=uuid5(NAMESPACE_URL, f"{IDENTITY}:{section}"),
        kind=kind,
        subject_code=_subject(section),
        content=json.dumps(value, sort_keys=True, separators=(",", ":")),
        provenance=CiboMemoryProvenance(
            source_ref=CiboMemorySourceRef(
                f"github:artifact:{SOURCE_ARTIFACT_ID}:{section.replace('_', '-')}"
            ),
            effective_at=EFFECTIVE_AT,
            recorded_at=RECORDED_AT,
        ),
        freshness=CiboMemoryFreshness(
            state=CiboMemoryFreshnessState.CURRENT,
            as_of=RECORDED_AT,
        ),
        evidence_refs=(evidence_ref,),
        limitations=(
            "association-only",
            "consumed-research-evidence",
            "no-rule-promotion",
        ),
    )


@lru_cache(maxsize=1)
def build_market_memory_store() -> CiboMemoryStore:
    dossier = dossier_runtime_view()
    evidence_ref = CiboCognitiveEvidenceRef(
        f"cibo:nas100:market-intelligence:v1:artifact:{SOURCE_ARTIFACT_ID}"
    )
    store = CiboMemoryStore()
    archive = CiboMemoryItem(
        item_id=uuid5(NAMESPACE_URL, f"{IDENTITY}:full-dossier"),
        kind=CiboMemoryKind.LONG_TERM_ARCHIVE,
        subject_code="nas100.market.full-dossier",
        content=json.dumps(dossier, sort_keys=True, separators=(",", ":")),
        provenance=CiboMemoryProvenance(
            source_ref=CiboMemorySourceRef(
                f"github:artifact:{SOURCE_ARTIFACT_ID}:full-dossier"
            ),
            effective_at=EFFECTIVE_AT,
            recorded_at=RECORDED_AT,
        ),
        freshness=CiboMemoryFreshness(
            state=CiboMemoryFreshnessState.CURRENT,
            as_of=RECORDED_AT,
        ),
        evidence_refs=(evidence_ref,),
        limitations=(
            "association-only",
            "consumed-research-evidence",
            "no-rule-promotion",
        ),
    )
    recorded = store.record(archive)
    if not isinstance(recorded, Success):
        raise ValueError(f"failed to record NAS100 full dossier: {recorded}")
    store = recorded.value

    for section in _MARKET_SECTIONS:
        recorded = store.record(
            _memory_item(
                section=section,
                value=dossier[section],
                kind=CiboMemoryKind.MARKET,
                evidence_ref=evidence_ref,
            )
        )
        if not isinstance(recorded, Success):
            raise ValueError(f"failed to record NAS100 market memory {section}")
        store = recorded.value

    for section in _RESEARCH_SECTIONS:
        recorded = store.record(
            _memory_item(
                section=section,
                value=dossier[section],
                kind=CiboMemoryKind.RESEARCH,
                evidence_ref=evidence_ref,
            )
        )
        if not isinstance(recorded, Success):
            raise ValueError(f"failed to record NAS100 research memory {section}")
        store = recorded.value
    return store


def market_memory_index() -> dict[str, Any]:
    index: dict[str, Any] = {}
    for item in build_market_memory_store().retrieve():
        index[item.subject_code] = json.loads(item.content)
    return index


@lru_cache(maxsize=1)
def cibo_market_memory_fingerprint() -> str:
    store = build_market_memory_store()
    encoded = json.dumps(
        [item.logical_values() for item in store.retrieve()],
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@lru_cache(maxsize=1)
def _market_memory_manifest_cached() -> dict[str, object]:
    store = build_market_memory_store()
    items = store.retrieve()
    counts: dict[str, int] = {}
    for item in items:
        counts[item.kind.value] = counts.get(item.kind.value, 0) + 1
    return {
        "identity": IDENTITY,
        "dossier_identity": DOSSIER_IDENTITY,
        "source_run_id": SOURCE_RUN_ID,
        "source_artifact_id": SOURCE_ARTIFACT_ID,
        "source_artifact_digest": SOURCE_ARTIFACT_DIGEST,
        "dossier_fingerprint": DOSSIER_FINGERPRINT,
        "memory_fingerprint": cibo_market_memory_fingerprint(),
        "items": len(items),
        "kind_counts": counts,
        "governed_cibo_memory_store": True,
        "external_cibo_runtime_dependency": False,
        "evidence_tier": "E1_ASSOCIATION_ONLY",
        "rule_promotion_allowed": False,
        "fresh_holdout_opened": False,
    }


def market_memory_manifest() -> dict[str, object]:
    return deepcopy(_market_memory_manifest_cached())


def validate_cibo_market_memory() -> None:
    dossier = dossier_payload()
    assert dossier["market"] == "NAS100"
    manifest = market_memory_manifest()
    assert manifest["governed_cibo_memory_store"] is True
    assert manifest["external_cibo_runtime_dependency"] is False
    assert manifest["rule_promotion_allowed"] is False
    assert manifest["fresh_holdout_opened"] is False
    assert len(str(manifest["memory_fingerprint"])) == 64
