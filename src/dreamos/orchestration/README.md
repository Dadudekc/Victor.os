# Dream.OS Swarm Controller and Test Suite

## Overview
The swarm controller and test suite provide robust agent coordination, monitoring, and testing capabilities for the Dream.OS system. The implementation includes:

1. Swarm Controller (`swarm_controller.py`)
   - Agent lifecycle management
   - Process monitoring
   - Stats collection
   - Feedback system

2. Swarm Cycle Test (`swarm_cycle_test.py`)
   - Automated testing of agent interactions
   - Cycle monitoring
   - Performance metrics
   - Error detection

3. Test Runner (`run_swarm_test.py`)
   - Automated test execution
   - Result reporting
   - Exit code handling

## Features

### Swarm Controller
- Agent process management (start/stop/status)
- Real-time stats collection
- Comprehensive feedback system
- Error handling and recovery
- Logging and monitoring

### Swarm Cycle Test
- Automated cycle testing
- Agent state monitoring
- Performance metrics collection
- Error detection and reporting
- Test result persistence

## Usage

### Running the Swarm Controller
```bash
python -m dreamos.orchestration.swarm_controller --action [start|stop|status|launch-all] [--agent-id AGENT_ID]
```

### Running the Swarm Test
```bash
python -m dreamos.orchestration.run_swarm_test
```

## Configuration

### Swarm Controller Config
Located at `runtime/config/swarm_config.json`:
```json
{
  "managed_agents": [
    {
      "agent_id": "Agent-1",
      "script_path": "src/dreamos/agents/agent1.py"
    }
  ]
}
```

### Test Configuration
The test suite uses the following paths:
- Logs: `runtime/logs/`
- Test Results: `runtime/test_results/`
- Agent Mailboxes: `runtime/agent_comms/agent_mailboxes/`

## Dependencies
- pyyaml>=6.0.1
- python-dateutil>=2.8.2
- typing-extensions>=4.5.0

## Error Handling
The system implements comprehensive error handling:
1. Process-level error detection
2. Cycle-level error monitoring
3. System-wide error reporting
4. Automatic recovery attempts
5. Detailed error logging

## Monitoring
The system provides multiple monitoring capabilities:
1. Real-time agent status
2. Performance metrics
3. Cycle statistics
4. Error tracking
5. System health monitoring

## Contributing
When contributing to this system:
1. Follow existing patterns
2. Maintain error handling
3. Add comprehensive logging
4. Update documentation
5. Include test coverage

## License
Proprietary - Dream.OS 