#!/usr/bin/env python3
"""
Dream.OS Documentation Validator

Validates documentation against established standards and requirements.
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple

class DocValidator:
    """Validates Dream.OS documentation against standards."""
    
    def __init__(self, docs_root: str = "docs"):
        self.docs_root = Path(docs_root)
        self.required_sections = {
            "version": r"\*\*Version:\*\*",
            "last_updated": r"\*\*Last Updated:\*\*",
            "status": r"\*\*Status:\*\*"
        }
        self.required_files = {
            "agents/onboarding/UNIFIED_AGENT_ONBOARDING_GUIDE.md",
            "agents/capabilities/AGENT_CAPABILITIES.md",
            "agents/protocols/AGENT_OPERATIONAL_LOOP_PROTOCOL.md",
            "agents/protocols/MESSAGE_ROUTING_PROTOCOL.md",
            "agents/protocols/RESPONSE_VALIDATION_PROTOCOL.md",
            "agents/faqs/general.md"
        }
        
    def validate_file_structure(self) -> List[str]:
        """Validates that all required files exist."""
        missing_files = []
        for file_path in self.required_files:
            if not (self.docs_root / file_path).exists():
                missing_files.append(file_path)
        return missing_files
    
    def validate_markdown_file(self, file_path: Path) -> Dict[str, List[str]]:
        """Validates a single markdown file against standards."""
        issues = []
        if not file_path.exists():
            return {"errors": [f"File not found: {file_path}"]}
            
        content = file_path.read_text()
        
        # Remove HTML comments to ignore links inside them
        def remove_html_comments(text):
            return re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
        content_no_comments = remove_html_comments(content)
        
        # Check required sections
        for section, pattern in self.required_sections.items():
            if not re.search(pattern, content):
                issues.append(f"Missing required section: {section}")
                
        # Check for broken links (ignore those inside comments)
        link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
        for match in re.finditer(link_pattern, content_no_comments):
            link_text, link_path = match.groups()
            if link_path.startswith(("http://", "https://")):
                continue
            if not (self.docs_root / link_path).exists():
                issues.append(f"Broken link: {link_text} -> {link_path}")
                
        # Check for proper headings hierarchy
        heading_pattern = r"^(#{1,6})\s+(.+)$"
        headings = re.findall(heading_pattern, content, re.MULTILINE)
        prev_level = 0
        for level, _ in headings:
            level = len(level)
            if level - prev_level > 1:
                issues.append(f"Invalid heading hierarchy: jumped from h{prev_level} to h{level}")
            prev_level = level
            
        return {"errors": issues} if issues else {"errors": []}
    
    def validate_all(self) -> Dict[str, List[str]]:
        """Validates all documentation files."""
        results = {
            "missing_files": self.validate_file_structure(),
            "file_issues": {}
        }
        
        for file_path in self.required_files:
            full_path = self.docs_root / file_path
            results["file_issues"][file_path] = self.validate_markdown_file(full_path)
            
        return results
    
    def generate_report(self, results: Dict[str, List[str]]) -> str:
        """Generates a human-readable validation report."""
        report = ["Dream.OS Documentation Validation Report", "=" * 40, ""]
        
        if results["missing_files"]:
            report.append("Missing Required Files:")
            for file in results["missing_files"]:
                report.append(f"  - {file}")
            report.append("")
            
        report.append("File-Specific Issues:")
        for file_path, issues in results["file_issues"].items():
            if issues["errors"]:
                report.append(f"\n{file_path}:")
                for error in issues["errors"]:
                    report.append(f"  - {error}")
                    
        return "\n".join(report)

def main():
    """Main entry point for the documentation validator."""
    validator = DocValidator()
    results = validator.validate_all()
    report = validator.generate_report(results)
    
    # Write report to file
    report_path = Path("runtime/validation/docs_validation_report.txt")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report)
    
    # Exit with error if issues found
    if results["missing_files"] or any(issues["errors"] for issues in results["file_issues"].values()):
        print("Documentation validation failed. See report for details.")
        exit(1)
    else:
        print("Documentation validation passed.")

if __name__ == "__main__":
    main() 