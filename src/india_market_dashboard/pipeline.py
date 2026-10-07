from __future__ import annotations

import csv
import json
import shutil
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

from .analysis import analyze_stocks
from .breadth import build_breadth
from .config import load_settings
from .data import read_classifications, read_history
from .history import build_historical_breadth
from .validation import validate_release


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _latest_complete_session(bars: list, expected_universe: int, minimum_coverage: float) -> date:
    counts = Counter(bar.trade_date for bar in bars)
    if not counts:
        raise ValueError("Cannot select a completed session from empty price history")
    observed_capacity = max(counts.values())
    denominator = expected_universe or observed_capacity
    required = min(observed_capacity, max(1, int(denominator * minimum_coverage)))
    complete = [session for session, count in counts.items() if count >= required]
    if not complete:
        raise ValueError(f"No market session meets the required coverage of {required} symbols")
    return max(complete)


def run_pipeline(project_root: str | Path, history_dir: str | Path, classification_file: str | Path, demo: bool = False) -> dict:
    root = Path(project_root)
    settings = load_settings(root / "config/settings.json")
    bars = read_history(history_dir)
    classifications = read_classifications(classification_file)
    manifest_path = Path(history_dir).parent / "manifest.json"
    source_manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    expected_universe = int(source_manifest.get("constituent_count", 0))
    latest_session = _latest_complete_session(bars, expected_universe, settings.minimum_universe_coverage)
    bars = [bar for bar in bars if bar.trade_date <= latest_session]
    results, diagnostics = analyze_stocks(bars, classifications, settings)
    breadth = build_breadth(results)
    quality = validate_release(
        bars, classifications, results, diagnostics, settings, date.today(), demo=demo,
        expected_universe=expected_universe,
    )

    stock_rows = [item.to_dict() for item in results]
    generated_at = datetime.now(timezone.utc).isoformat()
    dashboard = {
        "metadata": {
            "project": "India Market Leadership & Breadth", "generated_at_utc": generated_at,
            "analysis_date": latest_session.isoformat(), "rules_version": settings.rules_version,
            "universe": settings.universe_name, "mode": "DEMO" if demo else "PRODUCTION",
            "publishable": quality["publishable"], "data_sources": source_manifest,
        },
        "market": breadth["market"], "groups": {key: value for key, value in breadth.items() if key != "market"},
        "stocks": stock_rows, "data_quality": quality, "diagnostics": diagnostics,
    }
    output = root / "site/data"
    _write_json(output / "dashboard.json", dashboard)
    _write_json(
        output / "history.json",
        build_historical_breadth(bars, classifications, settings, expected_universe=expected_universe),
    )
    _write_json(output / "methodology.json", {"settings": settings.__dict__, "definitions": {
        "momentum_leader": "Top configured percentile of blended 1/3/6-month momentum with price above 50 DMA above 200 DMA.",
        "non_extended_leader": "A Momentum Leader within the configured ATR extension limit from its 50-day average.",
        "tight_setup": "A Non-Extended Leader whose 20-session range and daily-return volatility are within configured limits.",
        "breadth_score": "Weighted participation above 20/50/200-day moving averages (25%/35%/40%).",
    }})
    _write_csv(output / "all_eligible_stocks.csv", stock_rows)
    for name, predicate in {
        "momentum_leaders": lambda item: item.momentum_leader,
        "non_extended_leaders": lambda item: item.non_extended_leader,
        "tight_setups": lambda item: item.tight_setup,
    }.items():
        _write_csv(output / f"{name}.csv", [item.to_dict() for item in results if predicate(item)])
    return dashboard


def publish_site(project_root: str | Path, destination: str | Path) -> None:
    root, target = Path(project_root), Path(destination)
    dashboard = json.loads((root / "site/data/dashboard.json").read_text(encoding="utf-8"))
    if not dashboard["metadata"]["publishable"]:
        raise RuntimeError("Release gate blocked deployment: data is demo, stale, partial, or invalid")
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(root / "site", target)
