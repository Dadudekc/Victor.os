# Dream.OS Checkpoint Verification Tool

This module provides tools to verify agent checkpoint implementations against the Checkpoint Protocol defined in [docs/vision/CHECKPOINT_PROTOCOL.md](../../../../docs/vision/CHECKPOINT_PROTOCOL.md).

## Overview

The Checkpoint Verification Tool ensures that agent checkpoint implementations comply with the standardized Checkpoint Protocol, which addresses critical issues with agent drift in long sessions. The tool validates:

1. **File Structure:** Verifies that checkpoint files exist and follow the correct naming convention.
2. **Interval Requirements:** Checks that routine checkpoints are created at the specified 30-minute intervals.
3. **Content Validation:** Ensures checkpoint files contain all required fields and follow the correct schema.
4. **Restoration Capability:** Tests that checkpoint files include all necessary state fields for restoration.

## Installation

The tool is part of the Dream.OS core system and doesn't require separate installation. However, make sure you have the necessary Python dependencies installed.

## Usage

### Command-line Interface

```bash
# Verify a specific agent
python -m dreamos.core.validation.checkpoint.cli verify --agent-id agent-1

# Verify all agents
python -m dreamos.core.validation.checkpoint.cli verify-all

# Generate verification report in a custom location
python -m dreamos.core.validation.checkpoint.cli report --output-dir reports/
```

### Python API

You can also use the tool programmatically:

```python
from dreamos.core.validation.checkpoint import CheckpointVerifier

# Create verifier
verifier = CheckpointVerifier()

# Verify a specific agent
results = verifier.verify_agent("agent-1")

# Verify all agents
all_results = verifier.verify_all_agents()

# Generate report
report_path = verifier.generate_verification_report(all_results)
```

### Setup and Demo Data

To create demo checkpoint files for testing:

```bash
# Create demo checkpoint files with proper intervals
python -m dreamos.core.validation.checkpoint.setup --demo-agent-id demo-agent --count 3 --interval 30
```

## Report Format

The verification tool generates comprehensive reports in Markdown format. Reports include:

1. An overall summary table showing the verification status for each agent
2. Detailed verification results for each agent, including file validation, interval verification, content validation, and restoration testing
3. Recommendations for addressing any issues found

## Integration with Dream.OS

The Checkpoint Verification Tool integrates with the Dream.OS system in several ways:

1. **Automated Verification:** Task agents can run the tool to verify checkpoints.
2. **Compliance Monitoring:** The tool can be integrated into monitoring systems to ensure ongoing compliance.
3. **Documentation Generation:** Reports can be used to document compliance status.

## Security Considerations

- The tool only reads checkpoint files and does not modify them.
- It does not attempt to execute any code within checkpoint files.
- Reports do not include sensitive information, only validation status.

## Extending the Tool

To extend the tool for additional verifications:

1. Add new verification methods to the `CheckpointVerifier` class
2. Update the report generation to include the new verification results
3. Update the CLI to expose the new functionality

## Troubleshooting

Common issues and solutions:

| Issue | Solution |
|-------|----------|
| No checkpoint files found | Ensure the agent is implementing the CheckpointManager correctly and creating checkpoints in the right location |
| Interval verification failure | Check that the agent is creating routine checkpoints at 30-minute intervals |
| Content validation failure | Ensure checkpoint files follow the schema defined in the Checkpoint Protocol |
| Restoration test failure | Make sure all required state fields are included in the checkpoint |

## License

This tool is part of Dream.OS and is subject to the same license terms. 