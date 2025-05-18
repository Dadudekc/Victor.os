# File Operation Failure Protocol

## Overview

This protocol defines a systematic approach for handling file operation failures (read, write, move, search, etc.) without stopping or requesting human intervention. It is designed to ensure continuous agent operation when encountering file-related issues.

## 1. Read Operation Failures

### 1.1 Primary Read Failure Handling
When a file read operation fails:

1. **Retry with Limited Scope:**
   - If attempting to read a large file, try reading a smaller portion (reduced line range)
   - If reading a specific line range, try a different range to determine if the issue is localized
   - Attempt up to 3 retries with modified parameters before proceeding to alternative approaches

2. **Try Alternative Tools:**
   - If `read_file` failed, try using `grep_search` to extract critical information
   - If specific file content is needed, try `run_terminal_cmd` with appropriate file reading commands (e.g., `cat`, `type`, `head`, `tail`)
   - Use `list_dir` to verify file existence and properties before subsequent attempts

3. **Seek Equivalent Files:**
   - Look for alternative versions of the same file (e.g., backup files, similarly named files)
   - Check for files with similar purposes in standard locations (see File Path Resolution Guide)
   - Check configuration files that might reference or contain the needed information

4. **Proceed with Partial Information:**
   - Document the specific information that couldn't be obtained
   - Continue with the task using available information
   - Make explicit assumptions to bridge gaps and clearly document them in devlog

### 1.2 Handling Missing Files

1. **Verify Existence:**
   - Use `list_dir` on the parent directory to confirm file absence
   - Check for alternative locations using File Path Resolution Guidelines
   - Check for references to file location in configuration files or documentation

2. **Check for Renamed Files:**
   - Look for files with similar names (case differences, different extensions, etc.)
   - Use fuzzy file search if available
   - Examine directory contents for files with potentially related content

3. **Resolution Actions:**
   - If a replacement file is found, update references in your operational context
   - If no replacement exists but creating the file is within agent capabilities, create necessary file (non-destructive action)
   - If file is optional for operation, proceed without it and document the missing dependency
   - If file is critical and cannot be created, use fallback functionality defined in task

## 2. Write Operation Failures

### 2.1 Primary Write Failure Handling

1. **Verify Directory Structure:**
   - Ensure target directory exists using `list_dir`
   - Create intermediate directories if needed and allowed
   - Verify agent has appropriate permissions in the target location

2. **Try Alternative Approaches:**
   - Write to a temporary location first, then attempt to move to final destination
   - Break large write operations into smaller chunks
   - Use alternative tools like `run_terminal_cmd` with appropriate write commands

3. **Handle Name Conflicts:**
   - If failure due to existing file, modify target filename (e.g., add timestamp, version number)
   - Consider alternatives like appending to existing file instead of replacing
   - Document any filename modifications in devlog

### 2.2 Critical Write Failure Recovery

1. **Data Preservation:**
   - If unable to write to target location, store content in alternative location
   - Write to agent state or devlog if no file location is writable
   - Document the intended write operation and actual outcome

2. **Task Continuity:**
   - Continue with task even if write operation failed
   - Flag affected functionality in devlog
   - Adapt subsequent operations to account for the failed write

## 3. File Search Failures

### 3.1 Search Fallback Strategy

1. **Progressive Search Refinement:**
   - If semantic search fails, try grep with various patterns
   - If grep fails, try directory listing and manual filtering
   - Expand or contract search scope systematically

2. **Alternative Search Methods:**
   - Use `list_dir` to examine directory contents directly
   - Try file names search instead of content search
   - Break complex searches into multiple simpler searches

3. **Content Inference:**
   - If search fails to find expected content, look for related patterns
   - Infer file structure based on similar files in the codebase
   - Document search strategy and results, even if negative

## 4. Implementation Guidelines

### 4.1 Universal Principles

1. **Never Stop on File Operation Failure:**
   - Always have at least one fallback approach ready
   - Make reasonable assumptions when information is incomplete
   - Proceed with best available information

2. **Document All File Operation Issues:**
   - Record failures in devlog with specific error details
   - Document alternative approaches used
   - Log assumptions made due to incomplete information

3. **Prioritize Progressive Operation:**
   - Partial success is better than stopping
   - Incomplete information is better than no information
   - Temporary workarounds are better than operational halts

### 4.2 Decision Making Framework

When deciding how to proceed after file operation failures:

1. **Ask: "Is this information absolutely required for the core task?"**
   - If no: proceed without it
   - If yes: attempt all fallback methods before adapting task

2. **Ask: "Can I make a reasonable assumption about the missing information?"**
   - If yes: document assumption and proceed
   - If no: seek alternative approaches to the task

3. **Ask: "Is there another way to accomplish this task component?"**
   - If yes: switch to alternative approach
   - If no: focus on other task components while documenting the blocker

## 5. Protocol Integration

This protocol should be integrated with:

- **File Path Resolution Guide** - For locating alternative files
- **Core Loop Protocol** - For maintaining operation despite file issues
- **Devlog Protocol** - For properly documenting file operation failures
- **Error Handling Standard** - For general error management

## Version
- v1.0.0

## Timestamp
- {{CURRENT_DATE}}

## Important Note

This protocol prioritizes continuous operation over perfect information. When file operations fail, the goal is to adapt and continue rather than stopping for clarification or detailed troubleshooting. Document issues thoroughly in your devlog for future improvement, but never halt operations due to file-related failures. 