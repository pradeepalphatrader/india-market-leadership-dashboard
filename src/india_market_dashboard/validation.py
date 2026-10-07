from __future__ import annotations

from datetime import date
from .config import Settings
from .models import Classification, PriceBar, StockResult


def validate_release(
    bars: list[PriceBar], classifications: dict[str, Classification], results: list[StockResult],
    diagnostics: dict, settings: Settings, as_of: date, demo: bool = False, expected_universe: int = 0,
) -> dict:
    checks: list[dict] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    latest = max((bar.trade_date for bar in bars), default=date.min)
    input_symbols = diagnostics.get("input_symbols", 0)
    classification_coverage = len({bar.symbol for bar in bars} & set(classifications)) / max(input_symbols, 1)
    universe_coverage = len(results) / max(expected_universe or input_symbols, 1)
    classified = [item for item in classifications.values() if all(
        value and value.lower() not in {"unclassified", "unknown", "n/a"}
        for value in (item.macro_sector, item.sector, item.industry, item.basic_industry)
    )]
    hierarchy_coverage = len(classified) / max(len(classifications), 1)
    check("Price data present", bool(bars), f"{len(bars):,} price rows")
    check("Eligible universe present", bool(results), f"{len(results):,} eligible stocks")
    check("Fresh data", (as_of - latest).days <= settings.freshness_days, f"Latest session: {latest.isoformat()}")
    check("Classification coverage", classification_coverage >= settings.minimum_classification_coverage, f"{classification_coverage:.1%}")
    check("Four-level hierarchy coverage", hierarchy_coverage >= settings.minimum_classification_coverage, f"{hierarchy_coverage:.1%}")
    check("Universe coverage", universe_coverage >= settings.minimum_universe_coverage, f"{universe_coverage:.1%}")
    check("No duplicate stock results", len({item.symbol for item in results}) == len(results), "Symbol-level uniqueness")
    check("Production data", not demo, "Demo datasets can never be published")
    return {
        "publishable": all(item["passed"] for item in checks), "checks": checks,
        "latest_session": latest.isoformat(), "classification_coverage": round(classification_coverage, 4),
        "hierarchy_coverage": round(hierarchy_coverage, 4), "universe_coverage": round(universe_coverage, 4),
    }
