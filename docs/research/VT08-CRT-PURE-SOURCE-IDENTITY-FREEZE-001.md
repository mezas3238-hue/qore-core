# VT08 CRT PURE — SOURCE & IDENTITY FREEZE 001

**Status:** IMPLEMENTATION FOUNDATION / RESEARCH ONLY / NOT CERTIFIED  
**Repository:** `mezas3238-hue/qore-core`  
**Branch:** `agent/vt08-crt-pure-source-identity-001`  
**Parent architecture:** PR #622 / `53b04147eb145b8570901811e414c02cc89f9bdf`  
**Scope:** CRT PURE only

## 0. Owner directive

This lineage builds a **pure CRT trader** for exactly three initial markets:

- AUDUSD
- USDJPY
- BTCUSD

CRT-AMD is explicitly excluded from this work.

No rule, parameter, timing convention, entry family, stop model, target model, hierarchy,
or market behavior may be inherited from the historical `crt-4h-amd` evaluator merely
because it contains the string CRT.

The historical PR #516 remains immutable research lineage. It may provide source-discovery
clues, but its machine operationalizations are not automatically part of this new trader.

## 1. Methodology identity

Canonical trader family identity:

```text
methodology_family = CRT
methodology_variant = PURE
initial_markets = [AUDUSD, USDJPY, BTCUSD]
```

The methodology contract is common across the three markets. Market behavior is not.

```text
CRT Identity = common source-faithful methodology

AUDUSD Experience != USDJPY Experience != BTCUSD Experience
```

A market-specific observation can become market experience only through governed research.
It cannot rewrite the common CRT methodology identity.

## 2. Canonical source hierarchy

### LEVEL A — canonical authority: RomeoTPT

Primary authority for CRT methodology:

- original RomeoTPT videos;
- original RomeoTPT posts;
- original RomeoTPT examples;
- original RomeoTPT explanations;
- original RomeoTPT source material.

When Level A explicitly defines a rule, lower levels cannot override it.

### LEVEL A+ — author-distributed documents

Documents distributed directly by RomeoTPT are primary evidence when provenance can be
bound to the author's official distribution channel.

Examples include author-distributed PDFs such as `KOD.pdf`.

Required evidence binding when available:

- source URL / official channel location;
- publication date or retrieval date;
- local immutable SHA-256 for retained binary/text;
- page or timestamp locator;
- transcript/excerpt identifier used for adjudication.

### LEVEL B — corroboration, not authority

Approved secondary corroboration sources:

- SpeculatorFL
- TraderFlameseN
- TTrades

Level B may:

- clarify terminology;
- point to a RomeoTPT concept;
- surface examples;
- expose ambiguity;
- provide an independent interpretation to falsify.

Level B may **not** override an explicit Level A or Level A+ rule.

## 3. Explicit exclusion boundary

The following are not methodology authority for this lineage:

- `Vt08Crt4hAmd`;
- methodology id `crt-4h-amd`;
- AMD rules;
- PO3/AMD rules imported by analogy;
- old VT08 CRT machine choices not proven source-faithful;
- economic tuning results used to reverse-engineer methodology;
- third-party CRT websites/courses not in the approved source hierarchy.

An excluded concept can enter CRT PURE only if independently supported by the approved
source corpus as an actual CRT rule.

## 4. Source-adjudication law

No machine-level CRT rule is canonical until it has an evidence record with:

1. concept id;
2. exact source tier;
3. source identity/provenance;
4. location (video timestamp, post, page, section);
5. normalized rule statement;
6. ambiguity notes;
7. contradiction notes;
8. adjudication state.

Allowed adjudication states:

- `CANONICAL`
- `CORROBORATED`
- `AMBIGUOUS`
- `NOT_SOURCE_SUPPORTED`

Only `CANONICAL` rules may enter the common CRT Strategy Identity contract.

`CORROBORATED` evidence may strengthen interpretation but cannot independently create a
methodology rule.

`AMBIGUOUS` rules fail closed until resolved.

`NOT_SOURCE_SUPPORTED` rules are prohibited from the strategy identity.

## 5. Initial concept register — research questions, not frozen rules

The source corpus must adjudicate at least:

- CRT reference candle/range identity;
- CRH / CRL;
- equilibrium / midpoint semantics;
- liquidation / sweep identity;
- one-sided versus two-sided sweep;
- close-back-inside / reclaim;
- acceptance outside the range;
- Candle 1 / Candle 2 / Candle 3 semantics;
- KOD (Kiss of Death);
- Journey;
- Key Levels;
- invalidation;
- opportunity expiry;
- higher-timeframe / lower-timeframe nesting;
- permitted timeframe hierarchy;
- time/session rules, if any;
- entry family/families;
- structural stop;
- structural destination/target;
- continuation versus reversal;
- failure conditions;
- rearm/new-opportunity identity;
- same-bar ambiguity;
- BTCUSD-specific continuous-market implications if source-supported.

This list is a source-audit agenda. It does not assert that every item becomes an executable
rule.

## 6. Three-market topology

### AUDUSD

Own CRT Experience Memory and market research ledger.

No USDJPY/BTCUSD learned rule is silently transferred into AUDUSD.

### USDJPY

Own CRT Experience Memory and market research ledger.

No AUDUSD/BTCUSD learned rule is silently transferred into USDJPY.

### BTCUSD

Own CRT Experience Memory and market research ledger.

FX weekday/session assumptions are prohibited unless source evidence and BTCUSD-specific
market research independently support them.

## 7. Cognitive topology

The frozen architecture from PR #622 remains applicable:

```text
CRT STRATEGY IDENTITY
        +
CIBO MARKET MEMORY
        +
MARKET-SPECIFIC CRT EXPERIENCE
        |
CAUSAL SITUATION MODEL
        |
CRT REASONING
        |
EXECUTE / WAIT / ABSTAIN
        |
JOURNEY / DESTINATION
        |
POSITION INTELLIGENCE
        |
CIBO
        |
QORE RISK
        |
EXECUTION
```

CIBO and market experience cannot rewrite CRT methodology.

ABSTAIN cannot be bypassed by a fallback path using the same source event.

## 8. Research order

Mandatory order:

```text
APPROVED SOURCE CORPUS
    ->
SOURCE ADJUDICATION
    ->
PURE CRT STRATEGY IDENTITY FREEZE
    ->
DETERMINISTIC IMPLEMENTATION
    ->
AUDUSD / USDJPY / BTCUSD REPLAY
    ->
PER-MARKET FORENSICS & EXPERIENCE
    ->
FALSIFICATION
    ->
FROZEN CANDIDATE
    ->
UNSEEN VALIDATION
    ->
CERTIFICATION
```

Economic results may falsify a candidate. They may not silently redefine what CRT means.

## 9. Current authority state

- `CRT_AMD_EXCLUDED = TRUE`
- `CRT_PURE_SCOPE_FROZEN = TRUE`
- `SUPPORTED_MARKETS = AUDUSD, USDJPY, BTCUSD`
- `SOURCE_HIERARCHY_FROZEN = TRUE`
- `SOURCE_ADJUDICATION_COMPLETE = FALSE`
- `STRATEGY_IDENTITY_COMPLETE = FALSE`
- `DETERMINISTIC_ENTRY_IMPLEMENTED = FALSE`
- `CRT_CANDIDATE_FROZEN = FALSE`
- `CRT_CERTIFIED = FALSE`
- `DEMO_AUTHORIZED = FALSE`
- `LIVE_AUTHORIZED = FALSE`
- `REAL_CAPITAL_AUTHORIZED = FALSE`
- `PRODUCTION_AUTHORIZED = FALSE`

The next engineering step is to build the immutable source corpus / adjudication registry,
then promote only source-proven CRT rules into Strategy Identity.
