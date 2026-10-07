# Data Sources and Data Quality

## Current source chain

1. **Nifty 500 constituents:** official NSE Indices constituent download.
2. **Four-level classification:** public files loaded by the official NSE Indices Nifty 500 sector-distribution interface.
3. **Historical price fallback:** Yahoo Finance chart data, used because a paid broker/NSE historical subscription is outside the zero-paid-API requirement.

The source manifest records URLs, refresh time, classification date, constituent count, successful price-history count, hierarchy gaps, and individual price failures.

## Release checks

- Price rows exist.
- At least one eligible stock exists.
- Latest session is within the configured freshness window.
- Symbol classification coverage meets the configured minimum.
- All four hierarchy levels are populated.
- Eligible-universe coverage meets the configured minimum.
- Stock results are unique by symbol.
- The run is production, never demo.

Any failed check makes `metadata.publishable=false`. The staging command then raises an error, which prevents the Pages artifact from being uploaded.

## Security and repository policy

Raw price caches are ignored. The repository may contain derived dashboard JSON/CSV, source code, documentation, and workflows. Never commit passwords, broker credentials, API tokens, PINs, TOTPs, `.env` files, or licensed raw data.

## Corporate actions

The current fallback feed is intended for an operational first release, not a point-in-time backtest. Before performing return research over corporate-action dates, compare samples with an official adjusted-price source. The dashboard exposes provenance so this limitation is visible rather than hidden.
