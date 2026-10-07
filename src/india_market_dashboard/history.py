from __future__ import annotations

from collections import defaultdict
from statistics import mean

from .config import Settings
from .indicators import (
    median,
    range_percent,
    return_volatility_percent,
)
from .models import Classification, PriceBar


def _percentile_threshold(values: list[float], top_fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(len(ordered) * (1.0 - top_fraction))))
    return ordered[index]


def _reliability(coverage: float) -> str:
    if coverage >= 90:
        return "Reliable"
    if coverage >= 80:
        return "Caution"
    return "Low coverage"


def build_historical_breadth(
    bars: list[PriceBar],
    classifications: dict[str, Classification],
    settings: Settings,
    expected_universe: int = 0,
) -> dict:
    """Reconstruct daily breadth using the current constituent universe.

    This is intentionally not described as point-in-time index history. Historical
    index membership and delisted securities are not available in the input data.
    """
    grouped: dict[str, list[PriceBar]] = defaultdict(list)
    for bar in bars:
        if bar.series in settings.allowed_series and bar.symbol in classifications:
            grouped[bar.symbol].append(bar)
    for history in grouped.values():
        history.sort(key=lambda item: item.trade_date)

    sessions = sorted({bar.trade_date for history in grouped.values() for bar in history})
    warmup = settings.minimum_history_sessions
    if len(sessions) < warmup:
        return {
            "method": "current_universe_reconstructed",
            "label": "Current-Universe Reconstructed Breadth",
            "warmup_sessions": warmup,
            "series": [],
            "macro_sectors": [],
        }

    expected = expected_universe or len(classifications)
    snapshots_by_date: dict[object, list[dict]] = defaultdict(list)

    # Precompute every stock/date observation once. This keeps a multi-year
    # refresh linear in the number of price rows rather than repeatedly slicing
    # each stock's complete history for every market session.
    for symbol, history in grouped.items():
        closes = [bar.close for bar in history]
        highs = [bar.high for bar in history]
        lows = [bar.low for bar in history]
        traded_values = [bar.traded_value for bar in history]
        prefix = [0.0]
        for close in closes:
            prefix.append(prefix[-1] + close)
        true_ranges = [0.0]
        for index in range(1, len(history)):
            true_ranges.append(max(
                highs[index] - lows[index],
                abs(highs[index] - closes[index - 1]),
                abs(lows[index] - closes[index - 1]),
            ))

        for index in range(warmup - 1, len(history)):
            latest = history[index]
            if latest.close < settings.minimum_price_inr:
                continue
            if median(traded_values[index - 19:index + 1]) < settings.minimum_median_traded_value_inr:
                continue
            sma20 = (prefix[index + 1] - prefix[index - 19]) / 20
            sma50 = (prefix[index + 1] - prefix[index - 49]) / 50
            sma200 = (prefix[index + 1] - prefix[index - 199]) / 200
            atr_pct = mean(true_ranges[index - 13:index + 1]) / latest.close * 100
            extension = ((latest.close - sma50) / (sma50 * atr_pct / 100)) if sma50 > 0 and atr_pct > 0 else 0.0
            day_return = (latest.close / closes[index - 1] - 1) * 100 if closes[index - 1] > 0 else 0.0
            momentum = (
                (latest.close / closes[index - 21] - 1) * 100 * 0.25
                + (latest.close / closes[index - 63] - 1) * 100 * 0.35
                + (latest.close / closes[index - 126] - 1) * 100 * 0.40
            )
            recent_highs = highs[index - 19:index + 1]
            recent_lows = lows[index - 19:index + 1]
            recent_closes = closes[index - 20:index + 1]
            year_closes = closes[max(0, index - 251):index + 1]
            snapshots_by_date[latest.trade_date].append({
                "symbol": symbol,
                "sector": classifications[symbol].macro_sector,
                "day_return": day_return,
                "above20": latest.close > sma20,
                "above50": latest.close > sma50,
                "above200": latest.close > sma200,
                "momentum": momentum,
                "trend_aligned": latest.close > sma50 > sma200,
                "extension": extension,
                "tight": (
                    range_percent(recent_highs, recent_lows) <= settings.tight_setup_max_20_day_range_percent
                    and return_volatility_percent(recent_closes) <= settings.tight_setup_max_20_day_volatility_percent
                ),
                "high20": latest.close >= max(recent_closes[-20:]),
                "low20": latest.close <= min(recent_closes[-20:]),
                "high52": latest.close >= max(year_closes),
                "low52": latest.close <= min(year_closes),
            })

    series: list[dict] = []
    sector_series: list[dict] = []
    advance_decline_line = 0
    equal_weight_proxy = 100.0

    for session in sessions[warmup - 1 :]:
        snapshots = snapshots_by_date.get(session, [])
        if not snapshots:
            continue
        cutoff = _percentile_threshold([item["momentum"] for item in snapshots], settings.momentum_percentile)
        for item in snapshots:
            item["leader"] = item["trend_aligned"] and item["momentum"] >= cutoff
            item["non_extended"] = item["leader"] and item["extension"] <= settings.maximum_extension_atr_multiples
            item["tight_setup"] = item["non_extended"] and item["tight"]

        count = len(snapshots)
        advances = sum(item["day_return"] > 0 for item in snapshots)
        declines = sum(item["day_return"] < 0 for item in snapshots)
        above20 = sum(item["above20"] for item in snapshots) / count * 100
        above50 = sum(item["above50"] for item in snapshots) / count * 100
        above200 = sum(item["above200"] for item in snapshots) / count * 100
        breadth_score = above20 * 0.25 + above50 * 0.35 + above200 * 0.40
        advance_decline_line += advances - declines
        equal_weight_proxy *= 1 + mean(item["day_return"] for item in snapshots) / 100
        coverage = count / max(expected, 1) * 100
        series.append({
            "date": session.isoformat(),
            "eligible_stocks": count,
            "coverage_percent": round(coverage, 1),
            "reliability": _reliability(coverage),
            "breadth_score": round(breadth_score, 2),
            "above_sma_20_percent": round(above20, 2),
            "above_sma_50_percent": round(above50, 2),
            "above_sma_200_percent": round(above200, 2),
            "advances": advances,
            "declines": declines,
            "advance_decline_line": advance_decline_line,
            "new_20_day_highs": sum(item["high20"] for item in snapshots),
            "new_20_day_lows": sum(item["low20"] for item in snapshots),
            "new_52_week_highs": sum(item["high52"] for item in snapshots),
            "new_52_week_lows": sum(item["low52"] for item in snapshots),
            "momentum_leaders": sum(item["leader"] for item in snapshots),
            "non_extended_leaders": sum(item["non_extended"] for item in snapshots),
            "tight_setups": sum(item["tight_setup"] for item in snapshots),
            "equal_weight_proxy": round(equal_weight_proxy, 4),
        })

        by_sector: dict[str, list[dict]] = defaultdict(list)
        for item in snapshots:
            by_sector[item["sector"]].append(item)
        sector_series.append({
            "date": session.isoformat(),
            "scores": {
                name: round(
                    sum(item["above20"] for item in items) / len(items) * 25
                    + sum(item["above50"] for item in items) / len(items) * 35
                    + sum(item["above200"] for item in items) / len(items) * 40,
                    2,
                )
                for name, items in sorted(by_sector.items())
            },
        })

    return {
        "method": "current_universe_reconstructed",
        "label": "Current-Universe Reconstructed Breadth",
        "description": "Uses today's constituent universe across available historical prices; it is not point-in-time index membership history.",
        "warmup_sessions": warmup,
        "expected_universe": expected,
        "raw_history_start": sessions[0].isoformat(),
        "raw_history_end": sessions[-1].isoformat(),
        "usable_start": series[0]["date"] if series else None,
        "usable_end": series[-1]["date"] if series else None,
        "series": series,
        "macro_sectors": sector_series,
    }
