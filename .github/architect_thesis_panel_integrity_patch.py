from __future__ import annotations

from pathlib import Path


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"expected exactly one replacement in {path}, found {count}")
    path.write_text(text.replace(old, new), encoding="utf-8")


path = Path("src/qore/infrastructure/trader_lab/story_forensics_eleven_market_thesis.py")
old_lanes = '''def _empty_lanes() -> dict[str, object]:
    return {
        role.value: {
            "status": "PENDING",
            "assessment": None,
            "assessment_digest": None,
        }
        for role in _REQUIRED_ROLES
    }
'''
new_lanes = '''def _empty_lanes() -> dict[str, object]:
    return {
        role.value: {
            "status": "PENDING",
            "assessment": None,
            "assessment_digest": None,
        }
        for role in _REQUIRED_ROLES
    }


def _validate_panel_integrity(
    panel: dict[str, object],
) -> tuple[str, dict[str, str], dict[str, object]]:
    """Rebind every mutable panel surface to the frozen dossier before use."""

    if _text(panel.get("schema"), field_name="panel schema") != _PANEL_SCHEMA:
        raise ElevenMarketThesisError("unexpected thesis panel schema")
    if not _strict_bool(panel.get("research_only"), field_name="research_only"):
        raise ElevenMarketThesisError("thesis panel must remain research-only")
    if _strict_bool(panel.get("execution_authority"), field_name="execution_authority"):
        raise ElevenMarketThesisError("thesis panel cannot carry execution authority")

    frozen_dossier = _object(panel.get("frozen_dossier"), field_name="frozen_dossier")
    trader_code, markets = _validate_dossier(frozen_dossier)
    dossier_digest = _text(panel.get("dossier_digest"), field_name="dossier_digest")
    if _digest(frozen_dossier) != dossier_digest:
        raise ElevenMarketThesisError("frozen dossier digest mismatch")
    if _text(panel.get("trader_code"), field_name="trader_code") != trader_code:
        raise ElevenMarketThesisError("panel Trader does not match frozen dossier")

    required_markets = _string_list(panel.get("required_markets"), field_name="required_markets")
    if required_markets != list(_REQUIRED_MARKETS):
        raise ElevenMarketThesisError("panel required market order changed")
    evidence_index = _market_evidence_index(panel.get("market_evidence_index"))
    expected_index = {
        _text(row.get("symbol"), field_name="market symbol"): _text(
            row.get("evidence_digest"),
            field_name="evidence_digest",
        )
        for row in markets
    }
    if evidence_index != expected_index:
        raise ElevenMarketThesisError("panel evidence index diverges from frozen dossier")

    lanes = _object(panel.get("review_lanes"), field_name="review_lanes")
    expected_roles = {role.value for role in _REQUIRED_ROLES}
    if set(lanes) != expected_roles:
        raise ElevenMarketThesisError("review lane set changed")
    all_sealed = True
    for role in _REQUIRED_ROLES:
        lane = _object(lanes.get(role.value), field_name="review lane")
        if set(lane) != {"status", "assessment", "assessment_digest"}:
            raise ElevenMarketThesisError("review lane shape changed")
        status = lane.get("status")
        if status == "PENDING":
            all_sealed = False
            if lane.get("assessment") is not None or lane.get("assessment_digest") is not None:
                raise ElevenMarketThesisError("pending review lane contains sealed material")
            continue
        if status != "SEALED":
            raise ElevenMarketThesisError("review lane status is invalid")
        assessment = _object(lane.get("assessment"), field_name="assessment")
        assessment_digest = _text(
            lane.get("assessment_digest"),
            field_name="assessment_digest",
        )
        if _digest(assessment) != assessment_digest:
            raise ElevenMarketThesisError("sealed assessment digest mismatch")
        observed_role = _validate_assessment(
            assessment,
            dossier_digest=dossier_digest,
            evidence_index=evidence_index,
        )
        if observed_role is not role:
            raise ElevenMarketThesisError("sealed assessment role does not match lane")

    expected_status = (
        "READY_FOR_SYNTHESIS" if all_sealed else "BLOCKED_PENDING_REVIEWS"
    )
    if panel.get("synthesis_status") != expected_status:
        raise ElevenMarketThesisError("synthesis status does not match sealed review state")
    return dossier_digest, evidence_index, lanes
'''
replace_once(path, old_lanes, new_lanes)

old_packet = '''    if _text(panel.get("schema"), field_name="panel schema") != _PANEL_SCHEMA:
        raise ElevenMarketThesisError("unexpected thesis panel schema")
    lanes = _object(panel.get("review_lanes"), field_name="review_lanes")
    evidence_index = _market_evidence_index(panel.get("market_evidence_index"))
'''
new_packet = '''    _, evidence_index, lanes = _validate_panel_integrity(panel)
'''
replace_once(path, old_packet, new_packet)

old_validate = '''def _validate_assessment(
    assessment: dict[str, object],
    *,
    dossier_digest: str,
    evidence_index: dict[str, str],
) -> ReviewRole:
    if _text(assessment.get("dossier_digest"), field_name="dossier_digest") != dossier_digest:
'''
new_validate = '''def _validate_assessment(
    assessment: dict[str, object],
    *,
    dossier_digest: str,
    evidence_index: dict[str, str],
) -> ReviewRole:
    allowed_fields = {
        "dossier_digest",
        "role",
        "verdict_family",
        "central_conclusion",
        "rationale",
        "common_patterns",
        "material_exceptions",
        "strengths_to_preserve",
        "degradation_risks",
        "evidence_by_market",
        "causal_hypothesis",
        "counterexample_or_falsifier",
        "confidence",
        "fresh_holdout_required_for_changes",
    }
    if set(assessment) != allowed_fields:
        raise ElevenMarketThesisError("assessment shape does not match sealed first-pass contract")
    if _text(assessment.get("dossier_digest"), field_name="dossier_digest") != dossier_digest:
'''
replace_once(path, old_validate, new_validate)

old_seal = '''    result = deepcopy(panel)
    dossier_digest = _text(result.get("dossier_digest"), field_name="dossier_digest")
    evidence_index = _market_evidence_index(result.get("market_evidence_index"))
    role = _validate_assessment(
        assessment,
        dossier_digest=dossier_digest,
        evidence_index=evidence_index,
    )
    lanes = _object(result.get("review_lanes"), field_name="review_lanes")
'''
new_seal = '''    result = deepcopy(panel)
    dossier_digest, evidence_index, lanes = _validate_panel_integrity(result)
    role = _validate_assessment(
        assessment,
        dossier_digest=dossier_digest,
        evidence_index=evidence_index,
    )
'''
replace_once(path, old_seal, new_seal)

old_synthesis = '''    lanes = _object(panel.get("review_lanes"), field_name="review_lanes")
    reviews: dict[str, object] = {}
'''
new_synthesis = '''    _, _, lanes = _validate_panel_integrity(panel)
    reviews: dict[str, object] = {}
'''
replace_once(path, old_synthesis, new_synthesis)

test_path = Path("tests/infrastructure/trader_lab/test_story_forensics_eleven_market_thesis.py")
text = test_path.read_text(encoding="utf-8")
marker = "test_reviewer_packet_rejects_frozen_dossier_mutation_after_panel_creation"
if marker in text:
    raise SystemExit("panel integrity regressions already present")
text += '''\n\ndef test_reviewer_packet_rejects_frozen_dossier_mutation_after_panel_creation() -> None:\n    panel = build_eleven_market_thesis_panel(_dossier())\n    frozen = cast(dict[str, object], panel["frozen_dossier"])\n    markets = cast(list[dict[str, object]], frozen["markets"])\n    markets[0]["evidence_digest"] = "tampered-after-freeze"\n\n    with pytest.raises(ElevenMarketThesisError, match="research dossier fingerprint mismatch"):\n        reviewer_packet(panel, role=ReviewRole.HARNESS)\n\n\ndef test_seal_rejects_evidence_index_mutation_after_panel_creation() -> None:\n    panel = build_eleven_market_thesis_panel(_dossier())\n    assessment = _assessment(panel, role=ReviewRole.HARNESS)\n    evidence_index = cast(dict[str, str], panel["market_evidence_index"])\n    evidence_index["US30"] = "tampered-index"\n\n    with pytest.raises(ElevenMarketThesisError, match="evidence index diverges"):\n        seal_assessment(panel, assessment=assessment)\n\n\ndef test_sealed_assessment_digest_is_revalidated_before_synthesis() -> None:\n    panel = build_eleven_market_thesis_panel(_dossier())\n    for role in (\n        ReviewRole.HARNESS,\n        ReviewRole.EXPERT,\n        ReviewRole.WORK,\n        ReviewRole.ARCHITECT,\n    ):\n        panel = seal_assessment(panel, assessment=_assessment(panel, role=role))\n    panel = seal_assessment(\n        panel,\n        assessment=_assessment(panel, role=ReviewRole.HUMAN_OWNER),\n    )\n    lanes = cast(dict[str, object], panel["review_lanes"])\n    harness_lane = cast(dict[str, object], lanes["harness"])\n    harness_assessment = cast(dict[str, object], harness_lane["assessment"])\n    harness_assessment["central_conclusion"] = "tampered after sealing"\n\n    with pytest.raises(ElevenMarketThesisError, match="sealed assessment digest mismatch"):\n        synthesize_eleven_market_thesis(panel)\n\n\ndef test_machine_assessment_rejects_peer_material_outside_first_pass_contract() -> None:\n    panel = build_eleven_market_thesis_panel(_dossier())\n    assessment = _assessment(panel, role=ReviewRole.HARNESS)\n    assessment["sealed_machine_reviews"] = {"expert": "must not be embedded"}\n\n    with pytest.raises(ElevenMarketThesisError, match="assessment shape"):\n        seal_assessment(panel, assessment=assessment)\n'''
test_path.write_text(text, encoding="utf-8")
