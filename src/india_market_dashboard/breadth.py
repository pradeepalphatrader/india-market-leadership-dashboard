from __future__ import annotations

from collections import defaultdict
from statistics import median
from .models import StockResult


def _status(score: float, change: float) -> str:
    if score >= 70 and change >= 0:
        return "Strong"
    if score >= 52 and change >= 0:
        return "Improving"
    if score >= 48:
        return "Neutral"
    if change < 0 and score >= 30:
        return "Weakening"
    return "Weak"


def summarize_group(items: list[StockResult], name: str) -> dict:
    count = len(items)
    if not count:
        return {"name": name, "stock_count": 0, "status": "No data"}
    advances = sum(item.daily_change_percent > 0 for item in items)
    declines = sum(item.daily_change_percent < 0 for item in items)
    above20 = sum(item.above_sma_20 for item in items) / count * 100
    above50 = sum(item.above_sma_50 for item in items) / count * 100
    above200 = sum(item.above_sma_200 for item in items) / count * 100
    breadth_score = above20 * 0.25 + above50 * 0.35 + above200 * 0.40
    day_change = median(item.daily_change_percent for item in items)
    return {
        "name": name, "stock_count": count, "advances": advances, "declines": declines,
        "unchanged": count - advances - declines, "advance_decline_ratio": round(advances / max(declines, 1), 2),
        "above_sma_20_percent": round(above20, 1), "above_sma_50_percent": round(above50, 1),
        "above_sma_200_percent": round(above200, 1), "breadth_score": round(breadth_score, 1),
        "above_sma_65_percent": round(sum(item.above_sma_65 for item in items) / count * 100, 1),
        "median_daily_change_percent": round(day_change, 2),
        "median_1_month_return_percent": round(median(item.return_1_month_percent for item in items), 2),
        "median_3_month_return_percent": round(median(item.return_3_month_percent for item in items), 2),
        "median_6_month_return_percent": round(median(item.return_6_month_percent for item in items), 2),
        "momentum_leaders": sum(item.momentum_leader for item in items),
        "non_extended_leaders": sum(item.non_extended_leader for item in items),
        "tight_setups": sum(item.tight_setup for item in items),
        "breakout_candidates": sum(item.breakout_candidate for item in items),
        "recovery_candidates": sum(item.recovery_candidate for item in items),
        "contrarian_quality": sum(item.contrarian_quality for item in items),
        "near_sma_65": sum(item.near_sma_65 for item in items),
        "near_sma_200": sum(item.near_sma_200 for item in items),
        "new_20_day_highs": sum(item.new_20_day_high for item in items),
        "new_20_day_lows": sum(item.new_20_day_low for item in items),
        "new_52_week_highs": sum(item.new_52_week_high for item in items),
        "new_52_week_lows": sum(item.new_52_week_low for item in items),
        "status": _status(breadth_score, day_change),
    }


def build_breadth(results: list[StockResult]) -> dict:
    dimensions = {
        "macro_sectors": "macro_sector", "sectors": "sector",
        "industries": "industry", "basic_industries": "basic_industry",
    }
    payload = {"market": summarize_group(results, "Eligible Stock Universe")}
    for output_name, attribute in dimensions.items():
        grouped: dict[str, list[StockResult]] = defaultdict(list)
        for result in results:
            grouped[getattr(result, attribute)].append(result)
        payload[output_name] = sorted(
            (summarize_group(items, name) for name, items in grouped.items()),
            key=lambda item: item.get("breadth_score", -1), reverse=True,
        )
    return payload
