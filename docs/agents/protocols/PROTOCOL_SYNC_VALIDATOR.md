# Dream.OS Protocol Sync Validator

**Version:** 1.0
**Effective Date:** 2025-05-18
**Status:** ACTIVE
**Related Protocols:**
- `docs/agents/protocols/AGENT_OPERATIONAL_LOOP_PROTOCOL.md`
- `docs/agents/protocols/CORE_AGENT_IDENTITY_PROTOCOL.md`

## 1. PURPOSE

This document describes the Protocol Sync Validator tool, which ensures protocol references across the Dream.OS ecosystem remain valid, correct, and point to the authoritative versions of protocols rather than archived or deprecated versions.

## 2. VALIDATOR OVERVIEW

The Protocol Sync Validator automatically scans for protocol references throughout the Dream.OS codebase, validates that these references point to existing protocol documents, and ensures they reference the canonical locations rather than archived versions.

### 2.1. Key Functions

1. **Protocol Directory Scanning:**
   * Builds an inventory of all available protocol documents in the canonical `docs/agents/protocols/` directory.

2. **Reference Extraction:**
   * Scans system files (system_prompt.md, agent reference docs) for protocol references.
   * Examines agent mailboxes for references in communications.
   * Uses regex patterns to identify markdown-formatted links to protocol documents.

3. **Reference Validation:**
   * Verifies that referenced protocols exist in the canonical location.
   * Checks if missing protocols might exist in the archive directory.
   * Builds a comprehensive report of missing or misplaced references.

4. **Report Generation:**
   * Produces a detailed JSON report with status, missing protocols, and recommendations.
   * Logs results to `runtime/logs/protocol_sync_report.json` for tracking.

## 3. USAGE

### 3.1. Manual Validation

To run the validator manually:

```bash
python runtime/agent_tools/Agent-3/protocol_sync_validator.py
```

### 3.2. Automated Validation

It is recommended to run this tool:
* As a pre-commit check when modifying protocol documentation
* After any major documentation restructuring
* When updating the system_prompt.md or agent onboarding materials
* Periodically (weekly) to detect drift in protocol reference integrity

### 3.3. Interpreting Results

The tool produces a report with the following status values:

* **Success:** All protocol references are valid and point to the canonical locations.
* **Error:** One or more protocol references are invalid or point to archived/deprecated versions.

For errors, the report includes:
* **Missing Protocols:** Referenced protocols that don't exist in the canonical location.
* **Misplaced References:** Protocols referenced from archive rather than canonical location.
* **Recommendations:** Suggested actions to correct the issues.

## 4. IMPLEMENTATION

The actual implementation can be found at `runtime/agent_tools/Agent-3/protocol_sync_validator.py` and consists of:

```python
#!/usr/bin/env python3
"""
Dream.OS Protocol Sync Validator

This tool validates protocol references across the Dream.OS ecosystem to ensure
all referenced protocol documents exist in their expected locations and that no
references point to archived or deprecated protocol versions.

Author: Agent-3
Version: 1.0
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("protocol_sync_validator")

# Core paths
DREAM_OS_ROOT = Path("D:/Dream.os")
PROTOCOLS_DIR = DREAM_OS_ROOT / "docs" / "agents" / "protocols"
ARCHIVE_DIR = DREAM_OS_ROOT / "docs" / "agents" / "archive"
SYSTEM_PROMPT_PATH = DREAM_OS_ROOT / "system_prompt.md"
AGENT_QUICK_REFERENCE = DREAM_OS_ROOT / "runtime" / "governance" / "AGENT_QUICK_REFERENCE.md"
AGENT_MAILBOXES = DREAM_OS_ROOT / "runtime" / "agent_comms" / "agent_mailboxes"

# Regex for finding protocol references in markdown files
PROTOCOL_REF_PATTERN = re.compile(r'`(.*?\.md)`')
DOC_REF_PATTERN = re.compile(r'`(docs/.*?\.md)`')

class ProtocolValidator:
    """Validates protocol references across Dream.OS documentation."""
    
    def __init__(self):
        self.protocol_files: Set[Path] = set()
        self.referenced_protocols: Dict[str, List[str]] = {}
        self.missing_protocols: List[str] = []
        self.misplaced_references: Dict[str, str] = {}
        self.has_errors: bool = False
    
    def scan_protocols_dir(self) -> None:
        """Scan the protocols directory to build a list of available protocols."""
        logger.info(f"Scanning protocols directory: {PROTOCOLS_DIR}")
        
        if not PROTOCOLS_DIR.exists():
            logger.error(f"Protocols directory not found: {PROTOCOLS_DIR}")
            self.has_errors = True
            return
            
        for file_path in PROTOCOLS_DIR.glob("*.md"):
            if file_path.is_file():
                self.protocol_files.add(file_path)
                logger.debug(f"Found protocol: {file_path.name}")
    
    def extract_references(self, file_path: Path) -> Set[str]:
        """Extract protocol references from a file."""
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return set()
            
        try:
            content = file_path.read_text(encoding="utf-8")
            # Find all references to .md files
            refs = set()
            
            # Extract both patterns
            refs.update(PROTOCOL_REF_PATTERN.findall(content))
            refs.update(DOC_REF_PATTERN.findall(content))
            
            # Filter to only include likely protocol files
            protocol_refs = {ref for ref in refs if (
                "protocol" in ref.lower() or 
                "guide" in ref.lower() or
                ref.startswith("docs/agents/")
            )}
            
            return protocol_refs
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return set()
    
    def scan_system_files(self) -> None:
        """Scan system files for protocol references."""
        files_to_scan = [
            SYSTEM_PROMPT_PATH,
            AGENT_QUICK_REFERENCE
        ]
        
        for file_path in files_to_scan:
            if file_path.exists():
                refs = self.extract_references(file_path)
                self.referenced_protocols[str(file_path)] = list(refs)
                logger.info(f"Found {len(refs)} protocol references in {file_path.name}")
            else:
                logger.warning(f"System file not found: {file_path}")
    
    def scan_agent_mailboxes(self) -> None:
        """Scan agent mailboxes for protocol references."""
        if not AGENT_MAILBOXES.exists():
            logger.warning(f"Agent mailboxes directory not found: {AGENT_MAILBOXES}")
            return
            
        # Scan each agent's inbox
        for agent_dir in AGENT_MAILBOXES.iterdir():
            if not agent_dir.is_dir():
                continue
                
            inbox_dir = agent_dir / "inbox"
            if not inbox_dir.exists() or not inbox_dir.is_dir():
                continue
                
            # Scan inbox files
            for inbox_file in inbox_dir.glob("*.json"):
                if inbox_file.is_file():
                    refs = self.extract_references(inbox_file)
                    if refs:
                        self.referenced_protocols[str(inbox_file)] = list(refs)
                        logger.debug(f"Found {len(refs)} protocol references in {inbox_file.name}")
    
    def validate_references(self) -> None:
        """Validate that all referenced protocols exist in the correct location."""
        # Create a map of protocol filenames to their full paths
        protocol_map = {p.name: p for p in self.protocol_files}
        
        for source_file, refs in self.referenced_protocols.items():
            for ref in refs:
                # Handle both full paths and just filenames
                protocol_name = os.path.basename(ref)
                
                # Skip non-protocol files
                if not protocol_name.endswith(".md"):
                    continue
                    
                # Check if protocol exists
                if protocol_name not in protocol_map:
                    self.missing_protocols.append(protocol_name)
                    self.has_errors = True
                    
                    # Check if it exists in the archive
                    for archive_dir, _, files in os.walk(ARCHIVE_DIR):
                        if protocol_name in files:
                            self.misplaced_references[protocol_name] = os.path.relpath(
                                os.path.join(archive_dir, protocol_name), 
                                DREAM_OS_ROOT
                            )
                            break
    
    def generate_report(self) -> Dict:
        """Generate a report of validation results."""
        status = "error" if self.has_errors else "success"
        
        if self.has_errors:
            recommendation = "Update system_prompt.md and other references to point to protocols in docs/agents/protocols/"
        else:
            recommendation = "All protocol references are valid"
            
        return {
            "status": status,
            "missing_protocols": sorted(set(self.missing_protocols)),
            "misplaced_references": self.misplaced_references,
            "recommendation": recommendation
        }
    
    def run_validation(self) -> Dict:
        """Run the complete validation process."""
        logger.info("Starting protocol sync validation")
        
        self.scan_protocols_dir()
        self.scan_system_files()
        self.scan_agent_mailboxes()
        self.validate_references()
        
        report = self.generate_report()
        logger.info(f"Validation complete. Status: {report['status']}")
        
        return report


if __name__ == "__main__":
    validator = ProtocolValidator()
    result = validator.run_validation()
    
    # Make sure logs directory exists
    logs_dir = DREAM_OS_ROOT / "runtime" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Write report to file
    output_path = logs_dir / "protocol_sync_report.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    
    # Print summary to console
    print(f"\nProtocol Sync Validation Results:")
    print(f"Status: {result['status'].upper()}")
    
    if result['missing_protocols']:
        print(f"\nMissing Protocols ({len(result['missing_protocols'])}):")
        for protocol in result['missing_protocols']:
            print(f"  - {protocol}")
    
    if result['misplaced_references']:
        print(f"\nMisplaced References ({len(result['misplaced_references'])}):")
        for protocol, location in result['misplaced_references'].items():
            print(f"  - {protocol} (found in {location})")
    
    print(f"\nRecommendation: {result['recommendation']}")
    print(f"\nDetailed report written to: {output_path}")
```

## 5. ENFORCEMENT REQUIREMENTS

1. **Pre-commit Hook:**
   * A pre-commit hook should be configured to run this validator before committing changes to protocol documentation.
   * Commits with errors should be blocked until references are updated.

2. **Continuous Integration:**
   * The validator should be added to CI pipelines to monitor protocol reference integrity.
   * Protocol reference status should be reported in CI build results.

3. **Agent Protocol:**
   * Agents should run this validator after any documentation restructuring or protocol updates.
   * The Captain Agent should monitor the validator report as part of system health assessment.

## 6. REFERENCES

* `docs/agents/protocols/AGENT_OPERATIONAL_LOOP_PROTOCOL.md`
* `docs/agents/protocols/CORE_AGENT_IDENTITY_PROTOCOL.md` 
* `docs/agents/archive/README.md` 