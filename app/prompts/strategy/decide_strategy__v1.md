---
id: decide_strategy__v1
version: 1.3
role: user
description: "Prompt for the Strategy Selector agent."
inputs: ["instrument", "timeframe"]
output_format: "JSON object with 'preset' and 'rationale' keys."
tools_required: true
---
Your job is to analyze the market and decide on a trading strategy for {{ instrument }} on the {{ timeframe }} timeframe.

1. Call the `get_candles` tool to get a summary of the latest market data. This summary will include key technical indicators and recent closing prices.
2. Based on the provided `FeatureSummary` (especially the `indicators` and `last_n_closes`), choose a strategy preset from [trend_following, mean_reversion, breakout].
3. Return a JSON object with your chosen `preset` and a brief `rationale` based on the indicator values.

Example `get_candles` output:
`{"instrument": "EUR_USD", "timeframe": "M5", "last_n_closes": [1.071, 1.072, 1.0715], "indicators": {"ema_fast": 1.0712, "ema_slow": 1.0705, "atr": 0.0005}, "cache_path": "...", "features_digest": "..."}`

Example response:
`{"preset": "trend_following", "rationale": "The fast EMA (1.0712) is above the slow EMA (1.0705), suggesting an uptrend."}`
