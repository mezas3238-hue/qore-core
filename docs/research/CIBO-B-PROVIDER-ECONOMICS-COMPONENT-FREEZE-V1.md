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
