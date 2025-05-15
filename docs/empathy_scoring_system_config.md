# Empathy Scoring System Configuration

## Exponential Score Decay

The empathy scoring system now implements **exponential decay** for the impact of violations over time. This enhancement makes older violations less impactful on current scores than recent ones, allowing agents to demonstrate improvement and recover from past mistakes.

## Configuration Options

The following configuration parameters control the score decay behavior:

```json
{
    "scoring": {
        "score_decay_enabled": true,
        "decay_half_life_days": 7,
        "min_decay_factor": 0.1,
        "trend_window_days": 30
    }
}
```

| Parameter | Description |
|-----------|-------------|
| `score_decay_enabled` | Enables or disables the exponential decay functionality |
| `decay_half_life_days` | Number of days after which a violation's impact is reduced by half |
| `min_decay_factor` | Minimum factor to which impact can decay (prevents complete forgetting) |
| `trend_window_days` | Maximum number of days to consider when calculating trend metrics |

## Score Delta Tracking

The system now tracks score changes over time and logs detailed information about score evolution. This feature enables:

- Monitoring of agent improvement or regression
- Trend analysis over different time periods
- Quantifiable performance metrics

Score delta logs are stored in `runtime/logs/agents/{agent_id}_score_evolution.log` and contain:

- Timestamp of score update
- Previous and current score values
- Score delta (change amount)
- Current status
- Trend analysis (when sufficient history exists)

## Formula

The exponential decay is calculated using the formula:

```
decay_factor = max(min_decay_factor, 0.5 ^ (days_ago / half_life))
```

Where:
- `days_ago` is the number of days since the violation occurred
- `half_life` is the configured `decay_half_life_days`
- `min_decay_factor` prevents the impact from decaying completely to zero

## Example

A violation that occurred 14 days ago with a half-life of 7 days would have a decay factor of:

```
decay_factor = 0.5 ^ (14 / 7) = 0.5 ^ 2 = 0.25
```

This means the violation's impact on the current score is reduced to 25% of its original value.

## Implementation Details

The score decay is implemented in `_calculate_trend_metrics()` in the `EmpathyScorer` class. The method:

1. Groups logs by time periods (daily, weekly, overall)
2. Applies decay factors based on age of each log entry
3. Calculates weighted impact of compliances and violations
4. Normalizes and converts to a trend score

## Benefits

- **Recovery Path**: Agents can recover from past violations as their impact diminishes over time
- **Recency Bias**: Recent behavior is weighted more heavily, encouraging ongoing improvement
- **Historical Context**: Past violations are never completely forgotten, maintaining context
- **Adaptive Learning**: System can adapt to changing patterns in agent behavior
- **Trend Awareness**: Score evolution logs provide insights into agent development

## Integration

This feature integrates with the `AgentIdentity` class, which:

- Maintains a history of score changes
- Logs score deltas to agent-specific log files
- Provides trend analysis across multiple score updates
- Exposes score history through the identity API 