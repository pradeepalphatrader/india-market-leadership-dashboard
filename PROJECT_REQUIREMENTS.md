# India Market Leadership & Breadth — Product Requirements

## Outcome

Build one validated, end-to-end NSE end-of-day research dashboard and publish it as a static GitHub Pages site. The public site must never present demo, stale, partial, or failed-pipeline data as current market data.

## Scope

- Initial liquid universe: Nifty 500; architecture must also accept all eligible NSE equities.
- Four-level NSE classification: Macro-Economic Sector → Sector → Industry → Basic Industry.
- Market breadth: advances/declines, new highs/lows, and percent above 20/50/200-day moving averages.
- Approximately five usable years of current-universe reconstructed breadth after a 200-session warm-up, with explicit coverage, survivorship-bias disclosure, market-proxy comparison, leadership history, and macro-sector rotation charts.
- Scanners: Momentum Leaders, Non-Extended Leaders, Tight Setups, Emerging Leaders, and Weakening Leaders.
- Equal-weight group analytics with optional market-cap/index comparison fields.
- Explainable qualification/rejection reasons and versioned methodology.
- Responsive dark/light website with search, filters, sorting, date selection, drill-down, and CSV export.
- Data-health page, automated tests, daily GitHub Actions run, validation gate, and GitHub Pages deployment.

## Data policy

- Prefer official NSE daily reports, security masters, constituent lists, and classifications.
- Paid Dhan data is not required. Secrets, PINs, TOTPs, credentials, and restricted raw data must never be committed.
- A fallback provider may be used only when identified in output metadata.
- Derived JSON/CSV may be committed; raw bulk market files are ignored.

## Release gate

Production deployment is allowed only when schema checks, freshness checks, coverage checks, indicator tests, scanner tests, site tests, and data-quality checks pass. Demo data is local-only and must set `publishable=false`.

The current snapshot must use the latest completed session meeting minimum universe coverage. A newer partial session must never displace a completed session or pass the release gate.

## User-facing terminology

Use meaningful names. Do not expose unexplained abbreviations such as NEL. Display “Non-Extended Leaders” in the interface.
