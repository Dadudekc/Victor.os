"""
Protocol compliance checking utilities for Dream.os agent onboarding.
Provides tools to validate agent compliance with onboarding protocols.
"""

import os
import sys
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Union
from datetime import datetime

class ProtocolComplianceChecker:
    """Checks agent compliance with onboarding protocols."""
    
    def __init__(self, base_path: Union[str, Path]):
        self.base_path = Path(base_path)
        self.protocols_path = self.base_path / "protocols"
        self.reports_path = self.base_path / "reports"
        
    def check_directory(self, directory: Union[str, Path]) -> Dict:
        """Check all agents in a directory for protocol compliance."""
        directory = Path(directory)
        results = {}
        
        for agent_dir in directory.glob("agent-*"):
            if agent_dir.is_dir():
                agent_id = agent_dir.name
                results[agent_id] = self.check_agent(agent_dir)
                
        return results
    
    def check_agent(self, agent_path: Union[str, Path]) -> Dict:
        """Check a single agent for protocol compliance."""
        agent_path = Path(agent_path)
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {}
        }
        
        # Check required files
        results["checks"]["required_files"] = self._check_required_files(agent_path)
        
        # Check protocol compliance
        results["checks"]["protocol_compliance"] = self._check_protocol_compliance(agent_path)
        
        # Check documentation
        results["checks"]["documentation"] = self._check_documentation(agent_path)
        
        return results
    
    def _check_required_files(self, agent_path: Path) -> Dict[str, bool]:
        """Check for presence of required files."""
        required_files = [
            "onboarding_contract.yaml",
            "protocol_compliance.json",
            "documentation.md"
        ]
        
        results = {}
        for file in required_files:
            results[file] = (agent_path / file).exists()
            
        return results
    
    def _check_protocol_compliance(self, agent_path: Path) -> Dict[str, bool]:
        """Check protocol compliance based on contract and compliance files."""
        results = {}
        
        # Check contract
        contract_path = agent_path / "onboarding_contract.yaml"
        if contract_path.exists():
            with open(contract_path) as f:
                contract = yaml.safe_load(f)
                results["contract_valid"] = self._validate_contract(contract)
        
        # Check compliance
        compliance_path = agent_path / "protocol_compliance.json"
        if compliance_path.exists():
            with open(compliance_path) as f:
                compliance = json.load(f)
                results["compliance_valid"] = self._validate_compliance(compliance)
                
        return results
    
    def _check_documentation(self, agent_path: Path) -> Dict[str, bool]:
        """Check documentation completeness and format."""
        results = {}
        doc_path = agent_path / "documentation.md"
        
        if doc_path.exists():
            with open(doc_path) as f:
                content = f.read()
                results["has_required_sections"] = self._check_doc_sections(content)
                results["has_version_info"] = "## Version" in content
                results["has_timestamp"] = "## Timestamp" in content
                
        return results
    
    def _validate_contract(self, contract: Dict) -> bool:
        """Validate onboarding contract structure and content."""
        required_fields = [
            "agent_id",
            "protocol_version",
            "compliance_checks",
            "documentation_requirements"
        ]
        
        return all(field in contract for field in required_fields)
    
    def _validate_compliance(self, compliance: Dict) -> bool:
        """Validate protocol compliance data."""
        required_fields = [
            "last_check",
            "compliance_status",
            "violations"
        ]
        
        return all(field in compliance for field in required_fields)
    
    def _check_doc_sections(self, content: str) -> bool:
        """Check for required documentation sections."""
        required_sections = [
            "## Overview",
            "## Protocol Compliance",
            "## Documentation",
            "## Security",
            "## Operational Status"
        ]
        
        return all(section in content for section in required_sections)
    
    def generate_report(self, results: Dict) -> str:
        """Generate a human-readable compliance report."""
        report = ["# Protocol Compliance Report",
                 f"Generated: {datetime.utcnow().isoformat()}",
                 "\n## Results"]
        
        for agent_id, agent_results in results.items():
            report.append(f"\n### Agent: {agent_id}")
            
            for check_type, check_results in agent_results["checks"].items():
                report.append(f"\n#### {check_type.replace('_', ' ').title()}")
                
                for item, status in check_results.items():
                    status_icon = "✅" if status else "❌"
                    report.append(f"- {status_icon} {item}")
                    
        return "\n".join(report)
    
    def save_report(self, report: str, output_path: Optional[Union[str, Path]] = None) -> None:
        """Save compliance report to file."""
        if output_path is None:
            output_path = self.reports_path / f"compliance_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.md"
        else:
            output_path = Path(output_path)
            
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            f.write(report)

def main():
    """CLI entry point for protocol compliance checking."""
    if len(sys.argv) < 2:
        print("Usage: python protocol_compliance.py <directory_to_check>")
        sys.exit(1)
        
    directory = sys.argv[1]
    checker = ProtocolComplianceChecker("docs/development/guides/onboarding")
    results = checker.check_directory(directory)
    report = checker.generate_report(results)
    checker.save_report(report)
    
    print(f"Compliance report generated: {checker.reports_path}")

if __name__ == "__main__":
    main() 