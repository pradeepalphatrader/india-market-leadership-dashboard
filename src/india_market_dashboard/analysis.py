from __future__ import annotations

from collections import defaultdict
from .config import Settings
from .indicators import mean, median, percent_return, range_percent, return_volatility_percent, simple_moving_average, true_range_percent
from .models import Classification, PriceBar, StockResult


def _percentile_threshold(values: list[float], top_fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(len(ordered) * (1.0 - top_fraction))))
    return ordered[index]


def analyze_stocks(
    bars: list[PriceBar], classifications: dict[str, Classification], settings: Settings
) -> tuple[list[StockResult], dict]:
    grouped: dict[str, list[PriceBar]] = defaultdict(list)
    for bar in bars:
        if bar.series in settings.allowed_series:
            grouped[bar.symbol].append(bar)

    results: list[StockResult] = []
    rejected: dict[str, list[str]] = {}
    for symbol, history in grouped.items():
        history.sort(key=lambda item: item.trade_date)
        reasons: list[str] = []
        if len(history) < settings.minimum_history_sessions:
            rejected[symbol] = [f"Only {len(history)} sessions; {settings.minimum_history_sessions} required"]
            continue
        classification = classifications.get(symbol)
        if classification is None:
            rejected[symbol] = ["Missing four-level classification"]
            continue

        closes = [bar.close for bar in history]
        highs = [bar.high for bar in history]
        lows = [bar.low for bar in history]
        traded_values = [bar.traded_value for bar in history]
        latest = history[-1]
        median_value = median(traded_values[-20:])
        if latest.close < settings.minimum_price_inr:
            rejected[symbol] = [f"Price below ₹{settings.minimum_price_inr:,.0f}"]
            continue
        if median_value < settings.minimum_median_traded_value_inr:
            rejected[symbol] = ["Insufficient 20-session median traded value"]
            continue

        sma20 = simple_moving_average(closes, 20)
        sma50 = simple_moving_average(closes, 50)
        sma65 = simple_moving_average(closes, 65)
        sma200 = simple_moving_average(closes, 200)
        atr_pct = true_range_percent(highs, lows, closes)
        adr_pct = mean([(high / low - 1.0) * 100 for high, low in zip(highs[-20:], lows[-20:]) if low > 0])
        extension = ((latest.close - sma50) / (sma50 * atr_pct / 100.0)) if sma50 > 0 and atr_pct > 0 else 0.0
        change = percent_return(closes, 1)
        r1w = percent_return(closes, 5)
        r1 = percent_return(closes, 21)
        r3 = percent_return(closes, 63)
        r6 = percent_return(closes, 126)
        r12 = percent_return(closes, 252)
        high52, low52 = max(highs[-252:]), min(lows[-252:])
        range52 = high52 - low52
        score = r1 * 0.25 + r3 * 0.35 + r6 * 0.40
        result = StockResult(
            symbol=symbol, company_name=classification.company_name,
            macro_sector=classification.macro_sector, sector=classification.sector,
            industry=classification.industry, basic_industry=classification.basic_industry,
            close=latest.close, daily_change_percent=change,
            return_1_week_percent=r1w, return_1_month_percent=r1, return_3_month_percent=r3,
            return_6_month_percent=r6, return_12_month_percent=r12,
            sma_20=sma20, sma_50=sma50, sma_65=sma65, sma_200=sma200,
            above_sma_20=latest.close > sma20, above_sma_50=latest.close > sma50,
            above_sma_65=latest.close > sma65, above_sma_200=latest.close > sma200,
            atr_percent=atr_pct, adr_percent=adr_pct,
            extension_atr_multiples=extension, range_20_day_percent=range_percent(highs, lows),
            volatility_20_day_percent=return_volatility_percent(closes),
            median_traded_value_inr=median_value, momentum_score=score, reasons=reasons,
            high_52_week=high52, low_52_week=low52,
            position_52_week_percent=((latest.close-low52)/range52*100 if range52 > 0 else 0),
            distance_from_52_week_high_percent=(latest.close/high52-1)*100 if high52 > 0 else 0,
            new_20_day_high=latest.close >= max(closes[-20:]),
            new_20_day_low=latest.close <= min(closes[-20:]),
            new_52_week_high=latest.close >= max(closes[-252:]),
            new_52_week_low=latest.close <= min(closes[-252:]),
        )
        results.append(result)

    momentum_cutoff = _percentile_threshold([item.momentum_score for item in results], settings.momentum_percentile)
    benchmark = {
        "1w": median([item.return_1_week_percent for item in results]),
        "1m": median([item.return_1_month_percent for item in results]),
        "3m": median([item.return_3_month_percent for item in results]),
        "6m": median([item.return_6_month_percent for item in results]),
        "12m": median([item.return_12_month_percent for item in results]),
    }
    for result in results:
        result.relative_strength_score = (
            (result.return_1_month_percent-benchmark["1m"])*0.15
            +(result.return_3_month_percent-benchmark["3m"])*0.25
            +(result.return_6_month_percent-benchmark["6m"])*0.30
            +(result.return_12_month_percent-benchmark["12m"])*0.30
        )
    ranked = sorted(results, key=lambda item: item.relative_strength_score)
    for index, result in enumerate(ranked):
        result.relative_strength_rating = max(1, min(99, round((index+1)/max(len(ranked), 1)*99)))
    for result in results:
        trend_aligned = result.close > result.sma_50 > result.sma_200
        result.momentum_leader = trend_aligned and result.momentum_score >= momentum_cutoff
        result.non_extended_leader = result.momentum_leader and result.extension_atr_multiples <= settings.maximum_extension_atr_multiples
        result.tight_setup = (
            result.non_extended_leader
            and result.range_20_day_percent <= settings.tight_setup_max_20_day_range_percent
            and result.volatility_20_day_percent <= settings.tight_setup_max_20_day_volatility_percent
        )
        result.emerging_leader = result.close > result.sma_20 > result.sma_50 and not result.momentum_leader
        result.weakening_leader = result.momentum_score >= momentum_cutoff and result.close < result.sma_20
        result.breakout_candidate = result.new_20_day_high and result.above_sma_50 and result.relative_strength_rating >= 70
        result.recovery_candidate = result.close > result.sma_20 and result.sma_20 > result.sma_50 and result.relative_strength_rating >= 55 and not result.momentum_leader
        result.contrarian_quality = result.above_sma_200 and result.position_52_week_percent <= 45 and result.daily_change_percent > 0
        result.near_sma_65 = abs(result.close/result.sma_65-1) <= .03 if result.sma_65 else False
        result.near_sma_200 = abs(result.close/result.sma_200-1) <= .03 if result.sma_200 else False
        result.opportunity_type = (
            "Tight Leader" if result.tight_setup else "Non-Extended Leader" if result.non_extended_leader
            else "Momentum Leader" if result.momentum_leader else "Breakout" if result.breakout_candidate
            else "Recovery" if result.recovery_candidate else "Contrarian Quality" if result.contrarian_quality
            else "65 DMA Setup" if result.near_sma_65 else "200 DMA Setup" if result.near_sma_200 else "Monitor"
        )
        if result.momentum_leader:
            result.reasons.append("Top-decile blended 1/3/6-month momentum with price > 50 DMA > 200 DMA")
        if result.non_extended_leader:
            result.reasons.append(f"Extension is {result.extension_atr_multiples:.1f} ATR multiples, inside the configured limit")
        if result.tight_setup:
            result.reasons.append("20-session range and daily volatility meet tight-setup limits")
        if not result.reasons:
            result.reasons.append("Eligible stock; no leadership setup currently qualifies")

    return sorted(results, key=lambda item: item.momentum_score, reverse=True), {
        "input_symbols": len(grouped), "eligible_symbols": len(results), "rejected_symbols": len(rejected),
        "momentum_cutoff": momentum_cutoff, "benchmark_returns_percent": benchmark, "rejections": rejected,
    }
