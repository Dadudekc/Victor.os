# Dream.os Onboarding Documentation

This directory contains all onboarding-related documentation and resources for the Dream.os project. The documentation is organized into the following sections:

## Core Documentation

### Guides
- `onboarding_guide.md` - Main onboarding guide for all agents
- `agent_autonomy_and_continuous_operation.md` - Core principles of agent autonomy
- `onboarding_autonomous_operation.md` - Autonomous operation protocols
- `agent_operational_philosophy.md` - Agent operational philosophy and principles
- `developer_guide.md` - Developer-specific onboarding
- `user_onboarding.md` - User onboarding guide
- `branch_management.md` - Branch management guidelines

### Protocols
- `protocols/protocol_continuous_autonomy.md` - Continuous autonomy protocol
- `protocols/protocol_onboarding_standards.md` - Consolidated onboarding standards and requirements

### Tools and Utilities
The following utility files are available in the `utils/` directory:
- `onboarding_utils.py` - Core onboarding utilities
- `protocol_compliance.py` - Protocol compliance checking utilities
- `validation_utils.py` - Documentation validation utilities

## Directory Structure

```
onboarding/
├── README.md
├── onboarding_guide.md
├── agent_autonomy_and_continuous_operation.md
├── onboarding_autonomous_operation.md
├── agent_operational_philosophy.md
├── developer_guide.md
├── user_onboarding.md
├── branch_management.md
├── protocols/
│   ├── protocol_continuous_autonomy.md
│   └── protocol_onboarding_standards.md
└── utils/
    ├── onboarding_utils.py
    ├── protocol_compliance.py
    └── validation_utils.py
```

## Contributing

When adding or updating onboarding documentation:
1. Place new content in the appropriate section based on its type (guide, protocol, or utility)
2. Update this README if adding new categories or files
3. Ensure all cross-references are updated
4. Follow the established naming conventions
5. Include clear version information and effective dates

## Maintenance

This documentation structure is maintained by the Dream.os team. For questions or suggestions about the onboarding organization, please contact the team.

## Migration Status

The onboarding documentation has been consolidated into this directory structure. All previously scattered documentation has been migrated and organized according to the new structure. The following files have been consolidated:

- ✅ `docs/swarm/onboarding_protocols.md` → `protocols/protocol_onboarding_standards.md`
- ✅ `runtime/agent_registry/agent_onboarding_contracts.yaml` → Incorporated into `protocols/protocol_onboarding_standards.md`
- ✅ `runtime/governance/onboarding/agent_onboarding_checklist.yaml` → Incorporated into `protocols/protocol_onboarding_standards.md`

All utility files have been moved to the `utils/` directory and are actively maintained.
