"""SHA-pinned proof of raw cTrader provider trendbar.volume -> 33 RAW rows.

This is SOURCE CODE genealogy, not proof of same demo account, exchange order
volume, full provider capture correctness, or real broker Bid/Ask execution.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
from pathlib import Path

ORIGINAL_HEAD = "ab782b8e9f890f86a2b6500070f0556b4b685e3d"
NEW_HEAD = "e0ca5a13c866a19d8505c68cffc473598984b340"
BASE = "src/qore/infrastructure/trader_lab/cibo_market_atlas_10y_m5_consumer_v1.py"
PATCH = "src/qore/infrastructure/trader_lab/qore_native_icmarkets_missing_m5_capture_v1.py"
TRANSPORT = "src/qore/infrastructure/trader_lab/cibo_market_atlas_10y_windowed_runtime_v1.py"
PINNED = {
    "original12_native_normalizer": (ORIGINAL_HEAD, BASE,
        "370c33bd91c5be3b6ee3d3030a95cf52c18ca28a"),
    "new21_original_base_normalizer": (NEW_HEAD, BASE,
        "370c33bd91c5be3b6ee3d3030a95cf52c18ca28a"),
    "new21_wrapper": (NEW_HEAD, PATCH,
        "cb3e325ffec3b02e07453cb851578be9b4639697"),
    "original12_windowed_transport": (ORIGINAL_HEAD, TRANSPORT,
        "a8ad7fca6b5b6e3a4a61076f6f81be5c26b7e116"),
}


def git_blob(head: str, path: str) -> tuple[bytes, str]:
    out = subprocess.run(
        ["git", "show", f"{head}:{path}"],
        check=True, capture_output=True, timeout=10,
    ).stdout
    git_sha = hashlib.sha1(
        b"blob " + str(len(out)).encode("ascii") + b"\0" + out
    ).hexdigest()
    return out, git_sha


def _method(source: str, name: str) -> ast.FunctionDef:
    module = ast.parse(source)
    found = [x for x in module.body
             if isinstance(x,ast.FunctionDef) and x.name == name]
    if len(found) != 1:
        raise ValueError(f"frozen producer method absent: {name}")
    return found[0]


def _name_call(root: ast.AST, method: str) -> bool:
    return any(isinstance(z,ast.Call) and isinstance(z.func,ast.Attribute)
               and isinstance(z.func.value,ast.Name)
               and z.func.value.id == method.split(".")[0]
               and z.func.attr == method.split(".")[1]
               for z in ast.walk(root))


def verify_lineage() -> dict:
    frozen = {}
    for key, (sha,path,blob) in PINNED.items():
        raw,digest = git_blob(sha,path)
        if digest != blob:
            raise ValueError("ORIGINAL_FROZEN_PRODUCER_CODE_GIT_BLOB_DRIFT:"+key)
        frozen[key] = raw.decode("utf-8")
    base = frozen["original12_native_normalizer"]
    if frozen["new21_original_base_normalizer"] != base:
        raise ValueError("new21 copied a different relative-price/volume normalizer")
    native = _method(base,"_provider_bar")
    returns = [n for n in ast.walk(native)
               if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)
               and n.func.id == "RawM5Bar"]
    if len(returns)!=1:
        raise ValueError("original native RawM5Bar constructor changed")
    volume_arg = [x.value for x in returns[0].keywords if x.arg=="volume"]
    if len(volume_arg)!=1:
        raise ValueError("volume missing from raw provider constructor")
    expr = volume_arg[0]
    if not (isinstance(expr,ast.Call) and isinstance(expr.func,ast.Name)
            and expr.func.id == "_optional_native_int"
            and len(expr.args)==2
            and isinstance(expr.args[0],ast.Name) and expr.args[0].id=="native"
            and isinstance(expr.args[1],ast.Constant)
            and expr.args[1].value=="volume"):
        raise ValueError("provider volume field is transformed by source")
    optional = _method(base, "_optional_native_int")
    if not any(isinstance(node,ast.Return)
               and isinstance(node.value,ast.Name)
               and node.value.id=="raw" for node in ast.walk(optional)):
        raise ValueError("optional provider native int not passed through")
    wrapper = frozen["new21_wrapper"]
    install = _method(wrapper, "activate_capture")
    entry = _method(wrapper, "main")
    if not (_name_call(install,"windowed.install_windowed_transport")
            and _name_call(entry,"base.main")
            and any(isinstance(x,ast.Assign)
                    and any(isinstance(y,ast.Attribute)
                            and isinstance(y.value,ast.Name)
                            and y.value.id=="base" and y.attr=="RAW_SCHEMA"
                            for y in x.targets)
                    for x in ast.walk(install))):
        raise ValueError("new21 historical base consumer not reused")
    window = frozen["original12_windowed_transport"]
    call = _method(window,"read_windowed_chunk")
    code = ast.get_source_segment(window,call) or ""
    if ('"count"' in code or '"fromTimestamp"' not in code
            or '"toTimestamp"' not in code
            or '"ProtoOAGetTrendbarsReq"' not in code):
        raise ValueError("original provider M5 transport unexpected")
    return {
        "identity":"QORE_ALPHA2_G2_33_MARKET_PROVIDER_VOLUME_LINEAGE_SHA_PIN_V1",
        "source_normalizer_producer_head":ORIGINAL_HEAD,
        "new_capture_producer_head":NEW_HEAD,
        "pinned_blobs":{
            key:{"head":spec[0],"path":spec[1],"git_blob_sha":spec[2]}
            for key,spec in sorted(PINNED.items())
        },
        "old12_volume_exact_native_field_pass_through":True,
        "new21_reuses_same_original_raw_normalizer":True,
        "original_transport_gettrendbars_only_from_to":True,
        "volume_semantics":"CTRADER_PROTOOATRENDBAR_TICK_COUNT_NOT_EXCHANGE_VOLUME",
        "pinned_archive_raw_annual_SHA_33_verified_other_pipeline":True,
        "same_broker_demo_account_between_cohorts_proven":False,
        "historical_BID_ASK_or_spread_proven":False,
        "net_certification_authorized":False,
        "no_broker_order_or_token_access":True,
    }


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("output",type=Path)
    x=p.parse_args()
    witness=verify_lineage()
    x.output.parent.mkdir(parents=True,exist_ok=True)
    x.output.write_text(json.dumps(witness,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({
        "status":witness["identity"],
        "old12_same_volume_as_new21":True,
        "same_account":False,"net_authorized":False,
    },sort_keys=True))


if __name__=="__main__":
    main()
