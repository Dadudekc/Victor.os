"""
Agent compliance enforcement utilities.
Provides hooks for checking and enforcing compliance at agent boot.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Optional, Union
from datetime import datetime

from .onboarding_utils import OnboardingValidator
from .protocol_compliance import ProtocolComplianceChecker
from .validation_utils import DocumentationValidator

logger = logging.getLogger(__name__)

class AgentComplianceEnforcer:
    """Enforces agent compliance at boot time."""
    
    def __init__(
        self,
        base_path: Union[str, Path],
        strict: bool = False,
        escalate_violations: bool = True
    ):
        self.base_path = Path(base_path).resolve()  # Make path absolute
        self.strict = strict
        self.escalate_violations = escalate_violations
        self.validator = OnboardingValidator(self.base_path / "protocols")
        self.compliance_checker = ProtocolComplianceChecker(self.base_path)
        self.doc_validator = DocumentationValidator(self.base_path)
        
    def check_agent_compliance(
        self,
        agent_id: str,
        agent_dir: Optional[Union[str, Path]] = None
    ) -> Dict:
        """Check agent compliance and optionally enforce it."""
        if agent_dir is None:
            # For Agent-1, use the mailbox directory directly
            if agent_id == "Agent-1":
                agent_dir = self.base_path
            else:
                agent_dir = self.base_path / f"agent-{agent_id}"
        else:
            agent_dir = Path(agent_dir).resolve()  # Make path absolute
            
        if not agent_dir.exists():
            violation = {
                "agent_id": agent_id,
                "timestamp": datetime.utcnow().isoformat(),
                "type": "missing_directory",
                "message": f"Agent directory not found: {agent_dir}"
            }
            self._handle_violation(violation)
            return {"compliant": False, "violations": [violation]}
            
        # Run all compliance checks
        compliance_results = self.compliance_checker.check_agent(agent_dir)
        doc_results = self.doc_validator.validate_documentation(agent_dir / "AGENT_ONBOARDING_GUIDE.md")
        
        # Collect violations
        violations = []
        
        # Check required files
        for file, exists in compliance_results["checks"]["required_files"].items():
            if not exists:
                violations.append({
                    "agent_id": agent_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "missing_file",
                    "message": f"Required file missing: {file}"
                })
                
        # Check protocol compliance
        for check, passed in compliance_results["checks"]["protocol_compliance"].items():
            if not passed:
                violations.append({
                    "agent_id": agent_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "protocol_violation",
                    "message": f"Protocol violation: {check}"
                })
                
        # Check documentation
        for check, passed in doc_results["checks"].items():
            if not passed:
                violations.append({
                    "agent_id": agent_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "documentation_violation",
                    "message": f"Documentation violation: {check}"
                })
                
        # Handle violations
        if violations:
            for violation in violations:
                self._handle_violation(violation)
                
            if self.strict:
                logger.error(f"Agent {agent_id} failed compliance check in strict mode")
                raise ComplianceError(f"Agent {agent_id} failed compliance check", violations)
                
        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    def _handle_violation(self, violation: Dict) -> None:
        """Handle a compliance violation."""
        logger.warning(f"Compliance violation: {violation['message']}")
        
        if self.escalate_violations:
            self._escalate_violation(violation)
            
    def _escalate_violation(self, violation: Dict) -> None:
        """Escalate violation to Thea."""
        # Create violations directory if it doesn't exist
        violations_dir = self.base_path / "violations"
        violations_dir.mkdir(parents=True, exist_ok=True)  # Create parent dirs if needed
        
        # Save violation to file
        violation_file = violations_dir / f"violation_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(violation_file, 'w') as f:
            json.dump(violation, f, indent=2)
            
        # TODO: Implement Thea escalation
        logger.info(f"Violation escalated and saved to {violation_file}")

class ComplianceError(Exception):
    """Raised when an agent fails compliance check in strict mode."""
    def __init__(self, message: str, violations: list):
        self.violations = violations
        super().__init__(message)

def check_agent_compliance(
    agent_id: str,
    base_path: Union[str, Path],
    strict: bool = False,
    escalate_violations: bool = True
) -> Dict:
    """Convenience function to check agent compliance."""
    enforcer = AgentComplianceEnforcer(
        base_path=base_path,
        strict=strict,
        escalate_violations=escalate_violations
    )
    return enforcer.check_agent_compliance(agent_id) 