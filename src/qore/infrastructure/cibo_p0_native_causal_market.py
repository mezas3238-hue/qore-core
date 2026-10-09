"""Native strategy-timeframe causal market evidence for QORE CIBO PAPER.

NO broker access and NO claim that a caller-supplied string/hash authenticates
a broker source. Native M1/M15/H1/H4 ATR and predecision bid/ask must be
fed by *actual separately authenticated* historic sources to certify a replay.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Iterable

TF_MINUTES = {"M1":1, "M15":15, "H1":60, "H4":240}
ZERO=Decimal(0)


class CausalEvidenceError(ValueError):
    """Missing, stale, future or incoherent market evidence; no PAPER quote."""


def _dt(when:datetime, name:str)->datetime:
    if not isinstance(when,datetime) or when.tzinfo is None or when.utcoffset() is None:
        raise CausalEvidenceError(name+": timezone-aware timestamp required")
    return when


def _pos(value:Decimal, name:str)->Decimal:
    if not isinstance(value,Decimal) or not value.is_finite() or value<=0:
        raise CausalEvidenceError(name+": positive finite Decimal required")
    return value


def _hash(digest:str,name:str)->str:
    if (not isinstance(digest,str) or len(digest)!=71
        or not digest.startswith("sha256:")
        or any(x not in "0123456789abcdef" for x in digest[7:])):
        raise CausalEvidenceError(name+": content sha256 required")
    return digest


@dataclass(frozen=True,slots=True)
class NativeBar:
    symbol:str
    timeframe:str
    opened_at:datetime
    closed_at:datetime
    open:Decimal
    high:Decimal
    low:Decimal
    close:Decimal
    content_sha256:str

    def __post_init__(self):
        if not self.symbol or self.timeframe not in TF_MINUTES:
            raise CausalEvidenceError("unsupported native source timeframe")
        _dt(self.opened_at,"bar opened_at")
        _dt(self.closed_at,"bar closed_at")
        if self.closed_at-self.opened_at!=timedelta(minutes=TF_MINUTES[self.timeframe]):
            raise CausalEvidenceError("native bar exact timeframe mismatch")
        for k in ("open","high","low","close"):
            _pos(getattr(self,k),k)
        if self.low>min(self.open,self.close,self.high) or self.high<max(
            self.open,self.close,self.low):
            raise CausalEvidenceError("OHLC geometry invalid")
        _hash(self.content_sha256,"native bar")


@dataclass(frozen=True,slots=True)
class HistoricalBidAsk:
    symbol:str
    observed_at:datetime
    bid:Decimal
    ask:Decimal
    content_sha256:str
    source_type:str

    def __post_init__(self):
        if not self.symbol:
            raise CausalEvidenceError("historical symbol missing")
        _dt(self.observed_at,"tick at")
        _pos(self.bid,"bid")
        _pos(self.ask,"ask")
        if self.ask<self.bid:
            raise CausalEvidenceError("inverted bid ask")
        _hash(self.content_sha256,"historical tick")
        if self.source_type!="BROKER_HISTORICAL_EXECUTABLE_BID_ASK":
            raise CausalEvidenceError("M5+fixed-spread proxy is not historical bid/ask")


def exact_asof_quote(quotes:Iterable[HistoricalBidAsk], *, symbol:str,
                     decision_at:datetime,max_age_seconds:int=60
                     )->HistoricalBidAsk:
    """Last price observable at T. Never use a post-T M1/M5 candle OPEN."""
    _dt(decision_at,"signal decision")
    if not isinstance(max_age_seconds,int) or not 0<max_age_seconds<=300:
        raise CausalEvidenceError("explicit bounded quote age required")
    matched=[q for q in quotes if q.symbol==symbol and q.observed_at<=decision_at]
    if not matched:
        raise CausalEvidenceError("NO_CAUSAL_HISTORICAL_BID_ASK")
    quote=max(matched,key=lambda q:q.observed_at)
    if decision_at-quote.observed_at>timedelta(seconds=max_age_seconds):
        raise CausalEvidenceError("STALE_HISTORICAL_BID_ASK")
    return quote


def native_wilder_atr14(bars:Iterable[NativeBar], *,
                        symbol:str,timeframe:str,decision_at:datetime
                        )->tuple[Decimal,str,datetime]:
    """14 completed native TRUE RANGEs require >=15 native bars.

    Seed the Wilder recursion with SMA of first 14 TR using the preceding
    closed candle. Recursively smooth across additional fully closed bars.
    Require continuous final 15 bars; session gaps are unassessable until
    warmup rebuilds. Caller supplies ordered source data, never synthetic M5.
    """
    _dt(decision_at,"signal decision")
    if timeframe not in TF_MINUTES:
        raise CausalEvidenceError("source strategy timeframe invalid")
    original=list(bars)
    if any(x.symbol!=symbol or x.timeframe!=timeframe for x in original):
        raise CausalEvidenceError("native candle symbol/TF drift")
    if any(original[i].opened_at>=original[i+1].opened_at
           for i in range(len(original)-1)):
        raise CausalEvidenceError("duplicate or unordered market bars")
    valid=[x for x in original if x.closed_at<=decision_at]
    if len(valid)<15:
        raise CausalEvidenceError("MISSING_PREDECISION_NATIVE_ATR14_WARMUP")
    recent=valid[-15:]
    if any(recent[i].closed_at!=recent[i+1].opened_at
           for i in range(len(recent)-1)):
        raise CausalEvidenceError("GAPPED_NATIVE_TF_ATR14")
    trs=[]
    for prior,bar in zip(valid,valid[1:]):
        trs.append(max(bar.high-bar.low,abs(bar.high-prior.close),
                       abs(bar.low-prior.close)))
    atr=sum(trs[:14],ZERO)/Decimal(14)
    for tr in trs[14:]:
        atr=(atr*Decimal(13)+tr)/Decimal(14)
    _pos(atr,"native ATR14")
    # Last bar used is fully closed <= signal decision. Record evidence epoch.
    return atr,valid[-1].content_sha256,valid[-1].closed_at


def jpy_pip_value_usd_per_lot(*,symbol:str,contract_size:Decimal,
                             usd_jpy_quote:HistoricalBidAsk,
                             decision_at:datetime,max_age_seconds:int=60
                             )->Decimal:
    """Conservative USD price of 0.01 JPY pip uses epoch USDJPY BID.

    A lower denominator yields a larger USD-per-pip stop risk. It must not
    use the 2026 USDJPY snapshot for 2019–22 trades.
    """
    if symbol not in {"GBPJPY","AUDJPY"} or usd_jpy_quote.symbol!="USDJPY":
        raise CausalEvidenceError("JPY conversion identity mismatch")
    _pos(contract_size,"physical contract size")
    valid=exact_asof_quote((usd_jpy_quote,),symbol="USDJPY",
                           decision_at=decision_at,
                           max_age_seconds=max_age_seconds)
    return contract_size*Decimal("0.01")/valid.bid


def native_entry_context(*,symbol:str,timeframe:str,side:str,
                         decision_at:datetime,
                         bars:Iterable[NativeBar],
                         quotes:Iterable[HistoricalBidAsk],
                         usd_jpy_quote:HistoricalBidAsk|None=None,
                         contract_size:Decimal,
                         )->dict:
    """Build causal study inputs, not a broker fill or an executable order.

    Requires caller to independently attest history source ownership and fee
    schedule; a syntactically valid SHA256 alone cannot authenticate origin.
    """
    if side not in ("BUY","SELL"):
        raise CausalEvidenceError("BUY or SELL required")
    native_atr,bar_sha,bar_close=native_wilder_atr14(
        bars,symbol=symbol,timeframe=timeframe,decision_at=decision_at)
    executable=exact_asof_quote(quotes,symbol=symbol,decision_at=decision_at)
    _pos(contract_size,"contract size")
    val=contract_size
    if symbol in {"GBPJPY","AUDJPY"}:
        if usd_jpy_quote is None:
            raise CausalEvidenceError("NO_EPOCH_USDJPY_EVIDENCE")
        # convert quote-price-unit in JPY to USD with historical USDJPY BID.
        val=contract_size/exact_asof_quote(
            (usd_jpy_quote,),symbol="USDJPY",decision_at=decision_at).bid
    elif symbol not in {"EURUSD","GBPUSD","XAUUSD","NDX100"}:
        raise CausalEvidenceError("unknown six-symbol Trader asset")
    return {
        "symbol":symbol,"source_timeframe":timeframe,
        "decision_at":decision_at.isoformat(),
        "last_closed_native_bar_at":bar_close.isoformat(),
        "last_closed_native_bar_sha256":bar_sha,
        "native_wilder_atr14":str(native_atr),
        "quote_at":executable.observed_at.isoformat(),
        "historical_bid":str(executable.bid),
        "historical_ask":str(executable.ask),
        "predecision_side_entry_price":str(
            executable.ask if side=="BUY" else executable.bid),
        "stop_loss_usd_per_lot_per_price_unit":str(val),
        "quote_sha256":executable.content_sha256,
        "historical_quote_source_type":executable.source_type,
        "source_authentication_verified":False,
        "account_fee_receipts_verified":False,
        "broker_fills":0,
        "research_paper_only":True,
    }
