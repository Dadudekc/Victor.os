# DreamOS Metrics System

The DreamOS Metrics System provides comprehensive monitoring and analysis capabilities for agent performance and system health.

## Features

- Response time tracking
- Success rate monitoring
- Resource utilization metrics
- Visualization and reporting
- Decorator-based integration

## Installation

1. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

```python
from dreamos.metrics import MetricsManager

# Initialize metrics manager
metrics = MetricsManager()

# Record metrics
metrics.start_action("agent-1", "process_task")
# ... perform task ...
metrics.end_action("agent-1", "process_task", success=True)

# Record resource utilization
metrics.record_resource("agent-1", "cpu", 0.75)
metrics.record_resource("agent-1", "memory", 0.5)

# Generate report
metrics.generate_report()
```

### Using the Decorator

```python
from dreamos.metrics import MetricsManager, MetricsDecorator

metrics = MetricsManager()
track_metrics = MetricsDecorator(metrics)

@track_metrics
def process_task(agent_id: str, task_data: dict):
    # Task implementation
    pass
```

### Visualization

```python
from datetime import timedelta

# Plot response times for last hour
metrics.plot_response_times(
    agent_id="agent-1",
    time_window=timedelta(hours=1)
)

# Plot success rates
metrics.plot_success_rates(
    agent_id="agent-1",
    time_window=timedelta(hours=1)
)

# Plot resource utilization
metrics.plot_resource_utilization(
    agent_id="agent-1",
    resource_type="cpu",
    time_window=timedelta(hours=1)
)
```

## Components

### AgentMetrics

Core metrics storage and calculation:
- Response time tracking
- Success rate monitoring
- Resource utilization metrics
- Metrics persistence

### MetricsCollector

Metrics collection utilities:
- Action timing
- Success/failure tracking
- Resource monitoring

### MetricsVisualizer

Visualization and reporting:
- Response time plots
- Success rate trends
- Resource utilization graphs
- HTML report generation

### MetricsManager

High-level integration:
- Unified metrics interface
- Automatic persistence
- Visualization integration
- Decorator support

### MetricsDecorator

Easy integration with existing code:
- Automatic timing
- Success/failure tracking
- Minimal code changes

## Best Practices

1. **Consistent Agent IDs**
   - Use consistent agent identifiers
   - Follow naming conventions

2. **Resource Monitoring**
   - Monitor key resources (CPU, memory, etc.)
   - Set appropriate thresholds

3. **Error Handling**
   - Always use try/except blocks
   - Record failures accurately

4. **Report Generation**
   - Generate reports regularly
   - Archive historical data

5. **Visualization**
   - Use appropriate time windows
   - Focus on relevant metrics

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 