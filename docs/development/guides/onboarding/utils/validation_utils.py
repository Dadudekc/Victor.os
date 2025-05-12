"""
Documentation validation utilities for Dream.os agent onboarding.
Provides tools to validate documentation completeness, format, and cross-references.
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
from datetime import datetime

logger = logging.getLogger(__name__)

class DocumentationValidator:
    """Validates documentation completeness and format."""
    
    def __init__(self, base_path: Union[str, Path]):
        self.base_path = Path(base_path)
        self.required_sections = {
            "overview": ["## Overview"],
            "protocol_compliance": ["## Protocol Compliance"],
            "documentation": ["## Documentation"],
            "security": ["## Security"],
            "operational": ["## Operational Status"]
        }
        
    def validate_documentation(self, doc_path: Union[str, Path]) -> Dict[str, bool]:
        """Validate a documentation file for completeness and format."""
        doc_path = Path(doc_path)
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {}
        }
        
        if not doc_path.exists():
            results["checks"]["file_exists"] = False
            return results
            
        results["checks"]["file_exists"] = True
        
        with open(doc_path) as f:
            content = f.read()
            
        # Check required sections
        results["checks"]["required_sections"] = self._check_required_sections(content)
        
        # Check cross-references
        results["checks"]["cross_references"] = self._check_cross_references(content)
        
        # Check version info
        results["checks"]["version_info"] = self._check_version_info(content)
        
        # Check timestamp
        results["checks"]["timestamp"] = self._check_timestamp(content)
        
        return results
    
    def _check_required_sections(self, content: str) -> Dict[str, bool]:
        """Check for presence of required sections."""
        results = {}
        
        for section, patterns in self.required_sections.items():
            results[section] = any(pattern in content for pattern in patterns)
            
        return results
    
    def _check_cross_references(self, content: str) -> Dict[str, bool]:
        """Check validity of cross-references."""
        results = {
            "internal_links": self._check_internal_links(content),
            "protocol_references": self._check_protocol_references(content),
            "document_references": self._check_document_references(content)
        }
        
        return results
    
    def _check_internal_links(self, content: str) -> bool:
        """Check if internal links are valid."""
        # Find all markdown links
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        links = re.findall(link_pattern, content)
        
        for _, link in links:
            if link.startswith('#'):
                # Internal anchor link
                anchor = link[1:].lower().replace(' ', '-')
                if f"## {anchor}" not in content.lower():
                    return False
            elif not link.startswith(('http://', 'https://')):
                # Local file link
                link_path = self.base_path / link
                if not link_path.exists():
                    return False
                    
        return True
    
    def _check_protocol_references(self, content: str) -> bool:
        """Check if protocol references are valid."""
        protocol_pattern = r'`protocol_([^`]+)\.md`'
        protocols = re.findall(protocol_pattern, content)
        
        for protocol in protocols:
            protocol_path = self.base_path / "protocols" / f"protocol_{protocol}.md"
            if not protocol_path.exists():
                return False
                
        return True
    
    def _check_document_references(self, content: str) -> bool:
        """Check if document references are valid."""
        doc_pattern = r'`([^`]+)\.md`'
        docs = re.findall(doc_pattern, content)
        
        for doc in docs:
            if doc.startswith('protocol_'):
                continue  # Skip protocol references
            doc_path = self.base_path / f"{doc}.md"
            if not doc_path.exists():
                return False
                
        return True
    
    def _check_version_info(self, content: str) -> bool:
        """Check if version information is present and valid."""
        version_pattern = r'## Version\s*\n\s*-\s*v\d+\.\d+\.\d+'
        match = re.search(version_pattern, content)
        logger.debug(f"Version pattern match: {match}")
        if match:
            logger.debug(f"Version match group: {match.group()}")
        return bool(match)
    
    def _check_timestamp(self, content: str) -> bool:
        """Check if timestamp is present and valid."""
        timestamp_pattern = r'## Timestamp\s*\n\s*-\s*\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z'
        match = re.search(timestamp_pattern, content)
        logger.debug(f"Timestamp pattern match: {match}")
        if match:
            logger.debug(f"Timestamp match group: {match.group()}")
        return bool(match)
    
    def generate_report(self, results: Dict) -> str:
        """Generate a human-readable validation report."""
        report = ["# Documentation Validation Report",
                 f"Generated: {datetime.utcnow().isoformat()}",
                 "\n## Results"]
        
        for check_type, check_results in results["checks"].items():
            if isinstance(check_results, dict):
                report.append(f"\n### {check_type.replace('_', ' ').title()}")
                
                for item, status in check_results.items():
                    status_icon = "✅" if status else "❌"
                    report.append(f"- {status_icon} {item}")
            else:
                status_icon = "✅" if check_results else "❌"
                report.append(f"\n### {check_type.replace('_', ' ').title()}\n{status_icon}")
                
        return "\n".join(report)
    
    def save_report(self, report: str, output_path: Union[str, Path]) -> None:
        """Save validation report to file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            f.write(report)

def main():
    """CLI entry point for documentation validation."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python validation_utils.py <documentation_file>")
        sys.exit(1)
        
    doc_file = sys.argv[1]
    validator = DocumentationValidator("docs/development/guides/onboarding")
    results = validator.validate_documentation(doc_file)
    report = validator.generate_report(results)
    
    output_path = Path("reports/validation") / f"{Path(doc_file).stem}_validation.md"
    validator.save_report(report, output_path)
    
    print(f"Validation report generated: {output_path}")

if __name__ == "__main__":
    main() 