"""Freeze initial fill-bar parity windows for the four original later ambiguities.

The four roots already have exact consumed identity and a later ambiguous bar.
This script replays only enough frozen M1 mechanics to locate each root's first
entry-touch bar before 11:00 NY, so the original fill itself can be validated on
the executable quote side. No rule changes and no fresh evidence are introduced.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import vt31_r5_candidate as r5
from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import _day, _wall, load_market_evidence

MARKETS=("NAS100","SP500","US30")
PARTITIONS=("r5","r6","r8_fresh")


def _d(value: float) -> Decimal:
    return Decimal(str(value))


def _ms(value: object) -> int:
    return int(getattr(value,"astimezone")(UTC).timestamp()*1000)


def _days(path: Path) -> tuple[dict[date,tuple[object,...]], str]:
    series,_,_,_,_,provider=load_market_evidence(path)
    grouped:dict[date,list[object]]=defaultdict(list)
    for bar in series:
        grouped[_day(bar.opened_at)].append(bar)
    return {key:tuple(value) for key,value in grouped.items()},provider


def build(source_path: Path,evidence_paths: dict[tuple[str,str],Path],output_path: Path) -> dict[str,Any]:
    source=json.loads(source_path.read_text())
    if source.get('research_only') is not True or source.get('opens_new_holdout') is not False:
        raise ValueError('source governance guard failed')
    roots=source.get('windows')
    if not isinstance(roots,list) or len(roots)!=4:
        raise ValueError('expected exact four original later roots')
    caches={key:_days(path) for key,path in evidence_paths.items()}
    rows=[]
    for root in roots:
        if not isinstance(root,dict):
            raise ValueError('root row malformed')
        partition=str(root['partition']); market=str(root['market'])
        day_map,provider=caches[(partition,market)]
        if provider!=root['provider']:
            raise ValueError('provider mismatch')
        local_day=date.fromisoformat(str(root['ny_date']))
        bars=day_map.get(local_day)
        if bars is None:
            raise ValueError('root day missing')
        signal=datetime.fromisoformat(str(root['signal_opened_at']))
        signal_indexes=[i for i,b in enumerate(bars) if getattr(b,'opened_at').astimezone(UTC)==signal.astimezone(UTC)]
        if len(signal_indexes)!=1:
            raise ValueError('root signal bar identity mismatch')
        entry=Decimal(str(root['entry']))
        fill_index=None
        for index in range(signal_indexes[0]+1,len(bars)):
            bar=bars[index]
            if _wall(getattr(bar,'opened_at')) >= (11,0,0):
                break
            if index>signal_indexes[0]+1 and getattr(bar,'opened_at')!=getattr(bars[index-1],'closed_at'):
                raise ValueError('fill search continuity gap')
            if r5._touch(bar,entry):
                fill_index=index
                break
        if fill_index is None:
            raise ValueError('original later ambiguity unexpectedly lacks M1 entry touch')
        fill=bars[fill_index]
        stop=Decimal(str(root['initial_stop']))
        target=Decimal(str(root['fixed_2r_target']))
        side=str(root['side'])
        low=_d(cast(float,getattr(fill,'low'))); high=_d(cast(float,getattr(fill,'high')))
        hit_stop=low<=stop if side=='long' else high>=stop
        hit_target=high>=target if side=='long' else low<=target
        if hit_stop or hit_target:
            raise ValueError('original later ambiguity unexpectedly has fill-bar terminal touch')
        row={
            'root_id':root['root_id'],
            'partition':partition,
            'market':market,
            'provider':provider,
            'ny_date':root['ny_date'],
            'side':side,
            'signal_opened_at':root['signal_opened_at'],
            'entry':root['entry'],
            'initial_stop':root['initial_stop'],
            'fixed_2r_target':root['fixed_2r_target'],
            'fill_bar_opened_at':getattr(fill,'opened_at').astimezone(UTC).isoformat(),
            'fill_bar_closed_at':getattr(fill,'closed_at').astimezone(UTC).isoformat(),
            'tick_window_open_ms':_ms(getattr(fill,'opened_at')),
            'tick_window_close_ms':_ms(getattr(fill,'closed_at'))-1,
            'm1_low':format(low,'f'),
            'm1_high':format(high,'f'),
            'classification':'original-later-root-initial-fill-parity',
        }
        material=json.dumps(row,sort_keys=True,separators=(',',':'))
        row['window_id']=hashlib.sha256(material.encode()).hexdigest()[:24]
        rows.append(row)
    rows.sort(key=lambda row:(row['partition'],row['tick_window_open_ms'],row['market']))
    if len({row['root_id'] for row in rows})!=4 or len({row['window_id'] for row in rows})!=4:
        raise ValueError('fill parity identities not unique')
    payload={
        'schema':'qore.vt31.consumed_original_later_initial_fill_parity_manifest.v1',
        'research_only':True,
        'opens_new_holdout':False,
        'candidate_status':'NO_R9_NOT_CERTIFIED',
        'source_original_later_root_count':4,
        'windows':rows,
    }
    canonical=json.dumps(payload,sort_keys=True,separators=(',',':'))
    payload['sha256']=hashlib.sha256(canonical.encode()).hexdigest()
    output_path.write_text(json.dumps(payload,sort_keys=True,indent=2)+'\n')
    return payload


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    for partition in PARTITIONS:
        for market in MARKETS:
            parser.add_argument(f"--{partition.replace('_','-')}-{market.lower()}",required=True,type=Path)
    args=parser.parse_args()
    paths={(partition,market):getattr(args,f"{partition}_{market.lower()}") for partition in PARTITIONS for market in MARKETS}
    payload=build(args.source,paths,args.output)
    print(json.dumps({'count':len(payload['windows'])},sort_keys=True))


if __name__=='__main__':
    main()
