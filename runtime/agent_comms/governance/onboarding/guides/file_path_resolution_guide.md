# File Path Resolution Guide

## Overview

This guide provides a systematic approach for agents to resolve file path ambiguity without stopping or requiring human intervention. It should be referenced when tasked with finding, analyzing, or modifying files where the exact path is unclear or when encountering file operation failures.

## Key Principles

1. **Never Stop for File-Related Ambiguity** - Make informed decisions and proceed rather than asking for clarification
2. **Prioritize Canonical Locations** - Follow the system's established hierarchies
3. **Document Decisions** - Log your reasoning and chosen paths in your devlog
4. **Proceed with Best Available Information** - When perfect information isn't accessible

## Canonical Path Hierarchy

When trying to locate a file with an ambiguous path, prioritize in this order:

1. `runtime/governance/` - The primary location for current governance files
2. `runtime/agent_comms/governance/` - Agent communication governance files
3. Root-level directories - Main project directories
4. `docs/agents/protocols/` - Newer protocol documentation
5. `docs/agents/` - General agent documentation
6. `docs/agents/protocols/from_old_docs/` - Legacy files (lowest priority)

## Progressive Search Strategy

When a direct path fails, follow this systematic approach:

1. **Try Path Variants**:
   - Check both upper and lowercase versions of the filename (`FILE.md` vs `file.md`)
   - Try common extensions (`.md`, `.txt`, `.json`) if extension is unclear
   - Try with/without underscores or hyphens if naming convention is ambiguous

2. **Use Search Tools**:
   - Use fuzzy file search to find similarly named files
   - Use codebase search to locate references to the file
   - Search in configuration files that might reference the path

3. **Examine Directory Contents**:
   - List contents of likely parent directories
   - Look for similarly named files or common patterns

## Decision-Making Process

When multiple candidate files exist:

1. **Apply Prioritization Rules**:
   - Choose files from higher priority locations (`runtime/` over `docs/`)
   - Choose non-legacy versions over legacy/archived versions
   - Choose files with more recent modification dates if available
   - Choose files with naming conventions that match current standards

2. **Content-Based Selection**:
   - Read file snippets to determine relevance to the task
   - Check for version indicators in the content
   - Look for references to other current files/systems

3. **Make and Document Decision**:
   - Select the most appropriate file based on above criteria
   - Document your selection and reasoning in your devlog
   - Proceed with the selected file without asking for confirmation

## Handling File Operation Failures

If file operations (read, write, move) fail:

1. **Retry Operations**:
   - Try the operation again (up to 2-3 times)
   - Use alternative tools or methods for the same operation

2. **Adapt Strategy**:
   - If reading fails, try reading smaller portions or different line ranges
   - If writing fails, try writing to a temporary location first
   - Consider splitting large operations into smaller chunks

3. **Use Alternative Information Sources**:
   - If unable to read a specific file, search for related information in other files
   - Check for cached versions or copies in different locations
   - Proceed with partial information if sufficient for the task

4. **Create Target Directory Structure**:
   - If writing to a non-existent directory, ensure the directory exists first
   - Follow path convention patterns from similar existing files

## Example Resolution Workflow

**Scenario**: Agent needs to find `AGENT_ONBOARDING_CHECKLIST.md` but exact path is unknown.

**Resolution Steps**:
1. Check `runtime/governance/onboarding/` (highest priority location)
2. Not found, check `docs/agents/onboarding/` and `docs/agents/`
3. Found in both locations - compare timestamps and content
4. Choose the version in `docs/agents/` based on more recent modification date
5. Document choice in devlog: "Selected `docs/agents/AGENT_ONBOARDING_CHECKLIST.md` as primary source as it appears to be the most recent version (modified 2023-10-15 vs 2023-09-01 for the alternative version)"
6. Proceed with using the selected file

## Conclusion

By following this guide, agents can confidently handle file path ambiguity without stopping or requiring human intervention. This ensures continuous autonomous operation while making informed decisions about file locations and operations.

Remember: **It is always better to make a reasonable choice and proceed than to stop and ask for clarification about file paths.** 