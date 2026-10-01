# CIBO — cTrader DEMO Empirical Slippage Probe V1

Status: **READ-ONLY EMPIRICAL COLLECTION**

This probe attempts to close the provider-execution evidence gap without
creating any broker mutation.

It reads only historical cTrader DEMO deals labelled `QORE:*` and historical
provider ticks immediately preceding each entry execution. BUY fills are
compared with causal ASK quotes and SELL fills with causal BID quotes.

Readiness requires all six CIBO provider symbols and at least eight distinct
orders per symbol. Partial fills may contribute observations but cannot satisfy
the distinct-order threshold by themselves.

The probe reports observed slippage, execution latency, quote age and deal
commission where cTrader exposes it. It does not claim historical 2017
economics, does not read the final holdout, does not fit CIBO policy parameters
and grants no productive authority.

If the account does not contain enough QORE-labelled executions, the artifact
must remain `EMPIRICAL_SLIPPAGE_NOT_READY` with explicit blockers.
