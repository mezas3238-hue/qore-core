# QORE Risk — FundedNext 2K → 5K Capitalization Mission

## Status

Owner-approved mission contract. Implementation candidate on the exact LIVE lineage that
currently governs the FundedNext Stellar Instant account.

This mission does **not** create trading authority, signals, trades, entries, exits, stop changes,
or strategy changes. Trader methodology remains frozen. CIBO remains the structural opportunity
layer. QORE Risk remains the final capital authority.

## Mission

```text
MISSION_ID = FUNDEDNEXT_2K_TO_5K_CAPITALIZATION
START_BALANCE = 2,000 USD
TARGET_ACCOUNT_SIZE = 5,000 USD
PURPOSE = accumulate enough eligible reward cash to purchase the next Stellar Instant 5K account
POST_WITHDRAWAL_RESERVE = 3% of starting balance = 60 USD
FORCE_TRADES = FALSE
CHASE_LOSSES = FALSE
MARTINGALE = FALSE
ALTER_TRADER_METHODOLOGY = FALSE
```

## Certified economics

The purchase price is not hard-coded into Risk. The provider refresh reads the official FundedNext
Stellar Instant pricing article and extracts the current 5K purchase price into the certified policy
facts.

The reward share is consumed from the certified Stellar Instant policy.

Current verified values at implementation time:

```text
5K purchase price = 149.99 USD
Tier 1–2 reward split = 70%
post-withdrawal reserve = 60.00 USD
```

Deterministic mission economics:

```text
gross_reward_required = CEIL_CENTS(purchase_cash_required / reward_split)
                      = CEIL_CENTS(149.99 / 0.70)
                      = 214.28

minimum_trading_profit_target = gross_reward_required + reserve
                              = 274.28

BANK balance threshold = 2,000 + 214.28
                       = 2,214.28

mission balance target = 2,000 + 274.28
                       = 2,274.28
```

If provider price/reward economics change and are recertified, Risk recomputes the mission using the
new certified economics. Old target latches are not reused across an economic-contract fingerprint
change.

## Cognitive states

```text
CAPITALIZE
BANK
DEFEND
TARGET_REACHED
PAYOUT_READY
MISSION_COMPLETE
```

### CAPITALIZE

Default state while the purchase amount has not yet been economically funded. Existing trader/CIBO
opportunities may reach Account-Wide Risk normally. The mission does not manufacture opportunities.

### BANK

Once closed balance reaches the gross reward threshold, BANK latches for the same certified economic
contract. While BANK is active, the runtime forces the QORE capital posture to the existing BANK
posture. This protects accumulated purchase capital without modifying trader methodology.

### DEFEND

A provider/QORE capital rejection overlays DEFEND. No mission target can override provider limits,
QORE drawdown controls, account-wide heat, stale policy, or any other fail-closed guard.

### TARGET_REACHED

Once closed balance reaches the mission balance target, the mission sets:

```text
new_risk_allowed_by_mission = FALSE
```

The runtime therefore blocks new entries. Position management/closeout logic remains available.

### PAYOUT_READY

Requires separate payout eligibility evidence. Target balance alone does not invent EOD/dashboard
eligibility.

### MISSION_COMPLETE

Requires external confirmation that the purchase cash was actually separated/withdrawn for the next
account. It is never inferred from trading balance alone.

## Persistence

The mission is stored atomically at:

```text
var/fundednext/capitalization-mission.json
```

The state is bound to the account identity fingerprint and carries:

- certified economic-contract fingerprint;
- current closed balance/equity;
- realized profit;
- target remaining;
- purchase cash required;
- gross reward required;
- reserve;
- BANK threshold;
- mission target;
- highest closed balance observed;
- BANK / target / payout latches;
- mission completion flag;
- whether the mission permits new risk.

The mission survives process restart and VPS reboot.

## Runtime authority order

```text
CERTIFIED PROVIDER POLICY
        ↓
QORE CAPITAL PROTECTION
        ↓
ACCOUNT-WIDE RISK
        ↓
CAPITALIZATION MISSION
        ↓
TRADER / CIBO OPPORTUNITY
        ↓
EXECUTION
```

The mission can reduce or stop new risk. It can never create authority that does not already exist.

## Owner principle

```text
CORE PERSIGUE EL OBJETIVO,
PERO NO PERSIGUE OPERACIONES.
```
