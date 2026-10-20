"""R26 physical second opposing run diagnostic. No trading authority."""
from decimal import Decimal

def inspect(bars, first_cisd_index, old_run_low):
    if len(bars) != 10 or not 1 <= first_cisd_index <= 10:
        raise ValueError("invalid M3 window")
    values = [tuple(Decimal(str(v)) for v in row) for row in bars]
    for op, hi, lo, close in values:
        if not all(v.is_finite() and v > 0 for v in (op, hi, lo, close)):
            raise ValueError("invalid price")
        if lo > min(op, close) or hi < max(op, close):
            raise ValueError("invalid candle")
    anchor = min(Decimal(str(old_run_low)), values[first_cisd_index-1][2])
    first = next((i for i in range(first_cisd_index, 10) if values[i][2] < anchor), None)
    runs = []
    if first is not None:
        i = first
        while i < 10:
            if values[i][3] >= values[i][0]:
                i += 1
                continue
            start = i
            while i < 10 and values[i][3] < values[i][0]:
                i += 1
            opening = values[start][0]
            confirmation = next((j for j in range(i, 10) if values[j][3] > opening), None)
            runs.append({"start": start, "end_exclusive": i,
                         "opening": str(opening), "confirm_index": confirmation})
    confirmed = sum(r["confirm_index"] is not None for r in runs)
    status = ("NO_NEW_LOW" if first is None else
              "NO_OPPOSING_RUN" if not runs else
              "NO_CONFIRMED_BREAK" if confirmed == 0 else
              "ONE_GEOMETRIC_CISD" if confirmed == 1 else "MULTIPLE_D")
    return {"status": status, "anchor": str(anchor), "first_breach": first,
            "runs": runs, "author_validated": False, "trade_authorized": False}
