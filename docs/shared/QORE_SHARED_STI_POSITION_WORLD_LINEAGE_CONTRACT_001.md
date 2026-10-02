# QORE Shared STI-7/STI-9 — Position World Lineage Contract 001

## Status

**IMPLEMENTED CONTRACT / NON-PRODUCTIVE / NO POSITION AUTHORITY**

Primary PR: #635  
Owner directive: `QORE_SHARED_PROACTIVE_TRADER_INTELLIGENCE_OWNER_DIRECTIVE_007.md`

## Purpose

Make position monitoring causal rather than retrospective.

Shared must preserve:

```text
WORLD_STATE_AT_ENTRY
```

and later compare it to:

```text
WORLD_STATE_NOW
```

without rewriting entry truth after the position outcome becomes known.

## Entry-world law

`SharedPositionEntryWorldRecord` is committed at the position opening event.

Required chronology:

```text
entry_snapshot.evidence_cutoff_at
<= entry_snapshot.observed_at
<= position.opened_at
== entry_world_record.captured_at
```

A snapshot observed after the position opens cannot become the entry-world
snapshot.

A later post-hoc reconstruction cannot claim to be the original entry state.

## Current-world comparison

`SharedPositionWorldNowDelta` compares immutable entry truth with a current
Shared snapshot.

It records factual changes in:

- world state;
- market regime;
- macro regime;
- relationship coherence;
- relationship stability;
- elapsed causal time.

It does not classify the economic threat level. That belongs to later STI-8
research.

## Authority law

The entry record and factual delta carry no:

- position-management authority;
- forced exit;
- stop/target authority;
- sizing authority;
- Risk authority;
- execution authority.

```text
WORLD CHANGE OBSERVATION
!=
POSITION MANAGEMENT COMMAND
```

## Scientific consequence

STI-8 Position Threat Intelligence may consume this lineage only after its own
policy is preregistered and validated.

Later outcome analysis may evaluate whether a warning was useful, but future
position outcome may not enter either the entry record or historical
world-now comparison.

## Productive status

```text
ENTRY WORLD LINEAGE CONTRACT = IMPLEMENTED
POSITION THREAT MODEL = NOT CERTIFIED
TRADER POSITION BEHAVIOR CHANGE = NOT AUTHORIZED
PROTECTED HOLDOUT OPENED = FALSE
```
