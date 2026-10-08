# India Market Intelligence — Product Requirements

## Outcome

Build one validated, end-to-end NSE end-of-day research dashboard and publish it as a static GitHub Pages site. The public site must never present demo, stale, partial, or failed-pipeline data as current market data.

## Scope

- Initial liquid universe: Nifty 500; architecture must also accept all eligible NSE equities.
- Four-level NSE classification: Macro-Economic Sector → Sector → Industry → Basic Industry.
- Market breadth: advances/declines, new highs/lows, and percent above 20/50/200-day moving averages.
- Market command centre: clickable breadth counts, 52-week range context, market story, and exact underlying stock lists.
- Approximately five usable years of current-universe reconstructed breadth after a 200-session warm-up, with explicit coverage, survivorship-bias disclosure, market-proxy comparison, leadership history, and macro-sector rotation charts.
- Scanners: Momentum, Non-Extended, Tight, Emerging, Weakening, Breakout, Recovery, Contrarian Quality, 65 DMA, and 200 DMA setups.
- Preserve the original 13 VPK scanner intents as a separate India-adapted workspace: Fundamental Growth, Post-Earnings Continuation, two Strongest Stock groups, Daily Tightness, and eight size/timeframe momentum scans. ₹ market-cap equivalents use a versioned reference rate; all exact rules and zero-result states remain visible.
- Ticker 360: price; 1W/1M/3M/6M/12M performance; 20/50/65/200 DMA; ATR/ADR; 52-week range; 1–99 relative-strength rank versus the eligible Nifty 500 proxy; full NSE hierarchy.
- Universal search across every eligible stock, including stocks outside the selected scanner.
- Inline TradingView chart with weekly default, daily toggle, chart-type controls, and no forced external tab.
- User-owned browser storage for watchlists and dated notes; TradingView-format copy (`NSE:SYMBOL`).
- Market X-Ray grid across macro sectors, with breadth, trend, RS, volume, new highs, and 52-week location.
- Equal-weight group analytics with optional market-cap/index comparison fields.
- Explainable qualification/rejection reasons and versioned methodology.
- Responsive dark/light website with search, filters, sorting, date selection, drill-down, and CSV export.
- Data-health page, automated tests, daily GitHub Actions run, validation gate, and GitHub Pages deployment.
- Automated weekday refresh attempts at 6:30 PM, 8:30 PM, and 10:30 PM IST; later runs are completeness retries.

## Information hierarchy

The site must support a low-noise workflow: Market Health → Sector X-Ray → Opportunity Radar → complete scanner results → Ticker 360. A top-focus list may rank 10/20 names, but it must never hide or discard the complete result set.

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
