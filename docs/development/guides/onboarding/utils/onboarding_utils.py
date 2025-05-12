"""
Core utilities for agent onboarding in Dream.os.
Provides functions for validation, compliance checking, and onboarding workflow management.
"""

import os
import yaml
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

class OnboardingValidator:
    """Validates agent onboarding compliance and requirements."""
    
    def __init__(self, protocol_path: Union[str, Path]):
        self.protocol_path = Path(protocol_path)
        self.protocols = self._load_protocols()
        
    def _load_protocols(self) -> Dict:
        """Load onboarding protocols from YAML files."""
        protocols = {}
        protocol_dir = self.protocol_path.parent / "protocols"
        
        for protocol_file in protocol_dir.glob("protocol_*.md"):
            with open(protocol_file, 'r') as f:
                protocols[protocol_file.stem] = self._parse_protocol(f.read())
                
        return protocols
    
    def _parse_protocol(self, content: str) -> Dict:
        """Parse protocol markdown into structured data."""
        # Basic markdown parsing - can be enhanced
        sections = {}
        current_section = None
        
        for line in content.split('\n'):
            if line.startswith('### '):
                current_section = line[4:].strip()
                sections[current_section] = []
            elif current_section and line.startswith('- '):
                sections[current_section].append(line[2:].strip())
                
        return sections
    
    def validate_agent(self, agent_id: str, agent_data: Dict) -> Dict[str, bool]:
        """Validate an agent against onboarding requirements."""
        results = {
            "initialization": self._check_initialization(agent_data),
            "protocol_compliance": self._check_protocol_compliance(agent_data),
            "documentation": self._check_documentation(agent_data),
            "security": self._check_security(agent_data),
            "operational": self._check_operational(agent_data)
        }
        
        return results
    
    def _check_initialization(self, agent_data: Dict) -> bool:
        """Check if agent has completed initialization sequence."""
        required = self.protocols.get('protocol_onboarding_standards', {}).get('Initialization', [])
        return all(req in agent_data.get('initialization', []) for req in required)
    
    def _check_protocol_compliance(self, agent_data: Dict) -> bool:
        """Check if agent adheres to all protocols."""
        required = self.protocols.get('protocol_onboarding_standards', {}).get('Protocol Compliance', [])
        return all(req in agent_data.get('protocol_compliance', []) for req in required)
    
    def _check_documentation(self, agent_data: Dict) -> bool:
        """Check if agent has completed documentation requirements."""
        required = self.protocols.get('protocol_onboarding_standards', {}).get('Documentation Requirements', [])
        return all(req in agent_data.get('documentation', []) for req in required)
    
    def _check_security(self, agent_data: Dict) -> bool:
        """Check if agent meets security requirements."""
        required = self.protocols.get('protocol_onboarding_standards', {}).get('Security Requirements', [])
        return all(req in agent_data.get('security', []) for req in required)
    
    def _check_operational(self, agent_data: Dict) -> bool:
        """Check if agent meets operational requirements."""
        required = self.protocols.get('protocol_onboarding_standards', {}).get('Operational Requirements', [])
        return all(req in agent_data.get('operational', []) for req in required)

def generate_onboarding_report(agent_id: str, validation_results: Dict[str, bool]) -> str:
    """Generate a human-readable onboarding validation report."""
    report = [f"# Onboarding Validation Report for Agent {agent_id}",
              f"Generated: {datetime.utcnow().isoformat()}",
              "\n## Validation Results"]
    
    for category, passed in validation_results.items():
        status = "✅" if passed else "❌"
        report.append(f"\n### {category.title()}\n{status} {'Passed' if passed else 'Failed'}")
    
    return "\n".join(report)

def save_validation_report(report: str, output_path: Union[str, Path]) -> None:
    """Save validation report to specified path."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        f.write(report)

if __name__ == "__main__":
    # Example usage
    validator = OnboardingValidator("docs/development/guides/onboarding/protocols")
    agent_data = {
        "initialization": ["system_checks", "contract_verification"],
        "protocol_compliance": ["regular_checks", "updates_reviewed"],
        "documentation": ["activities_documented", "format_followed"],
        "security": ["authentication_completed", "access_controls_implemented"],
        "operational": ["monitoring_established", "error_handling_implemented"]
    }
    
    results = validator.validate_agent("agent-001", agent_data)
    report = generate_onboarding_report("agent-001", results)
    save_validation_report(report, "reports/onboarding/agent-001_validation.md") 