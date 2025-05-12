"""
Compliance dashboard for Dream.os agent onboarding.
Provides real-time monitoring of agent compliance status.
"""

import os
import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Union
from ..utils.onboarding_utils import OnboardingValidator
from ..utils.protocol_compliance import ProtocolComplianceChecker
from ..utils.validation_utils import DocumentationValidator

class ComplianceDashboard:
    """Dashboard for monitoring agent onboarding compliance."""
    
    def __init__(self, base_path: Union[str, Path]):
        self.base_path = Path(base_path)
        self.validator = OnboardingValidator(self.base_path / "protocols")
        self.compliance_checker = ProtocolComplianceChecker(self.base_path)
        self.doc_validator = DocumentationValidator(self.base_path)
        
    def get_agent_status(self, agent_id: str) -> Dict:
        """Get comprehensive status for a single agent."""
        agent_dir = self.base_path / f"agent-{agent_id}"
        if not agent_dir.exists():
            return {
                "status": "not_found",
                "message": f"Agent {agent_id} not found"
            }
            
        # Check protocol compliance
        compliance_results = self.compliance_checker.check_agent(agent_dir)
        
        # Check documentation
        doc_results = self.doc_validator.validate_documentation(agent_dir / "documentation.md")
        
        # Calculate overall status
        status = self._calculate_status(compliance_results, doc_results)
        
        return {
            "agent_id": agent_id,
            "status": status,
            "last_check": datetime.utcnow().isoformat(),
            "compliance": compliance_results,
            "documentation": doc_results,
            "details": self._generate_details(compliance_results, doc_results)
        }
    
    def get_all_agents_status(self) -> Dict[str, Dict]:
        """Get status for all agents."""
        results = {}
        agents_dir = self.base_path / "agents"
        
        if not agents_dir.exists():
            return results
            
        for agent_dir in agents_dir.glob("agent-*"):
            if agent_dir.is_dir():
                agent_id = agent_dir.name.replace("agent-", "")
                results[agent_id] = self.get_agent_status(agent_id)
                
        return results
    
    def _calculate_status(self, compliance_results: Dict, doc_results: Dict) -> str:
        """Calculate overall agent status."""
        # Check if all required files exist
        if not all(compliance_results["checks"]["required_files"].values()):
            return "🔴"
            
        # Check protocol compliance
        if not all(v for v in compliance_results["checks"]["protocol_compliance"].values()):
            return "🔴"
            
        # Check documentation
        if not all(v for v in doc_results["checks"].values()):
            return "🟡"
            
        return "💯"
    
    def _generate_details(self, compliance_results: Dict, doc_results: Dict) -> Dict:
        """Generate detailed status information."""
        details = {
            "compliance": {
                "required_files": compliance_results["checks"]["required_files"],
                "protocol_compliance": compliance_results["checks"]["protocol_compliance"]
            },
            "documentation": {
                "required_sections": doc_results["checks"]["required_sections"],
                "cross_references": doc_results["checks"]["cross_references"],
                "version_info": doc_results["checks"]["version_info"],
                "timestamp": doc_results["checks"]["timestamp"]
            }
        }
        
        return details
    
    def generate_dashboard_report(self) -> str:
        """Generate a human-readable dashboard report."""
        all_status = self.get_all_agents_status()
        
        report = ["# Agent Onboarding Compliance Dashboard",
                 f"Generated: {datetime.utcnow().isoformat()}",
                 "\n## Agent Status"]
        
        # Group agents by status
        status_groups = {
            "💯": [],
            "🟡": [],
            "🔴": []
        }
        
        for agent_id, status in all_status.items():
            status_groups[status["status"]].append(agent_id)
        
        # Add status groups to report
        for status, agents in status_groups.items():
            if agents:
                report.append(f"\n### {status} Status")
                for agent_id in sorted(agents):
                    report.append(f"- {agent_id}")
        
        # Add detailed status for each agent
        report.append("\n## Detailed Status")
        for agent_id, status in all_status.items():
            report.append(f"\n### Agent: {agent_id}")
            report.append(f"Status: {status['status']}")
            report.append(f"Last Check: {status['last_check']}")
            
            # Add compliance details
            report.append("\n#### Compliance")
            for check, result in status["details"]["compliance"].items():
                if isinstance(result, dict):
                    report.append(f"\n##### {check.replace('_', ' ').title()}")
                    for item, passed in result.items():
                        icon = "✅" if passed else "❌"
                        report.append(f"- {icon} {item}")
                else:
                    icon = "✅" if result else "❌"
                    report.append(f"- {icon} {check}")
            
            # Add documentation details
            report.append("\n#### Documentation")
            for check, result in status["details"]["documentation"].items():
                if isinstance(result, dict):
                    report.append(f"\n##### {check.replace('_', ' ').title()}")
                    for item, passed in result.items():
                        icon = "✅" if passed else "❌"
                        report.append(f"- {icon} {item}")
                else:
                    icon = "✅" if result else "❌"
                    report.append(f"- {icon} {check}")
        
        return "\n".join(report)
    
    def save_dashboard_report(self, output_path: Optional[Union[str, Path]] = None) -> None:
        """Save dashboard report to file."""
        if output_path is None:
            output_path = self.base_path / "reports" / f"dashboard_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.md"
        else:
            output_path = Path(output_path)
            
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        report = self.generate_dashboard_report()
        with open(output_path, 'w') as f:
            f.write(report)

def main():
    """CLI entry point for compliance dashboard."""
    import sys
    
    dashboard = ComplianceDashboard("docs/development/guides/onboarding")
    
    if len(sys.argv) > 1 and sys.argv[1] == "--agent":
        if len(sys.argv) < 3:
            print("Usage: python compliance_dashboard.py --agent <agent_id>")
            sys.exit(1)
            
        agent_id = sys.argv[2]
        status = dashboard.get_agent_status(agent_id)
        print(json.dumps(status, indent=2))
    else:
        dashboard.save_dashboard_report()
        print("Dashboard report generated in reports directory")

if __name__ == "__main__":
    main() 