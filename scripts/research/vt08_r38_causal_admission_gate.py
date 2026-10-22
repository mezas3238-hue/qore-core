"""VT08 R38: conservative research-only causal admission clock gate."""
from datetime import datetime

def utc(value):
    if not isinstance(value, str): raise ValueError("missing timestamp")
    t=datetime.fromisoformat(value.replace("Z","+00:00"))
    if t.tzinfo is None or t.utcoffset().total_seconds()!=0: raise ValueError("not UTC")
    return t

def audit_case(row):
    for field in ("case_id_sha256","market","c3_decision_at_utc","first_cisd_closed_at_utc"):
        if not row.get(field):
            return {"status":"WAIT","reason":"MISSING_"+field.upper(),"trade_authorized":False}
    try:
        c3=utc(row["c3_decision_at_utc"]); first=utc(row["first_cisd_closed_at_utc"])
        reason=("INITIAL_AFTER_C3" if first>c3 else "INITIAL_SAME_TIMESTAMP_C3" if first==c3 else "INITIAL_STRICTLY_BEFORE_C3")
        reclaim=row.get("first_close_reclaiming_old_level_available_at_utc")
        if row.get("post_cisd_lower_than_reanchored_low"):
            if reclaim is None: timing="NO_RECLAIM"
            else:
                t=utc(reclaim)
                timing=("AFTER_C3" if t>c3 else "SAME_TIMESTAMP_C3" if t==c3 else "STRICTLY_BEFORE_C3")
        else: timing="NOT_APPLICABLE"
    except (ValueError,TypeError,OverflowError):
        return {"status":"WAIT","reason":"INVALID_TIMESTAMP","trade_authorized":False}
    return {"status":"WAIT","reason":reason,"reclaim_timing":timing,"trade_authorized":False,"source_semantics_certified":False}

def audit_batch(rows):
    seen=set();out=[]
    for row in rows:
        key=(row.get("market"),row.get("case_id_sha256"))
        if key in seen:raise ValueError("duplicate case")
        seen.add(key);out.append(audit_case(row))
    return out
