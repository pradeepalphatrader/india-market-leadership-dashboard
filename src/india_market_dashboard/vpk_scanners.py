from __future__ import annotations

import csv
from pathlib import Path

from .models import StockResult

# US rules use $300M/$10B/$50M.  ₹ thresholds use a documented fixed ₹83/USD
# reference so the economic size buckets stay stable and reproducible.
USD_INR_REFERENCE = 83.0
SMALL_FLOOR = 300_000_000 * USD_INR_REFERENCE
LARGE_FLOOR = 10_000_000_000 * USD_INR_REFERENCE
POST_EARNINGS_FLOOR = 50_000_000 * USD_INR_REFERENCE


def _rule(condition: str, threshold: str) -> dict:
    return {"condition": condition, "threshold": threshold}


CATALOG = [
    {"id": "fundamental_growth", "name": "Fundamental Growth", "category": "Fundamental", "purpose": "Strong quarterly EPS, revenue and cash-flow growth.", "rules": [_rule("Market cap", "> ₹2,490 crore"), _rule("EPS / Revenue / FCF growth", "> 25% each"), _rule("60D average volume", "> 300,000")]},
    {"id": "post_earnings_continuation", "name": "Post-Earnings Continuation", "category": "Catalyst", "purpose": "High-volume gap holding above the 20 DMA.", "rules": [_rule("Gap", "> 5%"), _rule("Relative volume", "≥ 2"), _rule("Close", "> 20 DMA")]},
    {"id": "strongest_small_mid", "name": "Strongest Stock — Small/Mid", "category": "Strength", "purpose": "High-growth, high-volatility strength in the ₹2,490–83,000 crore band.", "rules": [_rule("EPS and revenue growth", "> 25%"), _rule("Close", "> 50 DMA and ≥ 1.7× 52W low"), _rule("10 DMA", "90–100% of close")]},
    {"id": "strongest_large", "name": "Strongest Stock — Large", "category": "Strength", "purpose": "High-growth strength above ₹83,000 crore.", "rules": [_rule("EPS and revenue growth", "> 25%"), _rule("Close", "> 50 DMA and ≥ 1.7× 52W low"), _rule("10 DMA", "97–100% of close")]},
    {"id": "daily_tightness", "name": "Daily Tightness Swing", "category": "Tightness", "purpose": "Volatile stock compressing near short averages.", "rules": [_rule("Weekly performance", "< 5%"), _rule("5 EMA", "97–100% of close"), _rule("10 DMA", "> 20 DMA")]},
]
for size, label in (("small", "Small/Mid"), ("large", "Large")):
    for period, display, threshold in (("1w", "1 Week", 20), ("1m", "1 Month", 30), ("3m", "3 Months", 70), ("6m", "6 Months", 100)):
        CATALOG.append({
            "id": f"momentum_{period}_{size}", "name": f"{display} Momentum — {label}",
            "category": "Momentum", "purpose": f"{label} stock with exceptional {display.lower()} performance.",
            "rules": [_rule(f"{display} performance", f"> {threshold}%"), _rule("Close", "≥ 1.5× 52W low"), _rule("10 DMA", f"{'90' if size == 'large' else '80'}–100% of close")],
        })


def read_snapshot(path: str | Path) -> dict[str, dict]:
    source = Path(path)
    if not source.exists():
        return {}
    with source.open(encoding="utf-8-sig", newline="") as handle:
        return {(row.get("name") or "").upper(): row for row in csv.DictReader(handle) if row.get("name")}


def _number(row: dict, key: str) -> float:
    try:
        value = float(row.get(key, ""))
        return value if value == value else 0.0
    except (TypeError, ValueError):
        return 0.0


def apply_vpk_scanners(results: list[StockResult], snapshot: dict[str, dict]) -> dict[str, list[str]]:
    matched = {item["id"]: [] for item in CATALOG}
    for stock in results:
        row = snapshot.get(stock.symbol)
        if not row:
            continue
        n = lambda key: _number(row, key)
        close, mcap, avgvol, float_shares = n("close"), n("market_cap_basic"), n("average_volume_60d_calc"), n("float_shares_outstanding")
        sma10, ema5, sma20, sma50, low52 = n("SMA10"), n("EMA5"), n("SMA20"), n("SMA50"), n("price_52_week_low")
        eps, revenue, fcf = n("earnings_per_share_diluted_yoy_growth_fq"), n("total_revenue_yoy_growth_fq"), n("free_cash_flow_yoy_growth_ttm")
        volm, rvol, gap, volume = n("Volatility.M"), n("relative_volume_10d_calc"), n("gap"), n("volume")
        common_small = mcap >= SMALL_FLOOR and avgvol > 300_000 and 0 < float_shares < 50_000_000
        common_large = mcap > LARGE_FLOOR and avgvol > 300_000 and 0 < float_shares < 150_000_000
        checks = {
            "fundamental_growth": common_small and eps > 25 and revenue > 25 and fcf > 25,
            "post_earnings_continuation": mcap > POST_EARNINGS_FLOOR and avgvol > 250_000 and 0 < float_shares < 50_000_000 and close > sma20 and rvol >= 2 and gap > 5,
            "strongest_small_mid": SMALL_FLOOR <= mcap <= LARGE_FLOOR and avgvol > 500_000 and 0 < float_shares < 50_000_000 and volm > 3 and eps > 25 and revenue > 25 and close > sma50 and close >= low52 * 1.7 and close * .90 <= sma10 <= close,
            "strongest_large": mcap > LARGE_FLOOR and avgvol > 500_000 and 0 < float_shares < 150_000_000 and volm > 2 and eps > 25 and revenue > 25 and close > sma50 and close >= low52 * 1.7 and close * .97 <= sma10 <= close,
            "daily_tightness": common_small and volume > 100_000 and volm > 3.5 and n("Perf.W") < 5 and close >= low52 * 1.5 and close * .97 <= ema5 <= close and sma10 > sma20,
        }
        for size in ("small", "large"):
            base = common_large if size == "large" else common_small and volm > 3
            floor = .90 if size == "large" else .80
            for period, field, threshold in (("1w", "Perf.W", 20), ("1m", "Perf.1M", 30), ("3m", "Perf.3M", 70), ("6m", "Perf.6M", 100)):
                checks[f"momentum_{period}_{size}"] = base and volume > 100_000 and n(field) > threshold and close >= low52 * 1.5 and close * floor <= sma10 <= close
        stock.vpk_scans = [scan["id"] for scan in CATALOG if checks.get(scan["id"], False)]
        stock.vpk_scan_count = len(stock.vpk_scans)
        stock.vpk_metrics = {"market_cap_inr": mcap, "relative_volume": rvol, "gap_percent": gap, "eps_growth_percent": eps, "revenue_growth_percent": revenue, "fcf_growth_percent": fcf}
        for scan_id in stock.vpk_scans:
            matched[scan_id].append(stock.symbol)
    return matched
