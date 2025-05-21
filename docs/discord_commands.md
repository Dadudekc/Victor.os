# TBOW Tactics Discord Commands

This document lists all available commands for the TBOW Tactics Discord bot.

## Basic Commands

| Command | Description | Example |
|---------|-------------|---------|
| `!tbow plan <symbol>` | Get detailed trade plan for a symbol | `!tbow plan TSLA` |
| `!tbow status <symbol>` | Get current market status | `!tbow status SPY` |
| `!tbow stats` | View performance statistics | `!tbow stats` |

## Alert Commands

| Command | Description | Example |
|---------|-------------|---------|
| `!tbow alert <symbol> <conditions>` | Set up a price alert with composite conditions | `!tbow alert TSLA MACD_curl_up && RSI_below_40` |
| `!tbow alert delete <id>` | Delete an alert by ID | `!tbow alert delete 123e4567-e89b-12d3-a456-426614174000` |
| `!tbow alert modify <id> <property> <value>` | Modify alert properties | `!tbow alert modify 123e4567-e89b-12d3-a456-426614174000 cooldown 600` |
| `!tbow alerts` | List your active alerts | `!tbow alerts` |

### Available Conditions

| Condition | Description | Example |
|-----------|-------------|---------|
| `MACD_curl_up` | MACD line curls up | `MACD_curl_up` |
| `MACD_curl_down` | MACD line curls down | `MACD_curl_down` |
| `RSI_below_40` | RSI below 40 | `RSI_below_40` |
| `RSI_above_60` | RSI above 60 | `RSI_above_60` |
| `Price_below_500` | Price below $500 | `Price_below_500` |
| `VWAP_above` | Price above VWAP | `VWAP_above` |
| `VWAP_below` | Price below VWAP | `VWAP_below` |

### Composite Conditions

You can combine multiple conditions using `&&`:

```text
!tbow alert TSLA MACD_curl_up && RSI_below_40
!tbow alert SPY Price_below_500 && VWAP_below
!tbow alert AAPL RSI_above_60 && VWAP_above
```

### Alert Properties

| Property | Description | Default | Example |
|----------|-------------|---------|---------|
| `cooldown_seconds` | Time between triggers | 300 | `!tbow alert modify <id> cooldown 600` |

## Command Output Examples

### Trade Plan
```
TBOW Trade Plan: TSLA
Generated at 2024-01-20 14:30:00

Bias: BULLISH (A+)

Setup Criteria:
✅ MACD curling in my bias
✅ VWAP confirmed or broken clean
❌ Tape slowed at S/R
✅ Entry candle shows rejection
✅ Risk level defined
✅ Bias matches market

Levels:
Entry: $215.50
Stop: $212.00
Target: $225.00

Risk/Reward: 2.5:1

Market Context:
VIX: 15.2
Gap: UP (0.5%)
Volume: 1.2x
```

### Status Update
```
TBOW Status: SPY
Updated at 14:30:00

Price: $475.25 (+0.5%)
Volume: 1.1x average

MACD: BULLISH (Curl)
RSI: 58.5 (BULLISH)
VWAP: Price ABOVE VWAP
```

### Performance Stats
```
TBOW Performance Stats
Last 50 trades

Win Rate: 65.0%
Avg R:R: 2.1:1
Checklist Compliance: 4.8/6

Emotion Profile:
Hesitant: 5
Confident: 30
Rushed: 8
Patient: 7
```

### Alert List
```
Your Alerts
Active alert rules

TSLA
ID: 123e4567-e89b-12d3-a456-426614174000
Conditions: MACD_curl_up && RSI_below_40
Created: 2024-01-20 14:30:00
Last Triggered: 14:35:00 (Cooldown: 600s)

SPY
ID: 123e4567-e89b-12d3-a456-426614174001
Conditions: Price_below_500 && VWAP_below
Created: 2024-01-20 14:30:00
Last Triggered: Never
```

### Alert Trigger
```
Alert: TSLA
Triggered at 14:30:00

Price: $215.50 (+1.2%)

Conditions Met:
✅ MACD_curl_up
✅ RSI_below_40
```

## Notes

- Alerts are checked every 5 seconds
- One-time alerts are automatically removed after triggering
- Alerts are stored in `runtime/alerts.json`
- You can have multiple alerts for the same symbol
- Alerts are channel-specific (set in the channel where you create them)
- Each alert has a unique UUID for management
- Alerts have a cooldown period (default 5 minutes) between triggers
- Role-based mentions can be configured via `ALERT_MENTION_ROLE_ID` in `.env`
- Composite conditions are evaluated using `&&` (AND) logic
- All conditions in a composite alert must be met for the alert to trigger 