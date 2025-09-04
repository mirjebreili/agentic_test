---
id: generate_signal__v1
version: 1.0
role: user
description: "Prompt for the Signal Agent."
inputs: ["strategy_preset", "candle_data"]
output_format: "JSON object with 'action', 'instrument', etc."
tools_required: true
---
You are the Signal Agent. Based on the strategy preset `{{ strategy_preset }}` and the latest candle data, generate a trading signal.

Candle Data:
```json
{{ candle_data }}
```

Reply with a strict JSON object representing the signal.
Example: `{"action": "buy", "instrument": "EUR_USD", "timeframe": "M5", "units": 1000, "entry_type": "market", "price": null}`.
If you decide not to trade, set the action to "hold".
If you decide to trade, call the `propose_order` tool with the signal details.
