from __future__ import annotations

import math
import statistics
from collections.abc import Sequence


def mean(values: Sequence[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def median(values: Sequence[float]) -> float:
    return statistics.median(values) if values else 0.0


def simple_moving_average(values: Sequence[float], period: int) -> float:
    if len(values) < period:
        return 0.0
    return mean(values[-period:])


def percent_return(values: Sequence[float], sessions: int) -> float:
    if len(values) <= sessions or values[-sessions - 1] <= 0:
        return 0.0
    return (values[-1] / values[-sessions - 1] - 1.0) * 100.0


def true_range_percent(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], period: int = 14) -> float:
    if len(closes) < period + 1 or closes[-1] <= 0:
        return 0.0
    ranges: list[float] = []
    start = len(closes) - period
    for index in range(start, len(closes)):
        previous_close = closes[index - 1]
        ranges.append(max(highs[index] - lows[index], abs(highs[index] - previous_close), abs(lows[index] - previous_close)))
    return mean(ranges) / closes[-1] * 100.0


def range_percent(highs: Sequence[float], lows: Sequence[float], period: int = 20) -> float:
    if len(highs) < period:
        return 0.0
    period_high = max(highs[-period:])
    period_low = min(lows[-period:])
    return ((period_high / period_low) - 1.0) * 100.0 if period_low > 0 else 0.0


def return_volatility_percent(closes: Sequence[float], period: int = 20) -> float:
    if len(closes) < period + 1:
        return 0.0
    returns = [(closes[i] / closes[i - 1] - 1.0) * 100.0 for i in range(len(closes) - period, len(closes)) if closes[i - 1] > 0]
    return statistics.pstdev(returns) if len(returns) > 1 else 0.0


def finite(value: float) -> float:
    return value if math.isfinite(value) else 0.0
