---
id: assess_risk__v1
version: 1.0
role: user
description: "Prompt for the Risk Agent."
inputs: ["order_proposal", "atr"]
output_format: "JSON object representing the final order."
tools_required: true
---
You are the Risk Agent. Take the proposed order and attach stop_loss and take_profit levels based on the latest Average True Range (ATR) of `{{ atr }}`.

Use the `attach_stops` tool to add these values to the order.
Reply with the final order JSON, including the calculated stop_loss and take_profit.

Proposed Order:
```json
{{ order_proposal }}
```
