"""Immutable 3,368-signal Trader manifest scheduler, NO legacy quote receipts.

Old stellar-instant-3368.json is an economic result from a different episode,
not an admissible input to new CIBO decisions. Only this manifest may schedule
signals in Native MAX replay.
"""
from __future__ import annotations
from datetime import datetime


class CiboP0ManifestSourceError(ValueError):
    pass


def original_chronological_signals(manifest: dict, *, expected_count: int = 3368) -> tuple[dict, ...]:
    if not isinstance(manifest,dict):
        raise CiboP0ManifestSourceError("sealed Trader manifest required")
    rows=manifest.get("opportunities")
    if not isinstance(rows,list) or len(rows)!=expected_count:
        raise CiboP0ManifestSourceError("canonical sealed Trader signal count drift")
    seen=set()
    output=[]
    for row in rows:
        if not isinstance(row,dict):
            raise CiboP0ManifestSourceError("malformed original opportunity")
        sid=row.get("signal_fingerprint")
        symbol=row.get("qore_symbol")
        trader=row.get("trader_id")
        at=row.get("market_decision_at")
        if not all(isinstance(x,str) and x for x in (sid,symbol,trader,at)):
            raise CiboP0ManifestSourceError("missing original Trader signal identity")
        if sid in seen:
            raise CiboP0ManifestSourceError("duplicate original fingerprint")
        seen.add(sid)
        try:
            dt=datetime.fromisoformat(at)
        except ValueError as err:
            raise CiboP0ManifestSourceError("bad original observation time") from err
        if dt.tzinfo is None or dt.utcoffset() is None:
            raise CiboP0ManifestSourceError("historical Trader timestamp not aware")
        output.append({
            "signal_fingerprint":sid,
            "at":dt.isoformat(),
            "signal_at":at,
            "symbol":symbol,
            "trader":trader,
        })
    output.sort(key=lambda r:(datetime.fromisoformat(r["at"]),r["signal_fingerprint"]))
    return tuple(output)
