from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date


@dataclass(frozen=True)
class PriceBar:
    trade_date: date
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    traded_value: float
    series: str = "EQ"


@dataclass(frozen=True)
class Classification:
    symbol: str
    company_name: str
    macro_sector: str
    sector: str
    industry: str
    basic_industry: str


@dataclass
class StockResult:
    symbol: str
    company_name: str
    macro_sector: str
    sector: str
    industry: str
    basic_industry: str
    close: float
    daily_change_percent: float
    return_1_month_percent: float
    return_3_month_percent: float
    return_6_month_percent: float
    sma_20: float
    sma_50: float
    sma_200: float
    above_sma_20: bool
    above_sma_50: bool
    above_sma_200: bool
    atr_percent: float
    extension_atr_multiples: float
    range_20_day_percent: float
    volatility_20_day_percent: float
    median_traded_value_inr: float
    new_20_day_high: bool = False
    new_20_day_low: bool = False
    new_52_week_high: bool = False
    new_52_week_low: bool = False
    momentum_score: float = 0.0
    momentum_leader: bool = False
    non_extended_leader: bool = False
    tight_setup: bool = False
    emerging_leader: bool = False
    weakening_leader: bool = False
    reasons: list[str] | None = None

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["reasons"] = self.reasons or []
        return payload
