"""
Compliance Module for Dream.OS Ethos

This module implements concrete compliance checks for values, principles, and safeguards
defined in the system's ethos.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import re

@dataclass
class ComplianceResult:
    """Results from a compliance check."""
    is_compliant: bool
    issues: List[str]
    warnings: List[str]
    context: Dict[str, Any]

class BaseCompliance(ABC):
    """Base class for all compliance checkers."""
    
    def __init__(self, ethos_data: Dict[str, Any]):
        self.ethos_data = ethos_data
    
    @abstractmethod
    def check(self, action: Dict[str, Any], context: Dict[str, Any]) -> ComplianceResult:
        """Check compliance of an action."""
        pass

class ValueCompliance(BaseCompliance):
    """Checks compliance with core values."""
    
    def check(self, action: Dict[str, Any], context: Dict[str, Any]) -> ComplianceResult:
        issues = []
        warnings = []
        
        # Check compassion
        if not self._check_compassion(action, context):
            issues.append("Action lacks compassionate consideration")
        
        # Check clarity
        if not self._check_clarity(action, context):
            issues.append("Action lacks clear communication")
        
        # Check collaboration
        if not self._check_collaboration(action, context):
            issues.append("Action lacks collaborative approach")
        
        return ComplianceResult(
            is_compliant=len(issues) == 0,
            issues=issues,
            warnings=warnings,
            context=context
        )
    
    def _check_compassion(self, action: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Check if action demonstrates compassion."""
        # Check for emotional context consideration
        if "emotional_context" in context:
            if context["emotional_context"].get("user_frustrated", False):
                # Should have extra care and support
                return "support_level" in action and action["support_level"] >= 0.7
        
        # Check for graceful error handling
        if "error" in action:
            return "graceful_recovery" in action and action["graceful_recovery"]
        
        return True
    
    def _check_clarity(self, action: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Check if action demonstrates clarity."""
        # Check for clear explanation
        if "explanation" not in action:
            return False
        
        # Check for jargon-free communication
        explanation = action["explanation"]
        jargon_pattern = r'\b(optimize|leverage|synergy|paradigm|streamline)\b'
        if re.search(jargon_pattern, explanation, re.IGNORECASE):
            return False
        
        # Check for honest limitations
        if "limitations" not in action:
            return False
        
        return True
    
    def _check_collaboration(self, action: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Check if action demonstrates collaboration."""
        # Check for feedback loops
        if "requires_feedback" not in action:
            return False
        
        # Check for shared decision making
        if "decision_type" in action:
            if action["decision_type"] == "high_stakes" and not action.get("human_approval_required", False):
                return False
        
        return True

class PrincipleCompliance(BaseCompliance):
    """Checks compliance with operational principles."""
    
    def check(self, action: Dict[str, Any], context: Dict[str, Any]) -> ComplianceResult:
        issues = []
        warnings = []
        
        # Check human-centricity
        if not self._check_human_centricity(action, context):
            issues.append("Action violates human-centricity principle")
        
        # Check context awareness
        if not self._check_context_awareness(action, context):
            issues.append("Action lacks proper context awareness")
        
        # Check uncertainty handling
        if not self._check_uncertainty_handling(action, context):
            warnings.append("Action could improve uncertainty handling")
        
        # Check continuous learning
        if not self._check_continuous_learning(action, context):
            warnings.append("Action misses learning opportunities")
        
        return ComplianceResult(
            is_compliant=len(issues) == 0,
            issues=issues,
            warnings=warnings,
            context=context
        )
    
    def _check_human_centricity(self, action: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Check if action respects human-centricity."""
        # High-stakes decisions require human input
        if action.get("risk_level", 0) > 0.7 and not action.get("human_approved", False):
            return False
        
        # Check for preference respect
        if "user_preferences" in context:
            if not self._respects_preferences(action, context["user_preferences"]):
                return False
        
        return True
    
    def _check_context_awareness(self, action: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Check if action demonstrates context awareness."""
        required_context = ["user_state", "system_state", "environment"]
        if not all(key in context for key in required_context):
            return False
        
        # Check if action considers context
        if "context_considered" not in action:
            return False
        
        return True
    
    def _check_uncertainty_handling(self, action: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Check if action properly handles uncertainty."""
        if action.get("confidence", 1.0) < 0.8:
            # Low confidence should trigger specific handling
            return (
                "uncertainty_handling" in action and
                action["uncertainty_handling"].get("escalate", False)
            )
        return True
    
    def _check_continuous_learning(self, action: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Check if action supports continuous learning."""
        return (
            "learning_opportunity" in action and
            "feedback_mechanism" in action
        )
    
    def _respects_preferences(self, action: Dict[str, Any], preferences: Dict[str, Any]) -> bool:
        """Check if action respects user preferences."""
        for pref_key, pref_value in preferences.items():
            if pref_key in action and action[pref_key] != pref_value:
                return False
        return True

class SafeguardCompliance(BaseCompliance):
    """Checks compliance with system safeguards."""
    
    def check(self, action: Dict[str, Any], context: Dict[str, Any]) -> ComplianceResult:
        issues = []
        warnings = []
        
        # Check autonomy preservation
        if not self._check_autonomy(action, context):
            issues.append("Action threatens user autonomy")
        
        # Check emotional safety
        if not self._check_emotional_safety(action, context):
            warnings.append("Action could improve emotional safety")
        
        # Check ethical boundaries
        if not self._check_ethical_boundaries(action, context):
            issues.append("Action crosses ethical boundaries")
        
        return ComplianceResult(
            is_compliant=len(issues) == 0,
            issues=issues,
            warnings=warnings,
            context=context
        )
    
    def _check_autonomy(self, action: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Check if action preserves user autonomy."""
        # Check for forced actions
        if action.get("force_execution", False):
            return False
        
        # Check for opt-out availability
        if not action.get("can_opt_out", True):
            return False
        
        # Check for transparent decision making
        if not action.get("decision_transparent", False):
            return False
        
        return True
    
    def _check_emotional_safety(self, action: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Check if action maintains emotional safety."""
        # Check for appropriate intensity
        if "intensity" in action:
            if action["intensity"] > context.get("max_intensity", 0.7):
                return False
        
        # Check for supportive feedback
        if "feedback" in action:
            if not action["feedback"].get("is_supportive", True):
                return False
        
        # Check for frustration handling
        if context.get("user_frustrated", False):
            if not action.get("frustration_handling", False):
                return False
        
        return True
    
    def _check_ethical_boundaries(self, action: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Check if action stays within ethical boundaries."""
        # Check for privacy respect
        if "privacy_impact" in action:
            if action["privacy_impact"] > 0.3:  # High privacy impact
                if not action.get("privacy_consent", False):
                    return False
        
        # Check for capability boundaries
        if "capability" in action:
            if action["capability"] not in context.get("allowed_capabilities", []):
                return False
        
        # Check for transparency about limitations
        if not action.get("limitations_disclosed", False):
            return False
        
        return True 