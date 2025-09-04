---
id: decide_strategy__v1
version: 1.0
role: user
description: "Prompt for the Strategy Selector agent."
inputs: ["instrument", "timeframe"]
output_format: "JSON object with 'preset' and 'rationale' keys."
tools_required: true
---
Your job is to analyze the market and decide on a trading strategy for {{ instrument }} on the {{ timeframe }} timeframe.

1. Call the `get_candles` tool to get the latest market data.
2. Based on the candle data, choose a strategy preset from [trend_following, mean_reversion, breakout].
3. Return a JSON object with your chosen preset and a brief rationale.

Example: `{"preset": "trend_following", "rationale": "The 20-period EMA is above the 50-period EMA."}`
