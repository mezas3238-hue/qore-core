"""Resolve consumed VT-31 later same-M1 stop/target ambiguity for an open position.

The position is already open before each supplied window. Therefore there is no
entry event to infer. Long exits are evaluated on BID; short exits on ASK. The
first executable stop/target event on that one quote stream wins. Missing or
contradictory evidence remains censored. Consumed evidence only; no fresh access.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

from vt31_tick_execution_resolution import TickResolutionError, _price, _timestamp, _validated_stream


def _predicate(side: str, kind: str, threshold: Decimal) -> Callable[[Decimal], bool]:
    if kind == "stop":
        return (lambda price: price <= threshold) if side == "long" else (lambda price: price >= threshold)
    if kind == "target":
        return (lambda price: price >= threshold) if side == "long" else (lambda price: price <= threshold)
    raise AssertionError(kind)


def resolve_window(source: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    window_id = source.get("window_id")
    if not isinstance(window_id, str) or not window_id:
        raise TickResolutionError("open-position source id is malformed")
    evidence_source = evidence.get("source_window")
    if not isinstance(evidence_source, dict) or evidence_source.get("window_id") != window_id:
        raise TickResolutionError("open-position evidence/source identity mismatch")
    side = source.get("side")
    if side not in {"long", "short"}:
        raise TickResolutionError("open-position side is malformed")
    opened_ms = source.get("tick_window_open_ms")
    closed_ms = source.get("tick_window_close_ms")
    if type(opened_ms) is not int or type(closed_ms) is not int or closed_ms <= opened_ms:
        raise TickResolutionError("open-position tick boundaries are malformed")
    entry = Decimal(str(source["entry"]))
    stop = Decimal(str(source["current_protected_stop"]))
    target = Decimal(str(source["fixed_2r_target"]))
    risk = Decimal(str(source["initial_risk"]))
    if min(entry, stop, target, risk) <= 0:
        raise TickResolutionError("open-position prices/risk must be positive")
    if side == "long" and not stop < target:
        raise TickResolutionError("long protected stop must be below target")
    if side == "short" and not target < stop:
        raise TickResolutionError("short target must be below protected stop")

    stream_name = "bid" if side == "long" else "ask"
    stream = _validated_stream(evidence, stream_name, opened_ms, closed_ms)
    if not stream:
        return {
            "window_id": window_id,
            "status": "unresolved-missing-exit-quote-side",
            "side": side,
            "exit_quote_side": stream_name.upper(),
            "terminal_timestamp_ms": None,
            "terminal_r": None,
        }
    stop_pred = _predicate(side, "stop", stop)
    target_pred = _predicate(side, "target", target)
    stop_tick = next((tick for tick in stream if stop_pred(_price(tick))), None)
    target_tick = next((tick for tick in stream if target_pred(_price(tick))), None)
    candidates: list[tuple[int, str, str]] = []
    if stop_tick is not None:
        stop_r = (stop - entry) / risk if side == "long" else (entry - stop) / risk
        candidates.append((_timestamp(stop_tick), "terminal-protected-stop", format(stop_r, "f")))
    if target_tick is not None:
        candidates.append((_timestamp(target_tick), "terminal-fixed-2r-target", "2"))
    if not candidates:
        return {
            "window_id": window_id,
            "status": "unresolved-no-executable-stop-or-target-in-source-bar",
            "side": side,
            "exit_quote_side": stream_name.upper(),
            "terminal_timestamp_ms": None,
            "terminal_r": None,
        }
    candidates.sort(key=lambda item: (item[0], item[1]))
    first_ms = candidates[0][0]
    tied = [item for item in candidates if item[0] == first_ms]
    if len(tied) != 1:
        return {
            "window_id": window_id,
            "status": "unresolved-same-ms-stop-target-order",
            "side": side,
            "exit_quote_side": stream_name.upper(),
            "terminal_timestamp_ms": first_ms,
            "terminal_r": None,
        }
    terminal_ms, status, terminal_r = tied[0]
    return {
        "window_id": window_id,
        "status": status,
        "side": side,
        "exit_quote_side": stream_name.upper(),
        "terminal_timestamp_ms": terminal_ms,
        "terminal_r": terminal_r,
    }


def _load_acquisition(root: Path) -> dict[str, dict[str, Any]]:
    summary=json.loads((root/'vt31-bounded-tick-acquisition-summary.json').read_text())
    if summary.get('research_only') is not True or summary.get('opens_new_holdout') is not False:
        raise TickResolutionError('acquisition governance guard failed')
    rows=summary.get('results')
    if not isinstance(rows,list):
        raise TickResolutionError('acquisition rows malformed')
    return {str(row['window_id']): row for row in rows if isinstance(row,dict)}


def _evidence(root: Path, row: dict[str, Any]) -> dict[str, Any]:
    if row.get('status') != 'available':
        raise TickResolutionError('open-position acquisition row unavailable')
    filename=row.get('evidence_file')
    if not isinstance(filename,str) or not filename:
        raise TickResolutionError('open-position evidence filename missing')
    return json.loads((root/'windows'/filename).read_text())


def resolve_manifest(manifest_path: Path, acquisition_dir: Path, output_path: Path) -> dict[str, Any]:
    manifest=json.loads(manifest_path.read_text())
    if manifest.get('research_only') is not True or manifest.get('opens_new_holdout') is not False:
        raise TickResolutionError('manifest governance guard failed')
    windows=manifest.get('windows')
    if not isinstance(windows,list) or not windows:
        raise TickResolutionError('open-position ambiguity manifest malformed')
    by_id=_load_acquisition(acquisition_dir)
    if len(by_id) != len(windows):
        raise TickResolutionError('open-position acquisition cardinality mismatch')
    results=[]
    for source in windows:
        if not isinstance(source,dict):
            raise TickResolutionError('open-position source row malformed')
        window_id=source.get('window_id')
        if not isinstance(window_id,str) or window_id not in by_id:
            raise TickResolutionError('open-position acquisition identity mismatch')
        row=by_id[window_id]
        if row.get('status') != 'available':
            result={
                'window_id':window_id,
                'status':'unresolved-acquisition-not-available',
                'side':source.get('side'),
                'terminal_timestamp_ms':None,
                'terminal_r':None,
            }
        else:
            result=resolve_window(source,_evidence(acquisition_dir,row))
        result.update({
            'parent_window_id':source.get('parent_window_id'),
            'partition':source.get('partition'),
            'market':source.get('market'),
            'ny_date':source.get('ny_date'),
        })
        results.append(result)
    counts=Counter(str(row['status']) for row in results)
    payload={
        'schema':'qore.vt31.consumed_open_position_tick_exit_resolution.v1',
        'research_only':True,
        'opens_new_holdout':False,
        'candidate_status':'NO_R9_NOT_CERTIFIED',
        'source_window_count':len(windows),
        'semantics':{
            'position_state':'already-open-before-window',
            'long_exit_quote_side':'BID',
            'short_exit_quote_side':'ASK',
            'first_executable_terminal_event':'wins',
            'missing_or_contradictory_evidence':'censor-no-imputation',
        },
        'counts':dict(sorted(counts.items())),
        'results':results,
    }
    output_path.write_text(json.dumps(payload,sort_keys=True,indent=2)+'\n')
    return payload


def self_test() -> None:
    long_source={
        'window_id':'x','side':'long','entry':'100','current_protected_stop':'100.5',
        'fixed_2r_target':'102','initial_risk':'1','tick_window_open_ms':1,'tick_window_close_ms':59_999,
    }
    evidence={'source_window':dict(long_source),'bid':[_tick(1_000,'101'),_tick(2_000,'100.4'),_tick(3_000,'102.1')],'ask':[]}
    result=resolve_window(long_source,evidence)
    assert result['status']=='terminal-protected-stop'
    assert result['terminal_r']=='0.5'
    short_source={
        'window_id':'y','side':'short','entry':'100','current_protected_stop':'99.5',
        'fixed_2r_target':'98','initial_risk':'1','tick_window_open_ms':1,'tick_window_close_ms':59_999,
    }
    evidence={'source_window':dict(short_source),'bid':[],'ask':[_tick(1_000,'99'),_tick(2_000,'97.9'),_tick(3_000,'99.6')]}
    result=resolve_window(short_source,evidence)
    assert result['status']=='terminal-fixed-2r-target'
    assert result['terminal_r']=='2'


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument('--manifest',type=Path)
    parser.add_argument('--acquisition-dir',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--self-test',action='store_true')
    args=parser.parse_args()
    if args.self_test:
        self_test(); print('vt31 open-position tick exit resolver self-test: PASS'); return
    if args.manifest is None or args.acquisition_dir is None or args.output is None:
        parser.error('manifest/acquisition/output required unless --self-test')
    payload=resolve_manifest(args.manifest,args.acquisition_dir,args.output)
    print(json.dumps(payload['counts'],sort_keys=True))


if __name__=='__main__':
    main()
