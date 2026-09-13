from pathlib import Path

path = Path("src/qore/infrastructure/trader_lab/vt08_challenge_speed_monte_carlo_r3_13.py")
text = path.read_text()
old = """    successful_days = [
        float(item.target_days[TARGET_INDEX_10PCT])
        for item in results
        if item.target_days[TARGET_INDEX_10PCT] is not None
        and item.target_days[TARGET_INDEX_10PCT] <= CHALLENGE_HORIZON_DAYS
        and (
            item.first_breach_day is None
            or item.target_days[TARGET_INDEX_10PCT] <= item.first_breach_day
        )
    ]
"""
new = """    successful_days: list[float] = []
    for item in results:
        achieved_day = item.target_days[TARGET_INDEX_10PCT]
        if achieved_day is None or achieved_day > CHALLENGE_HORIZON_DAYS:
            continue
        if item.first_breach_day is None or achieved_day <= item.first_breach_day:
            successful_days.append(float(achieved_day))
"""
if old not in text:
    raise SystemExit("expected target-day block not found")
path.write_text(text.replace(old, new))
