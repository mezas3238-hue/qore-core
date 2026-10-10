#!/usr/bin/env python3
"""Reconcile every sealed Trader opportunity with real Native MAX research cognition.

KEEP Native MAX as economic/exit-management ADVISORY for 3368 Trader signals:
it MUST NOT resurrect Native capital_disposition as a trade admission gate.
The legacy Native research receipts DO NOT contain authenticated broker fills,
managed exit price paths or CIBO Bank/Cushion proof. Plans are P0 experimental
suggestions, never proof of actual closed or open positions or financial PnL.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from contextlib import ExitStack
from pathlib import Path
from zipfile import ZipFile

from qore.infrastructure.cibo_p0_native_cognitive_management import native_sensor_management_plan

SOURCE_MEMBER = "cibo-native-baseline.json"
MANIFEST_MEMBER = "walk-forward-manifest.json"

class NativeManagementEvidenceError(ValueError):
    pass


def _stream_receipts(archive: Path, *, raw_json: bool=False):
    """Read 377 MB Native MAX JSON without materializing verbose sensor arrays."""
    with ExitStack() as context:
        if raw_json:
            f = context.enter_context(archive.open("rb"))
        else:
            zipped = context.enter_context(ZipFile(archive))
            if SOURCE_MEMBER not in zipped.namelist():
                raise NativeManagementEvidenceError("missing native max report")
            f = context.enter_context(zipped.open(SOURCE_MEMBER))
        if True:
            needle='"decision_receipts": ['
            buffer=""
            while needle not in buffer:
                more=f.read(65536)
                if not more:
                    raise NativeManagementEvidenceError("native decision_receipts missing")
                buffer+=more.decode("utf-8")
                if needle not in buffer:
                    buffer=buffer[-len(needle):]
            buffer=buffer.split(needle,1)[1]
            decoder=json.JSONDecoder()
            while True:
                buffer=buffer.lstrip()
                if buffer.startswith("]"):
                    break
                if buffer.startswith(","):
                    buffer=buffer[1:].lstrip()
                while True:
                    try:
                        row, end = decoder.raw_decode(buffer)
                        buffer=buffer[end:]
                        yield row
                        break
                    except json.JSONDecodeError:
                        more=f.read(65536)
                        if not more:
                            raise NativeManagementEvidenceError(
                                "corrupt/truncated native receipt list"
                            )
                        buffer+=more.decode("utf-8")


def _calibration_note(row: dict) -> str:
    matches=[r for r in row["cognitive_sensors"]
             if r.get("component_code") == "CALIBRATION"]
    if len(matches)!=1:
        raise NativeManagementEvidenceError("Native MAX CALIBRATION evidence absent")
    metrics=dict(matches[0]["input_metrics"] + matches[0]["output_metrics"])
    note=metrics.get("note")
    if not isinstance(note,str) or not note.strip():
        raise NativeManagementEvidenceError("Native MAX calibration note missing")
    return note


def classify_native_advisory(row: dict, original: dict) -> dict:
    """Use real causal MAX sensors for a research economic plan, not legacy gates."""
    sid=row.get("signal_fingerprint")
    if (sid!=original["signal_fingerprint"]
        or row.get("trader_id")!=original["trader_id"]
        or row.get("decided_at")!=original["market_decision_at"]):
        raise NativeManagementEvidenceError("native and Trader source drift")
    if not (row.get("native_maximum_intelligence") is True
            and row.get("full_semantics_consumed") is True
            and row.get("outcome_used_for_predecision") is False
            and row.get("external_ai_call_count")==0):
        raise NativeManagementEvidenceError("Native MAX causal semantic integrity not verified")
    disposition=row["capital_disposition"]  # audit only; NEVER controls the plan
    if disposition not in ("COGNITIVE_BLOCK", "CAPITAL_BLOCK", "RISK_REVIEW_READY"):
        raise NativeManagementEvidenceError("Native MAX unknown legacy disposition")
    note=_calibration_note(row)
    plan=native_sensor_management_plan(row)
    mode=plan["mode"]
    return {
        "signal_fingerprint":sid,
        "trader_id":row["trader_id"],
        "decided_at":row["decided_at"],
        "native_max_cognition_read":True,
        "native_max_semantic_digest":row["semantic_digest"],
        "native_legacy_capital_disposition_for_diagnostics_only":disposition,
        "native_max_calibration_note":note,
        "manager_mode_SHADOW_from_native_cognitive_sensors":mode,
        "manager_risk_fraction_of_nav_SHADOW":plan["requested_risk_fraction_of_current_qore_nav"],
        "manager_cognitive_sensor_evidence_SHADOW":plan,
        "manager_exit_policy_SHADOW":plan["exit_policy_SHADOW"],
        "native_cibo_mode_instruction_issued": plan["native_runtime_mode_instruction_consumed"],
        "native_cibo_mode_instruction_sha256": plan["native_runtime_mode_instruction_digest"],
        "bank_medium_attack_request_qdle_physical_lotage": True,
        "trader_signal_received":True,
        "admission_gate_applied":False,
        "economic_stop_and_lot_owned_by_cibo_qdle_not_native_abstract_volume":True,
        "broker_fills_proven":False,
        "managed_exits_reconstructed":False,
    }


def prepare(manifest: dict, native_rows) -> dict:
    rows=manifest["opportunities"]
    original={r["signal_fingerprint"]:r for r in rows}
    if len(rows)!=3368 or len(original)!=3368:
        raise NativeManagementEvidenceError("sealed manifest must have 3368 distinct ids")
    by_id={}
    for row in native_rows:
        sid=row.get("signal_fingerprint")
        if sid not in original or sid in by_id:
            raise NativeManagementEvidenceError("unexpected/duplicate Native MAX signal")
        by_id[sid]=classify_native_advisory(row,original[sid])
    if set(by_id)!=set(original):
        raise NativeManagementEvidenceError("Native MAX failed 3368 coverage")
    receipt_list=[by_id[r["signal_fingerprint"]] for r in rows]
    mode=Counter(r["manager_mode_SHADOW_from_native_cognitive_sensors"] for r in receipt_list)
    native_count = sum(r["native_cibo_mode_instruction_issued"] for r in receipt_list)
    notes=Counter(r["native_max_calibration_note"] for r in receipt_list)
    legacy=Counter(r["native_legacy_capital_disposition_for_diagnostics_only"] for r in receipt_list)
    digest="sha256:"+hashlib.sha256(json.dumps(
        receipt_list,sort_keys=True,separators=(",",":")
    ).encode()).hexdigest()
    return {
        "schema":"qore.cibo.p0.native-max-3368-received-manager-advisory.v1",
        "source":"SEALED_NATIVE_MAX_3368_INDEPENDENT_REPORT_CAUSAL_ADVISORY",
        "admission_gate_applied":False,
        "cognitive_intelligence_receipts_consumed":3368,
        "trader_signals_received":3368,
        "manager_exit_policies_are_research_hypotheses":True,
        "cognitive_sensor_evidence_controls_qdle_risk_request":True,
        "native_cibo_bank_medium_attack_instructions_issued":native_count,
        "native_cibo_qdle_mode_authority_is_runtime":native_count==3368,
        "legacy_disposition_is_not_an_economic_policy_input":True,
        "exit_price_path_reconstruction_done":False,
        "real_mt5_fills":0,
        "seal_sha256":digest,
        "legacy_dispositions_for_diagnostics":dict(sorted(legacy.items())),
        "native_calibration_notes":dict(sorted(notes.items())),
        "mode_counts":dict(sorted(mode.items())),
        "receipts":receipt_list,
    }


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--native-zip",type=Path)
    p.add_argument("--native-json",type=Path)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if (a.native_zip is None) == (a.native_json is None):
        raise NativeManagementEvidenceError("exactly one Native MAX source required")
    with ZipFile(a.manifest) as z:
        manifest=json.load(z.open(MANIFEST_MEMBER))
    native_source = a.native_json if a.native_json is not None else a.native_zip
    result=prepare(manifest,_stream_receipts(native_source, raw_json=a.native_json is not None))
    if a.native_json is not None:
        result["source"]="FRESH_NATIVE_MAX_REPLAY_3368_SAME_SEALED_TRADER_INPUT"
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("CIBO_NATIVE_MAX_3368_RECONCILED",json.dumps({
        k:v for k,v in result.items() if k!="receipts"
    },sort_keys=True))


if __name__=="__main__":
    main()
