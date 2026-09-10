from __future__ import annotations

from pathlib import Path


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"expected exactly one replacement in {path}, found {count}")
    path.write_text(text.replace(old, new), encoding="utf-8")


path = Path("src/qore/infrastructure/trader_lab/story_forensics_review_panel.py")

old_build = '''    for subject in subjects:
        subject["review_lanes"] = _empty_lanes()
        subject["synthesis_status"] = "BLOCKED_PENDING_REVIEWS"
'''
new_build = '''    for subject in subjects:
        subject["descriptor_digest"] = _subject_descriptor_digest(subject)
        subject["review_lanes"] = _empty_lanes()
        subject["synthesis_status"] = "BLOCKED_PENDING_REVIEWS"
'''
replace_once(path, old_build, new_build)

old_empty = '''def _empty_lanes() -> dict[str, object]:
    return {
        role.value: {
            "status": "PENDING",
            "assessment": None,
            "assessment_digest": None,
        }
        for role in _REQUIRED_ROLES
    }


def build_review_panel(story: dict[str, object]) -> dict[str, object]:
'''
new_empty = '''def _empty_lanes() -> dict[str, object]:
    return {
        role.value: {
            "status": "PENDING",
            "assessment": None,
            "assessment_digest": None,
        }
        for role in _REQUIRED_ROLES
    }


def _subject_descriptor_material(subject: dict[str, object]) -> dict[str, object]:
    subject_type = _text(subject.get("subject_type"), field_name="subject type")
    if subject_type == "episode":
        keys = (
            "subject_id",
            "subject_type",
            "subject_digest",
            "trader_code",
            "symbol",
            "classification",
        )
    elif subject_type == "streak":
        keys = (
            "subject_id",
            "subject_type",
            "subject_digest",
            "family",
            "episode_ids",
        )
    else:
        raise StoryForensicsReviewError("unknown review subject type")
    return {key: deepcopy(subject.get(key)) for key in keys}


def _subject_descriptor_digest(subject: dict[str, object]) -> str:
    return _digest(_subject_descriptor_material(subject))


def _validate_subject_integrity(subject: dict[str, object]) -> None:
    observed_descriptor = _text(
        subject.get("descriptor_digest"),
        field_name="subject descriptor digest",
    )
    if _subject_descriptor_digest(subject) != observed_descriptor:
        raise StoryForensicsReviewError("review subject descriptor digest mismatch")

    lanes = _object(subject.get("review_lanes"), field_name="review lanes")
    expected_roles = {role.value for role in _REQUIRED_ROLES}
    if set(lanes) != expected_roles:
        raise StoryForensicsReviewError("review lane set changed")

    subject_digest = _text(subject.get("subject_digest"), field_name="subject digest")
    all_sealed = True
    for role in _REQUIRED_ROLES:
        lane = _object(lanes.get(role.value), field_name="review lane")
        if set(lane) != {"status", "assessment", "assessment_digest"}:
            raise StoryForensicsReviewError("review lane shape changed")
        status = lane.get("status")
        if status == "PENDING":
            all_sealed = False
            if lane.get("assessment") is not None or lane.get("assessment_digest") is not None:
                raise StoryForensicsReviewError("pending review lane contains sealed material")
            continue
        if status != "SEALED":
            raise StoryForensicsReviewError("review lane status is invalid")
        assessment = _object(lane.get("assessment"), field_name="sealed assessment")
        assessment_digest = _text(
            lane.get("assessment_digest"),
            field_name="assessment digest",
        )
        if _digest(assessment) != assessment_digest:
            raise StoryForensicsReviewError("sealed assessment digest mismatch")
        observed_role = _validate_assessment(assessment, subject_digest=subject_digest)
        if observed_role is not role:
            raise StoryForensicsReviewError("sealed assessment role does not match lane")

    expected_status = (
        "READY_FOR_ARCHITECT_ADJUDICATION"
        if all_sealed
        else "BLOCKED_PENDING_REVIEWS"
    )
    if subject.get("synthesis_status") != expected_status:
        raise StoryForensicsReviewError(
            "subject synthesis status does not match sealed review state"
        )


def build_review_panel(story: dict[str, object]) -> dict[str, object]:
'''
replace_once(path, old_empty, new_empty)

old_return = '''    if len(matches) != 1:
        raise StoryForensicsReviewError("subject_id must identify exactly one review subject")
    return matches[0]
'''
new_return = '''    if len(matches) != 1:
        raise StoryForensicsReviewError("subject_id must identify exactly one review subject")
    subject = matches[0]
    _validate_subject_integrity(subject)
    return subject
'''
replace_once(path, old_return, new_return)

old_validate = '''def _validate_assessment(
    assessment: dict[str, object],
    *,
    subject_digest: str,
) -> ReviewRole:
    if _text(assessment.get("subject_digest"), field_name="subject digest") != subject_digest:
'''
new_validate = '''def _validate_assessment(
    assessment: dict[str, object],
    *,
    subject_digest: str,
) -> ReviewRole:
    allowed_fields = {
        "subject_digest",
        "role",
        "favorable_candidate",
        "degradation_risks",
        "preserve",
        "evidence",
        "counterexample_or_falsifier",
        "scope",
        "confidence",
        "fresh_holdout_required",
    }
    if set(assessment) != allowed_fields:
        raise StoryForensicsReviewError(
            "assessment shape does not match sealed first-pass contract"
        )
    if _text(assessment.get("subject_digest"), field_name="subject digest") != subject_digest:
'''
replace_once(path, old_validate, new_validate)

old_policy_loop = '''    for item in subjects:
        subject = _object(item, field_name="review subject")
        subject_id = _text(subject.get("subject_id"), field_name="subject id")
'''
new_policy_loop = '''    for item in subjects:
        subject = _object(item, field_name="review subject")
        _validate_subject_integrity(subject)
        subject_id = _text(subject.get("subject_id"), field_name="subject id")
'''
replace_once(path, old_policy_loop, new_policy_loop)

test_path = Path("tests/infrastructure/trader_lab/test_story_forensics_review_panel.py")
text = test_path.read_text(encoding="utf-8")
marker = "test_reviewer_packet_rejects_subject_descriptor_mutation_after_freeze"
if marker in text:
    raise SystemExit("review panel integrity regressions already present")
text += '''\n\ndef test_reviewer_packet_rejects_subject_descriptor_mutation_after_freeze() -> None:\n    panel = build_review_panel(_story())\n    subject = _subject(panel, "episode-001")\n    subject["classification"] = "WIN_CANONICAL"\n\n    with pytest.raises(StoryForensicsReviewError, match="descriptor digest mismatch"):\n        reviewer_packet(\n            panel,\n            subject_id="episode-001",\n            role=ReviewRole.HARNESS,\n        )\n\n\ndef test_subject_synthesis_rejects_mutated_sealed_assessment() -> None:\n    panel = build_review_panel(_story())\n    for role in (\n        ReviewRole.HARNESS,\n        ReviewRole.EXPERT,\n        ReviewRole.WORK,\n        ReviewRole.ARCHITECT,\n    ):\n        panel = seal_assessment(\n            panel,\n            subject_id="episode-001",\n            assessment=_assessment(panel, subject_id="episode-001", role=role),\n        )\n    panel = seal_assessment(\n        panel,\n        subject_id="episode-001",\n        assessment=_assessment(\n            panel,\n            subject_id="episode-001",\n            role=ReviewRole.HUMAN_OWNER,\n        ),\n    )\n    subject = _subject(panel, "episode-001")\n    lanes = cast(dict[str, object], subject["review_lanes"])\n    harness_lane = cast(dict[str, object], lanes["harness"])\n    harness_assessment = cast(dict[str, object], harness_lane["assessment"])\n    harness_assessment["favorable_candidate"] = "tampered after sealing"\n\n    with pytest.raises(StoryForensicsReviewError, match="sealed assessment digest mismatch"):\n        synthesize_subject(panel, subject_id="episode-001")\n\n\ndef test_review_assessment_rejects_embedded_peer_material() -> None:\n    panel = build_review_panel(_story())\n    assessment = _assessment(\n        panel,\n        subject_id="episode-001",\n        role=ReviewRole.HARNESS,\n    )\n    assessment["sealed_machine_reviews"] = {"expert": "must not be embedded"}\n\n    with pytest.raises(StoryForensicsReviewError, match="assessment shape"):\n        seal_assessment(panel, subject_id="episode-001", assessment=assessment)\n\n\ndef test_policy_rejects_tampered_lane_status() -> None:\n    panel = build_review_panel(_story())\n    subject = _subject(panel, "episode-001")\n    lanes = cast(dict[str, object], subject["review_lanes"])\n    harness_lane = cast(dict[str, object], lanes["harness"])\n    harness_lane["status"] = "SEALED"\n\n    with pytest.raises(StoryForensicsReviewError, match="sealed assessment"):\n        build_trader_policy_candidate(panel)\n'''
test_path.write_text(text, encoding="utf-8")
