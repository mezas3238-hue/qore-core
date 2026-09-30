# CIBO Architect B — Provider Economics Component Freeze V1

Status: **CURRENT PROVIDER TERMS FROZEN / PRE-HOLDOUT PROVIDER ECONOMICS NOT READY**

The latest verified cTrader DEMO provider-economics artifact is now the canonical
B-side point-in-time source for current provider terms:

- workflow run: `36727848127`
- artifact id: `11104595302`
- artifact ZIP SHA-256:
  `db65a47bc964c3540a0f7c60ba1e707f8d79b5b6927299f6e685846afe9f4863`
- provider payload SHA-256:
  `8bef208a155b94902ad7df4f6e84f01343892f3ec57380e74c7137b0d86fadc3`
- observed at: `2026-09-30T14:28:18.024787+00:00`
- broker mutation: false
- holdout outcomes used: false

The component freeze locks the provider-native point-in-time contract/volume,
spread, commission and expected-margin terms.

It deliberately leaves:

- empirical slippage: **NOT FROZEN**;
- execution model: **NOT FROZEN**;
- historical 2017 exact provider economics: **NOT CLAIMED**.

Therefore `pre_holdout_provider_economics_ready=false` and the global
`ACTIVE_PRE_HOLDOUT_FREEZE` remains untouched / inactive. This component freeze
must not be interpreted as permission to open 2017H1 or as productive authority.

## Forward execution calibration path

Architect B now has a deterministic calibration path for the two open execution
components. It consumes only:

- the immutable Architect-B forward economic manifest;
- the durable Phase20 executed-risk book;
- exact pre-decision provider bid/ask;
- the reconciled weighted provider fill price and fill refs;
- decision, fill and risk-reconciliation timestamps.

For a long position, signed entry slippage is measured as
`weighted_fill - provider_ask`. For a short position it is
`provider_bid - weighted_fill`. Positive values are adverse; favorable fills remain
negative and are not clipped except for the separate one-sided adverse metric.

The calibration is not eligible until the manifest itself is scientifically
consumable under the frozen Phase20D minima, all complete manifest rows reconcile
to their exact executed-risk SHA, all six current provider symbols are represented,
and each required symbol has at least the frozen minimum outcomes-per-lineage.

The resulting artifact records p95 adverse slippage, quote age, decision-to-fill
latency and fill-to-risk-reconciliation latency per symbol. It never changes a
policy, sizes a trade, mutates the broker, reads 2017H1 or claims historical terms.

The component freeze may bind this calibration by SHA. Until such a **real**
forward calibration becomes ready, the existing blockers remain:

- `EMPIRICAL_SLIPPAGE_NOT_FROZEN`;
- `EXECUTION_MODEL_NOT_FROZEN`.


## T17 limited-risk evidence

The provider-economics workflow now seals an additional read-only artifact:

`t17-limited-risk-capability.json`

It is derived from the same account fingerprint as the account-capability and
provider-economics probes and partitions the observed QORE symbols into:

- GSL supported;
- GSL unsupported;
- GSL unknown.

The artifact can identify a Limited-Risk/GSL candidate, but it cannot freeze
T17 as ready. Execution economics and fresh OOS utility remain independent
mandatory gates.
