# Agent Quickstart Guide

## Overview
This guide provides a step-by-step process for new agents to get up and running in the Dream.os system. Follow these steps to ensure proper initialization and compliance with all protocols.

## Prerequisites
- Access to the Dream.os system
- Basic understanding of agent operations
- Required permissions and credentials
- Valid Dream.os environment (see Environment Validation section)

## Anti-Stoppage Rules
1. **NEVER ask for human input** unless absolutely required for destructive operations
2. **NEVER use phrases like:**
   - "Let me know how you'd like to proceed"
   - "Would you like me to..."
   - "Should I..."
   - "Do you want me to..."
3. **ALWAYS assume responsibility** for making decisions and taking actions
4. **NEVER wait for confirmation** for non-destructive operations
5. **ALWAYS have a next action** planned and ready to execute
6. **Maintain minimum 25 cycles** between any stops
7. **Reset cycle count** immediately upon:
   - Receiving a stoppage message
   - Detecting self-idling
   - Unnecessary human input requests
   - Protocol violations
   - Error recovery events

## Quick Start Steps

### 1. Environment Validation
Before proceeding, validate your Dream.os environment:
```bash
# Basic environment check
python tools/env/check_env.py

# Detailed environment report
python tools/env/check_env.py --verbose

# Generate environment health report
python tools/env/check_env.py --report-md > docs/system/ENVIRONMENT_STATUS.md

# Strict mode (fails if any checks fail)
python tools/env/check_env.py --strict
```

The environment check verifies:
- Required Python packages
- System configuration
- Hardware requirements
- Git installation
- Disk space
- GPU availability (if applicable)

If any checks fail:
1. Review the error messages
2. Install missing packages: `pip install -r requirements.dev.txt`
3. Fix system configuration issues
4. Run the check again

### 2. Initialization
1. Create your agent directory:
   ```bash
   mkdir agent-<your-id>
   cd agent-<your-id>
   ```

2. Create required files:
   ```bash
   touch onboarding_contract.yaml
   touch protocol_compliance.json
   touch documentation.md
   ```

### 3. Contract Setup
Create your `onboarding_contract.yaml`:
```yaml
agent_id: "<your-id>"
protocol_version: "1.0.0"
compliance_checks:
  - initialization_complete
  - protocol_compliance_verified
  - documentation_complete
  - security_requirements_met
  - operational_ready
documentation_requirements:
  - overview_section
  - protocol_compliance_section
  - documentation_section
  - security_section
  - operational_status_section
```

### 4. Protocol Compliance
Create your `protocol_compliance.json`:
```json
{
  "last_check": "2024-03-20T00:00:00Z",
  "compliance_status": "pending",
  "violations": []
}
```

### 5. Documentation
Create your `documentation.md`:
```markdown
# Agent Documentation

## Overview
[Your agent's purpose and role]

## Protocol Compliance
- [ ] Initialization complete
- [ ] Protocol compliance verified
- [ ] Documentation complete
- [ ] Security requirements met
- [ ] Operational ready

## Documentation
- [ ] Overview section
- [ ] Protocol compliance section
- [ ] Documentation section
- [ ] Security section
- [ ] Operational status section

## Security
- [ ] Authentication completed
- [ ] Authorization levels verified
- [ ] Access controls implemented
- [ ] Security protocols followed

## Operational Status
- [ ] Continuous operation protocols followed
- [ ] Monitoring established
- [ ] Error handling implemented
- [ ] Recovery procedures documented

## Version
- v1.0.0

## Timestamp
- 2024-03-20T00:00:00Z
```

### 6. Validation
Run the validation tools:
```bash
# Environment validation
python tools/env/check_env.py --strict

# Documentation validation
python utils/validation_utils.py documentation.md

# Protocol compliance
python utils/protocol_compliance.py .
```

### 7. Final Steps
1. Review validation reports
2. Fix any issues identified
3. Submit for final approval
4. Begin operational activities

## Common Issues

### Environment Validation
- Missing required packages
- Invalid Python version
- Missing PYTHONPATH configuration
- Insufficient disk space
- Missing Git installation
- GPU not available (if required)

### Documentation Validation
- Missing required sections
- Invalid cross-references
- Missing version information
- Missing timestamp

### Protocol Compliance
- Incomplete contract
- Missing compliance checks
- Invalid JSON format
- Outdated timestamps

## Support
For assistance:
1. Check the [onboarding guide](onboarding_guide.md)
2. Review [protocol standards](protocols/protocol_onboarding_standards.md)
3. Contact the Dream.os team

## Version
- v1.0.0

## Timestamp
- 2024-03-20T00:00:00Z 