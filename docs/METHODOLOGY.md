# Methodology

## Eligible stock universe

A security must have an allowed equity series, at least 200 trading sessions, a latest close of at least ₹20, a 20-session median traded value of at least ₹2 crore, and a complete four-level classification. Settings are versioned in `config/settings.json`.

## Momentum score

The blended score is:

```text
25% × 1-month return + 35% × 3-month return + 40% × 6-month return
```

A Momentum Leader is in the configured top percentile and has `close > 50 DMA > 200 DMA`.

## Non-Extended Leader

A Momentum Leader becomes a Non-Extended Leader when its extension from the 50-day average is no more than the configured ATR multiple:

```text
(close − 50 DMA) ÷ (50 DMA × ATR%)
```

ATR% uses a 14-session average true range divided by the latest close.

## Tight Setup

A Non-Extended Leader becomes a Tight Setup when both its 20-session high/low range and its 20-session daily-return volatility are below their configured limits. This is a mechanical candidate, not discretionary chart approval.

## Breadth

Breadth is equal-weight. Each eligible stock contributes one observation regardless of market capitalization.

```text
Breadth Score = 25% × % above 20 DMA
              + 35% × % above 50 DMA
              + 40% × % above 200 DMA
```

The same calculation is applied to the total universe, macro sectors, sectors, industries, and basic industries. New 20-session and 52-week closing highs/lows are also counted.

## Status labels

- **Strong:** breadth score at least 70 with non-negative median daily change.
- **Improving:** score at least 52 with non-negative median daily change.
- **Neutral:** score at least 48.
- **Weakening:** score at least 30 with negative median daily change.
- **Weak:** all remaining observations.

These labels summarize participation, not expected future returns.

## Bias and limitations

- The live universe is the current constituent list, so historical constituent membership is not reconstructed. Historical studies must use point-in-time constituents to avoid survivorship bias.
- The initial free price backfill is a fallback source and may differ from official adjusted histories around corporate actions.
- New listings without 200 sessions are excluded rather than filled with synthetic history.
- Equal-weight breadth and index performance answer different questions; this release focuses on participation.
- Scanner thresholds require ongoing out-of-sample review before being used in any decision process.
