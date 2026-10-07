# India Market Leadership & Breadth

A transparent, end-of-day NSE research dashboard for market participation, momentum leadership, non-extended leaders, tight setups, and rotation across the official four-level NSE Indices classification.

> Educational research only. This project is not investment advice and does not recommend buying or selling securities.

## What is included

- Current Nifty 500 constituent refresh from NSE Indices.
- Official Macro-Economic Sector → Sector → Industry → Basic Industry mappings used by the Nifty 500 page.
- A zero-paid-API historical-price fallback with explicit source metadata.
- Liquidity/history eligibility checks, 20/50/200-day averages, ATR%, range contraction, volatility, and blended 1/3/6-month momentum.
- Market, sector, industry, and basic-industry breadth.
- Five-year usable historical breadth after a 200-session warm-up, including a current-universe equal-weight market proxy, A/D line, leadership counts, highs/lows, coverage, and macro-sector rotation comparisons.
- Momentum Leaders, Non-Extended Leaders, Tight Setups, Emerging Leaders, and Weakening Leaders.
- Explainable stock qualification reasons, searchable/sortable tables, CSV export, dark/light themes, and responsive layouts.
- A hard release gate: demo, stale, partial, or insufficiently classified data cannot deploy.
- Tests and a scheduled GitHub Pages workflow.

## Quick start

Requires Python 3.10 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python scripts/generate_demo_data.py
python -m india_market_dashboard.cli build \
  --history-dir data/demo \
  --classification-file data/demo/classifications.csv \
  --demo
python -m http.server 8080 --directory site
```

The demo exercises the whole product but deliberately fails the production release gate.

## Production refresh

```bash
python scripts/refresh_production_data.py --output data/input --history-days 2200
python -m india_market_dashboard.cli build \
  --history-dir data/input/history \
  --classification-file data/input/classifications.csv
python -m india_market_dashboard.cli publish --destination build
```

`publish` refuses to stage the site unless every release check passes.

The historical page is explicitly labelled **Current-Universe Reconstructed Breadth**. It applies today's constituent list to historical prices and therefore contains survivorship bias; it is not point-in-time Nifty 500 membership history. Daily snapshots generated from deployment onward preserve the observed universe for progressively stronger future research.

## Tests

```bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py' -v
```

## Data sources

- Universe: [Nifty 500 constituent CSV](https://www.niftyindices.com/IndexConstituent/ind_nifty500list.csv)
- Classification: the public JSONP feeds used by the official Nifty 500 sector-distribution visualization
- Initial price-history fallback: Yahoo Finance public chart endpoint

The generated dashboard always identifies its active sources in `site/data/dashboard.json`. NSE public report paths and formats can change; failures stop deployment instead of silently substituting incomplete results. See [Data Sources](docs/DATA_SOURCES.md).

## GitHub Pages

1. Push the repository to GitHub.
2. In **Settings → Pages**, select **GitHub Actions** as the source.
3. Run **Build validated dashboard and deploy Pages** once, or wait for its weekday schedule.
4. The `deploy` job receives an artifact only after production validation and tests pass.

## Important interpretation note

The engine supports the complete four-level NSE hierarchy. A particular universe displays the classifications represented by its constituent stocks. The current Nifty 500 snapshot covers all 12 macro sectors and the sectors/industries/basic industries represented inside that index; categories containing no Nifty 500 constituent have no breadth observation.

## Project layout

```text
config/                     Versioned scanner and release settings
scripts/                    Demo and production refresh jobs
src/india_market_dashboard Data parsing, indicators, scanners, breadth, validation
site/                       Static responsive dashboard
tests/                      Calculation and release-gate tests
.github/workflows/          CI and validated GitHub Pages deployment
```

Rules and terminology are defined in [Methodology](docs/METHODOLOGY.md). Product scope is frozen in [PROJECT_REQUIREMENTS.md](PROJECT_REQUIREMENTS.md).
