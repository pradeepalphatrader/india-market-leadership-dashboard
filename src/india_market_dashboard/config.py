from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    rules_version: str
    universe_name: str
    allowed_series: tuple[str, ...]
    minimum_history_sessions: int
    minimum_price_inr: float
    minimum_median_traded_value_inr: float
    momentum_percentile: float
    maximum_extension_atr_multiples: float
    tight_setup_max_20_day_range_percent: float
    tight_setup_max_20_day_volatility_percent: float
    freshness_days: int
    minimum_classification_coverage: float
    minimum_universe_coverage: float


def load_settings(path: str | Path) -> Settings:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    raw["allowed_series"] = tuple(raw["allowed_series"])
    return Settings(**raw)
