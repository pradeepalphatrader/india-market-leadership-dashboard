#!/usr/bin/env python3
from pathlib import Path

from refresh_production_data import refresh_tradingview_snapshot


if __name__ == "__main__":
    output = Path("data/input")
    symbols = {
        row.split(",", 1)[0].strip().upper()
        for row in (output / "classifications.csv").read_text(encoding="utf-8-sig").splitlines()[1:]
        if row.strip()
    }
    count = refresh_tradingview_snapshot(output, symbols)
    print(f"TradingView NSE scanner snapshot: {count} symbols")
