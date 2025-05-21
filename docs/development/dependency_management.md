# Dependency Management

## Overview

This document outlines the dependency management system for Dream.OS, including tools, protocols, and best practices.

## Current Implementation

### Dependency Management Tool

The system uses a dedicated CLI tool (`src/dreamos/cli/manage_deps.py`) for managing Python dependencies in `pyproject.toml`. This tool:
- Uses `tomlkit` for robust TOML parsing and writing
- Preserves file formatting
- Handles atomic writes
- Validates dependency changes

### Key Features

1. **Safe Dependency Updates**
   - Atomic writes to prevent corruption
   - Format preservation
   - Dependency conflict checking

2. **Validation Hooks**
   - Pre-commit validation of TOML structure
   - Poetry dependency conflict checking
   - CI/CD integration

3. **Agent Integration**
   - Automated dependency management
   - Conflict resolution
   - Version control integration

## Best Practices

1. **Adding Dependencies**
   - Use the dedicated dependency management tool
   - Specify version constraints
   - Document dependency purpose

2. **Updating Dependencies**
   - Test compatibility before updates
   - Update in isolated environments
   - Maintain changelog

3. **Removing Dependencies**
   - Verify no other components depend on the package
   - Clean up related configuration
   - Update documentation

## Troubleshooting

### Common Issues

1. **TOML Parsing Errors**
   - Check file format
   - Verify section structure
   - Validate syntax

2. **Dependency Conflicts**
   - Review version constraints
   - Check for circular dependencies
   - Use `poetry check` for validation

3. **Tool Failures**
   - Verify file permissions
   - Check for concurrent access
   - Review error logs

## Future Improvements

1. **Enhanced Validation**
   - Automated conflict detection
   - Security scanning
   - License compliance checking

2. **Integration Features**
   - Container support
   - Environment management
   - Automated testing

3. **Documentation**
   - Dependency graphs
   - Usage examples
   - Best practices guide

## Related Documentation

- [Project Structure](../architecture/project_structure.md)
- [Development Guidelines](../development/guidelines.md)
- [CI/CD Pipeline](../development/ci_cd.md) 