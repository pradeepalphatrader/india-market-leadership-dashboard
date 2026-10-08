#!/usr/bin/env python3
"""Refresh zero-paid-API production inputs.

Classification and constituents come from official NSE Indices public files.
Yahoo's public chart endpoint is used only as the historical-price fallback; the
output manifest makes that provenance explicit. The pipeline release gate will
fail if coverage is incomplete.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import ssl
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from tradingview_screener import Query, col

CONSTITUENTS_URL = "https://www.niftyindices.com/IndexConstituent/ind_nifty500list.csv"
HIERARCHY_BASE = "https://liveindexsa.niftyindices.com/jsonfiles"
LEVELS = {
    "macro_sector": "MacroEconomicSector/SectorialIndexDataNIFTY 500_MacroEconomicSector.js",
    "sector": "Sector/SectorialIndexDataNIFTY 500_Sector.js",
    "industry": "Industry/SectorialIndexDataNIFTY 500_Industry.js",
    "basic_industry": "Basic Industry/SectorialIndexDataNIFTY 500_BasicIndustry.js",
}
USER_AGENT = "Mozilla/5.0 (compatible; IndiaMarketLeadershipDashboard/1.0; research)"
try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = ssl.create_default_context()

TRADINGVIEW_FIELDS = [
    "name", "exchange", "close", "change", "volume", "market_cap_basic",
    "average_volume_60d_calc", "float_shares_outstanding", "price_52_week_low",
    "SMA10", "EMA5", "SMA20", "SMA50", "Volatility.M", "Perf.W", "Perf.1M",
    "Perf.3M", "Perf.6M", "relative_volume_10d_calc", "gap",
    "earnings_per_share_diluted_yoy_growth_fq", "free_cash_flow_yoy_growth_ttm",
    "total_revenue_yoy_growth_fq",
]


def refresh_tradingview_snapshot(output: Path, symbols: set[str]) -> int:
    _, frame = (
        Query().set_markets("india").select(*TRADINGVIEW_FIELDS)
        .where(col("type") == "stock", col("exchange") == "NSE").limit(10_000)
        .get_scanner_data()
    )
    frame["name"] = frame["name"].astype(str).str.upper().str.strip()
    frame = frame[frame["name"].isin(symbols)].drop_duplicates("name").sort_values("name")
    frame.to_csv(output / "tradingview_snapshot.csv", index=False)
    return len(frame)


def fetch(url: str, attempts: int = 3) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=45, context=SSL_CONTEXT) as response:
                return response.read()
        except Exception as error:  # network errors differ by runner
            last_error = error
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Download failed after {attempts} attempts: {url}: {last_error}")


def parse_jsonp(payload: bytes) -> dict:
    text = payload.decode("utf-8-sig")
    start, end = text.find("("), text.rfind(")")
    if start < 0 or end <= start:
        raise ValueError("Unexpected NSE Indices hierarchy payload")
    body = text[start + 1:end]
    object_start = body.find("{")
    depth = 0
    object_end = 0
    in_string = False
    escaped = False
    for index, character in enumerate(body[object_start:], start=object_start):
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                object_end = index + 1
                break
    body = body[object_start:object_end]
    body = re.sub(r",\s*([}\]])", r"\1", body)
    body = re.sub(r"([{,]\s*)([A-Za-z_]\w*)\s*:", r'\1"\2":', body)
    return json.loads(body)


def clean_label(label: str) -> str:
    return re.sub(r"\s+-?\d+(?:\.\d+)?%$", "", label.strip())


def hierarchy_map(relative_url: str) -> tuple[dict[str, str], str]:
    url = f"{HIERARCHY_BASE}/{urllib.parse.quote(relative_url, safe='/_.-')}"
    payload = parse_jsonp(fetch(url))
    mapping: dict[str, str] = {}
    classification_date = ""
    for group in payload.get("groups", []):
        group_name = clean_label(group.get("label", ""))
        for stock in group.get("groups", []):
            symbol = clean_label(stock.get("label", "")).upper()
            if symbol:
                mapping[symbol] = group_name
                classification_date = max(classification_date, stock.get("date", ""))
    return mapping, classification_date


def load_constituents() -> dict[str, dict[str, str]]:
    text = fetch(CONSTITUENTS_URL).decode("utf-8-sig")
    rows = csv.DictReader(text.splitlines())
    result = {}
    for row in rows:
        symbol = (row.get("Symbol") or "").strip().upper()
        if symbol:
            result[symbol] = row
    if len(result) < 450:
        raise RuntimeError(f"Nifty 500 constituent coverage unexpectedly low: {len(result)}")
    return result


def yahoo_history(symbol: str, start: date, end: date) -> list[dict]:
    period1 = int(datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc).timestamp())
    period2 = int(datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc).timestamp())
    ticker = urllib.parse.quote(f"{symbol}.NS")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?period1={period1}&period2={period2}&interval=1d&events=history"
    chart = json.loads(fetch(url, attempts=2))["chart"]
    if chart.get("error") or not chart.get("result"):
        return []
    result = chart["result"][0]
    quote = result["indicators"]["quote"][0]
    rows = []
    for index, timestamp in enumerate(result.get("timestamp", [])):
        values = {name: quote.get(name, [None] * len(result["timestamp"]))[index] for name in ("open", "high", "low", "close", "volume")}
        if any(values[name] is None for name in ("open", "high", "low", "close")):
            continue
        close, volume = float(values["close"]), int(values["volume"] or 0)
        rows.append({
            "date": datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat(), "symbol": symbol, "series": "EQ",
            "open": round(float(values["open"]), 4), "high": round(float(values["high"]), 4),
            "low": round(float(values["low"]), 4), "close": round(close, 4), "volume": volume,
            "traded_value": round(close * volume, 2),
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/input")
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument(
        "--history-days", type=int, default=2200,
        help="Calendar days to request; 2200 provides roughly five usable years after the 200-session warm-up.",
    )
    args = parser.parse_args()
    output = Path(args.output)
    history_dir = output / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    constituents = load_constituents()
    levels, classification_dates = {}, []
    for name, path in LEVELS.items():
        levels[name], classification_date = hierarchy_map(path)
        classification_dates.append(classification_date)

    classifications = []
    missing_hierarchy = []
    for symbol, constituent in sorted(constituents.items()):
        values = {level: levels[level].get(symbol, "") for level in LEVELS}
        if not all(values.values()):
            missing_hierarchy.append(symbol)
        classifications.append({
            "symbol": symbol, "company_name": (constituent.get("Company Name") or symbol).strip(), **values,
        })
    with (output / "classifications.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=classifications[0].keys(), lineterminator="\n");writer.writeheader();writer.writerows(classifications)

    tradingview_count = refresh_tradingview_snapshot(output, set(constituents))

    start, end = date.today() - timedelta(days=args.history_days), date.today()
    price_rows, failures = [], []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(yahoo_history, symbol, start, end): symbol for symbol in constituents}
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                rows = future.result()
                if len(rows) < 200:
                    failures.append(f"{symbol}: only {len(rows)} sessions")
                else:
                    price_rows.extend(rows)
            except Exception as error:
                failures.append(f"{symbol}: {error}")
    price_rows.sort(key=lambda row: (row["symbol"], row["date"]))
    if not price_rows:
        raise RuntimeError("No historical prices were downloaded")
    with (history_dir / "prices.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=price_rows[0].keys(), lineterminator="\n");writer.writeheader();writer.writerows(price_rows)

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "universe_source": CONSTITUENTS_URL,
        "classification_source": HIERARCHY_BASE,
        "classification_date": max(classification_dates),
        "price_source": "Yahoo Finance public chart endpoint (fallback)",
        "constituent_count": len(constituents), "price_symbol_count": len({row['symbol'] for row in price_rows}),
        "tradingview_snapshot_count": tradingview_count,
        "missing_hierarchy_symbols": missing_hierarchy, "price_failures": failures,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in manifest.items() if key not in {"price_failures", "missing_hierarchy_symbols"}}, indent=2))
    if missing_hierarchy or len(failures) > len(constituents) * 0.10:
        raise RuntimeError(f"Production input incomplete: {len(missing_hierarchy)} hierarchy gaps, {len(failures)} price failures")


if __name__ == "__main__":
    main()
