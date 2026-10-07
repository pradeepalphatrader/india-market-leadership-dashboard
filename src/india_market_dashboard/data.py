from __future__ import annotations

import csv
import io
import urllib.request
import zipfile
from datetime import date, datetime
from pathlib import Path

from .models import Classification, PriceBar


ALIASES = {
    "date": ("date", "trade_date", "trad_dt", "TradDt"),
    "symbol": ("symbol", "ticker", "TckrSymb", "SYMBOL"),
    "open": ("open", "OpnPric", "OPEN"),
    "high": ("high", "HghPric", "HIGH"),
    "low": ("low", "LwPric", "LOW"),
    "close": ("close", "ClsPric", "CLOSE"),
    "volume": ("volume", "TtlTradgVol", "TOTTRDQTY"),
    "value": ("traded_value", "TtlTrfVal", "TOTTRDVAL"),
    "series": ("series", "SctySrs", "SERIES"),
}


def _first(row: dict[str, str], logical: str, default: str = "") -> str:
    for name in ALIASES[logical]:
        if name in row and row[name] not in (None, ""):
            return str(row[name]).strip()
    return default


def _parse_date(value: str) -> date:
    value = value.strip()
    for pattern in ("%Y-%m-%d", "%d-%m-%Y", "%Y%m%d", "%d-%b-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            continue
    raise ValueError(f"Unsupported trade date: {value}")


def read_price_csv(path: str | Path) -> list[PriceBar]:
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    bars: list[PriceBar] = []
    for row in rows:
        symbol = _first(row, "symbol").upper()
        close = float(_first(row, "close", "0"))
        if not symbol or close <= 0:
            continue
        volume = int(float(_first(row, "volume", "0")))
        value = float(_first(row, "value", "0")) or close * volume
        bars.append(PriceBar(
            trade_date=_parse_date(_first(row, "date")), symbol=symbol,
            open=float(_first(row, "open", str(close))), high=float(_first(row, "high", str(close))),
            low=float(_first(row, "low", str(close))), close=close, volume=volume,
            traded_value=value, series=_first(row, "series", "EQ").upper(),
        ))
    return bars


def read_history(directory: str | Path) -> list[PriceBar]:
    paths = sorted(Path(directory).glob("*.csv"))
    if not paths:
        raise FileNotFoundError(f"No CSV price files found in {directory}")
    bars: list[PriceBar] = []
    for path in paths:
        bars.extend(read_price_csv(path))
    unique = {(bar.trade_date, bar.symbol, bar.series): bar for bar in bars}
    return sorted(unique.values(), key=lambda bar: (bar.symbol, bar.trade_date))


def read_classifications(path: str | Path) -> dict[str, Classification]:
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        rows = csv.DictReader(handle)
        required = {"symbol", "company_name", "macro_sector", "sector", "industry", "basic_industry"}
        if not required.issubset(rows.fieldnames or []):
            raise ValueError(f"Classification file missing columns: {sorted(required - set(rows.fieldnames or []))}")
        result = {}
        for row in rows:
            symbol = row["symbol"].strip().upper()
            if symbol:
                result[symbol] = Classification(**{key: row[key].strip() for key in required})
        return result


def download_nse_udiff(trade_date: date, destination: str | Path, url_template: str) -> Path:
    """Download and extract an NSE UDiFF daily bhavcopy.

    The URL is configuration rather than hard-coded because NSE report locations can change.
    Use {yyyymmdd} and {ddmmyyyy} placeholders in the template.
    """
    target_dir = Path(destination)
    target_dir.mkdir(parents=True, exist_ok=True)
    url = url_template.format(yyyymmdd=trade_date.strftime("%Y%m%d"), ddmmyyyy=trade_date.strftime("%d%m%Y"))
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/zip,text/csv,*/*"})
    with urllib.request.urlopen(request, timeout=45) as response:
        payload = response.read()
    if payload[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
            if len(csv_names) != 1:
                raise ValueError("Expected exactly one CSV in UDiFF archive")
            output = target_dir / Path(csv_names[0]).name
            output.write_bytes(archive.read(csv_names[0]))
            return output
    output = target_dir / f"nse_cm_{trade_date.isoformat()}.csv"
    output.write_bytes(payload)
    return output
