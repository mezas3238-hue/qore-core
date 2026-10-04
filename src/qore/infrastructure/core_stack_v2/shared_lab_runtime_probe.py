"""Runtime instrumentation for QORE Shared Lab native-engine and cable reality.

The probe is neutral instrumentation: it executes a supplied native callable,
fingerprints exact inputs/outputs and creates receipts that downstream probes can
bind without recreating evidence.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import time
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, is_dataclass
from typing import Any

from qore.infrastructure.core_stack_v2.shared_lab import (
    CableRealityReceipt,
    EngineKind,
    NativeEngineReceipt,
)


def _canonical(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Mapping):
        return {
            str(key): _canonical(item)
            for key, item in sorted(
                value.items(),
                key=lambda pair: str(pair[0]),
            )
        }
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "value") and isinstance(value.value, (str, int, float, bool)):
        return value.value
    return repr(value)


def fingerprint_payload(value: Any) -> str:
    raw = json.dumps(_canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class NativeInvocationTrace:
    capability_id: str
    engine_id: str
    callable_module: str
    callable_qualname: str
    input_fingerprint: str
    output_fingerprint: str
    latency_ns: int
    output_type: str
    native_receipt: NativeEngineReceipt


@dataclass(frozen=True, slots=True)
class DownstreamConsumptionTrace:
    producer_capability_id: str
    consumer_capability_id: str
    producer_output_fingerprint: str
    consumer_input_fingerprint: str
    consumer_output_fingerprint: str
    consumer_invoked: bool
    consumer_changed_output: bool
    cable_receipt: CableRealityReceipt


def invoke_native_engine(
    *,
    capability_id: str,
    engine_id: str,
    engine: Callable[..., Any],
    args: tuple[Any, ...] = (),
    kwargs: Mapping[str, Any] | None = None,
    downstream_native_consumer: str,
) -> tuple[Any, NativeInvocationTrace]:
    if not capability_id.strip() or not engine_id.strip() or not downstream_native_consumer.strip():
        raise ValueError("native invocation identities are required")
    if not callable(engine):
        raise TypeError("engine must be callable")
    module = inspect.getmodule(engine)
    module_name = module.__name__ if module is not None else ""
    qualname = getattr(engine, "__qualname__", getattr(engine, "__name__", ""))
    if not module_name or not qualname:
        raise ValueError("native engine callable must expose module and qualname")

    call_kwargs = dict(kwargs or {})
    input_payload = {"args": args, "kwargs": call_kwargs}
    input_fp = fingerprint_payload(input_payload)
    started = time.perf_counter_ns()
    output = engine(*args, **call_kwargs)
    latency_ns = time.perf_counter_ns() - started
    output_fp = fingerprint_payload(output)

    receipt = NativeEngineReceipt(
        capability_id=capability_id,
        engine_id=engine_id,
        engine_kind=EngineKind.NATIVE,
        real_input=True,
        native_engine_exists=True,
        native_engine_called=True,
        typed_output_emitted=output is not None,
        downstream_native_consumer=downstream_native_consumer,
    )
    return output, NativeInvocationTrace(
        capability_id=capability_id,
        engine_id=engine_id,
        callable_module=module_name,
        callable_qualname=qualname,
        input_fingerprint=input_fp,
        output_fingerprint=output_fp,
        latency_ns=latency_ns,
        output_type=type(output).__qualname__,
        native_receipt=receipt,
    )


def consume_exact_output(
    *,
    producer_trace: NativeInvocationTrace,
    consumer_capability_id: str,
    consumer: Callable[[Any], Any],
    producer_output: Any,
) -> tuple[Any, DownstreamConsumptionTrace]:
    if not consumer_capability_id.strip():
        raise ValueError("consumer capability identity is required")
    parent_fp = fingerprint_payload(producer_output)
    if parent_fp != producer_trace.output_fingerprint:
        raise ValueError("producer output does not match invocation trace fingerprint")

    before_fp = parent_fp
    output = consumer(producer_output)
    output_fp = fingerprint_payload(output)
    receipt = CableRealityReceipt(
        producer=producer_trace.capability_id,
        consumer=consumer_capability_id,
        producer_output_sha256=producer_trace.output_fingerprint,
        consumer_input_parent_sha256=parent_fp,
        observed=True,
        consumed=True,
        decision_changed=output_fp != before_fp,
    )
    return output, DownstreamConsumptionTrace(
        producer_capability_id=producer_trace.capability_id,
        consumer_capability_id=consumer_capability_id,
        producer_output_fingerprint=producer_trace.output_fingerprint,
        consumer_input_fingerprint=parent_fp,
        consumer_output_fingerprint=output_fp,
        consumer_invoked=True,
        consumer_changed_output=output_fp != before_fp,
        cable_receipt=receipt,
    )
