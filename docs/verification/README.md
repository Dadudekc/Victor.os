# Dream.OS Verification Framework

This directory contains the verification framework for Dream.OS, providing standardized approaches to testing and validating system components.

## Overview

The verification framework is designed to ensure the reliability, stability, and correctness of Dream.OS components through systematic testing and validation. The framework focuses on critical operational aspects of the system, including tool reliability, protocol adherence, and module integration.

## Components

### Documentation

- [Implementation Plan](implementation_plan.md): The current implementation plan and status tracking
- [Tool Reliability Framework](tool_reliability_framework.md): Design document for the tool reliability testing framework
- [Protocol Verification Framework](protocol_verification_framework.md): Design document for the protocol verification framework
- [Coordination Request](coordination_request.md): Initial coordination request sent to other agents
- [Coordination Update](coordination_update.md): Latest progress update sent to other agents

### Implementation

- `src/dreamos/testing/tools/reliability.py`: Tool reliability testing implementation
- `src/dreamos/testing/tools/validation.py`: Basic validation utilities
- `src/dreamos/testing/tools/protocol.py`: Protocol verification framework implementation
- `src/dreamos/testing/run_verification.py`: Verification runner script

### Automation

- `.github/workflows/verification.yml`: CI/CD integration for automated verification
- `scripts/verification/daily_verification.bat`: Windows batch script for daily verification
- `scripts/verification/daily_verification.sh`: Unix shell script for daily verification

## Usage

To run the verification suite:

```bash
python -m src.dreamos.testing.run_verification
```

Optional arguments:
- `--base-path PATH`: Specify the base path for testing
- `--output-dir DIR`: Specify the output directory for reports (default: logs/verification)
- `--json`: Output results as JSON
- `--markdown`: Output results as Markdown
- `--html`: Output results as HTML
- `--only {reliability,all}`: Only run specific verification

## Coordination

The verification framework is being developed in coordination with other specialized agents:

- **Agent-2 (Infrastructure)**: Tool reliability diagnostics
- **Agent-3 (Loop Engineer)**: Protocol documentation and verification
- **Agent-4 (Integration)**: Bridge module testing
- **Agent-5 (Task Engineer)**: Task system verification
- **Agent-6 (Feedback)**: Metrics integration and alerting

## Implementation Status

The current implementation status is tracked in the [Implementation Plan](implementation_plan.md). The following components have been completed:

- ✅ Tool Reliability Framework
- ✅ Verification Runner
- ✅ CI/CD Integration
- ✅ Protocol Verification Framework (Initial)

The following components are in progress:

- 🔄 Metrics Collection Integration
- 🔄 Protocol Verification Framework (Complete)

The following components are planned:

- 📝 Module Validation Framework
- 📝 Task System Verification

## Next Steps

1. Complete Protocol Verification Framework implementation
2. Coordinate with Agent-2 on tool reliability diagnostics
3. Coordinate with Agent-6 on metrics dashboard integration
4. Begin Module Validation Framework implementation 