#!/usr/bin/env python3
"""Create deterministic local-only data for UI and pipeline verification."""
from __future__ import annotations

import csv
import math
import random
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/demo"

GROUPS = [
    ("Commodities", "Metals & Mining", "Ferrous Metals", "Iron & Steel"),
    ("Consumer Discretionary", "Automobile and Auto Components", "Automobiles", "Passenger Cars & Utility Vehicles"),
    ("Consumer Staples", "Fast Moving Consumer Goods", "Food Products", "Packaged Foods"),
    ("Energy", "Oil, Gas & Consumable Fuels", "Oil", "Refineries & Marketing"),
    ("Financial Services", "Financial Services", "Banks", "Private Sector Bank"),
    ("Healthcare", "Healthcare", "Pharmaceuticals & Biotechnology", "Pharmaceuticals"),
    ("Industrials", "Capital Goods", "Industrial Manufacturing", "Industrial Products"),
    ("Information Technology", "Information Technology", "IT Services", "Computers - Software & Consulting"),
    ("Services", "Services", "Transport Services", "Logistics Solution Provider"),
    ("Telecommunication", "Telecommunication", "Telecom Services", "Telecom - Cellular & Fixed Line Services"),
    ("Utilities", "Power", "Power", "Power Generation"),
    ("Diversified", "Diversified", "Diversified", "Diversified"),
]


def trading_days(count: int) -> list[date]:
    current, days = date.today(), []
    while len(days) < count:
        if current.weekday() < 5:
            days.append(current)
        current -= timedelta(days=1)
    return list(reversed(days))


def main() -> None:
    random.seed(24)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    classifications = []
    symbols = []
    for group_index, hierarchy in enumerate(GROUPS, 1):
        for stock_index in range(1, 4):
            symbol = f"IM{group_index:02d}{stock_index}"
            symbols.append((symbol, group_index, stock_index))
            classifications.append({
                "symbol": symbol, "company_name": f"Illustrative {hierarchy[1]} Company {stock_index}",
                "macro_sector": hierarchy[0], "sector": hierarchy[1], "industry": hierarchy[2],
                "basic_industry": hierarchy[3],
            })
    with (OUTPUT / "classifications.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=classifications[0].keys(), lineterminator="\n");writer.writeheader();writer.writerows(classifications)

    days = trading_days(260)
    rows = []
    for symbol, group_index, stock_index in symbols:
        price = 70 + group_index * 11 + stock_index * 5
        trend = (group_index - 5.5) * 0.0008 + stock_index * 0.00035
        for index, day in enumerate(days):
            cycle = math.sin(index / (9 + stock_index)) * 0.004
            shock = random.gauss(0, 0.008 + stock_index * 0.0015)
            daily_return = trend + cycle + shock
            open_price = price * (1 + random.gauss(0, 0.002))
            close = max(10, price * (1 + daily_return))
            spread = abs(random.gauss(0.011, 0.003))
            high = max(open_price, close) * (1 + spread)
            low = min(open_price, close) * (1 - spread)
            volume = int(350000 + group_index * 50000 + random.random() * 500000)
            rows.append({"date": day.isoformat(), "symbol": symbol, "series": "EQ", "open": f"{open_price:.2f}", "high": f"{high:.2f}", "low": f"{low:.2f}", "close": f"{close:.2f}", "volume": volume, "traded_value": f"{close*volume:.2f}"})
            price = close
    with (OUTPUT / "prices.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys(), lineterminator="\n");writer.writeheader();writer.writerows(rows)
    print(f"Generated {len(rows):,} demo price rows for {len(symbols)} illustrative stocks")


if __name__ == "__main__":
    main()
