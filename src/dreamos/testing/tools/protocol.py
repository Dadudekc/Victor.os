"""
Protocol verification framework for Dream.OS.

This module provides a framework for verifying protocol adherence
within Dream.OS, with initial focus on the Autonomous Operation Protocol
and Degraded Operation Mode.
"""

import os
import re
import json
import time
import yaml
import logging
from pathlib import Path

class ProtocolDefinitionLoader:
    """Load and parse protocol definitions."""
    
    def __init__(self, protocol_path=None, logger=None):
        self.protocol_path = protocol_path or os.path.join("docs", "protocols")
        self.protocols = {}
        self.logger = logger or logging.getLogger(__name__)
    
    def load_protocol(self, protocol_name):
        """Load a specific protocol by name."""
        # First check if the protocol is already loaded
        if protocol_name in self.protocols:
            return self.protocols[protocol_name]
        
        # Look for the protocol file
        protocol_file = None
        for ext in [".md", ".yaml", ".json"]:
            file_path = os.path.join(self.protocol_path, f"{protocol_name}{ext}")
            if os.path.exists(file_path):
                protocol_file = file_path
                break
        
        if not protocol_file:
            raise FileNotFoundError(f"Protocol definition not found: {protocol_name}")
        
        # Parse the protocol definition based on file extension
        protocol_def = self._parse_protocol_file(protocol_file)
        self.protocols[protocol_name] = protocol_def
        return protocol_def
    
    def _parse_protocol_file(self, protocol_file):
        """Parse a protocol definition file."""
        extension = os.path.splitext(protocol_file)[1].lower()
        
        try:
            if extension == ".json":
                with open(protocol_file, "r") as f:
                    return json.load(f)
            elif extension == ".yaml":
                with open(protocol_file, "r") as f:
                    return yaml.safe_load(f)
            elif extension == ".md":
                return self._parse_markdown_protocol(protocol_file)
            else:
                raise ValueError(f"Unsupported protocol file format: {extension}")
        except Exception as e:
            self.logger.error(f"Error parsing protocol file {protocol_file}: {str(e)}")
            raise
    
    def _parse_markdown_protocol(self, md_file):
        """Parse a markdown protocol definition."""
        with open(md_file, "r") as f:
            content = f.read()
        
        # This is a simplified parser that should be expanded based on the actual format
        # of the protocol documentation
        protocol = {
            "name": os.path.basename(md_file).replace(".md", ""),
            "states": [],
            "transitions": [],
            "decision_points": [],
            "fallback_modes": []
        }
        
        # Extract states
        states_match = re.search(r"## States\s+(.*?)(?=##|\Z)", content, re.DOTALL)
        if states_match:
            states_text = states_match.group(1)
            for line in states_text.strip().split("\n"):
                if line.strip() and line.strip().startswith("- "):
                    state = line.strip()[2:].strip()
                    protocol["states"].append(state)
        
        # Extract transitions
        transitions_match = re.search(r"## Transitions\s+(.*?)(?=##|\Z)", content, re.DOTALL)
        if transitions_match:
            transitions_text = transitions_match.group(1)
            for line in transitions_text.strip().split("\n"):
                if line.strip() and line.strip().startswith("- "):
                    transition_text = line.strip()[2:].strip()
                    # Assuming format: FROM + EVENT -> TO
                    match = re.search(r"([^+]+)\+\s*([^-]+)->(.+)", transition_text)
                    if match:
                        from_state = match.group(1).strip()
                        event = match.group(2).strip()
                        to_state = match.group(3).strip()
                        protocol["transitions"].append({
                            "from": from_state,
                            "event": event,
                            "to": to_state
                        })
        
        # Extract decision points
        decision_match = re.search(r"## Decision Points\s+(.*?)(?=##|\Z)", content, re.DOTALL)
        if decision_match:
            decision_text = decision_match.group(1)
            for line in decision_text.strip().split("\n"):
                if line.strip() and line.strip().startswith("- "):
                    decision = line.strip()[2:].strip()
                    protocol["decision_points"].append(decision)
        
        # Extract fallback modes
        fallback_match = re.search(r"## Fallback Modes\s+(.*?)(?=##|\Z)", content, re.DOTALL)
        if fallback_match:
            fallback_text = fallback_match.group(1)
            for line in fallback_text.strip().split("\n"):
                if line.strip() and line.strip().startswith("- "):
                    fallback = line.strip()[2:].strip()
                    protocol["fallback_modes"].append(fallback)
        
        return protocol

class ProtocolStateMachine:
    """Model a protocol as a state machine for verification."""
    
    def __init__(self, protocol_def, logger=None):
        self.protocol_def = protocol_def
        self.current_state = None
        self.history = []
        self.logger = logger or logging.getLogger(__name__)
    
    def initialize(self, state=None):
        """Initialize the state machine."""
        if not self.protocol_def["states"]:
            raise ValueError("Protocol has no states defined")
            
        self.current_state = state or self.protocol_def["states"][0]
        self.history = [self.current_state]
        return self.current_state
    
    def transition(self, event):
        """Attempt a state transition based on an event."""
        if self.current_state is None:
            raise ValueError("State machine not initialized")
            
        for transition in self.protocol_def["transitions"]:
            if (transition["from"] == self.current_state and 
                transition["event"] == event):
                self.current_state = transition["to"]
                self.history.append(self.current_state)
                self.logger.debug(f"Transition: {transition['from']} + {event} -> {self.current_state}")
                return True, self.current_state
                
        self.logger.warning(f"Invalid transition: {self.current_state} + {event}")
        return False, self.current_state
    
    def verify_path(self, path):
        """Verify that a given path through the state machine is valid."""
        if not path:
            return True, "Empty path is valid"
            
        # Reset the state machine
        self.initialize(path[0][0])
        
        # Attempt to follow the path
        for i, (state, event) in enumerate(path[:-1]):
            if state != self.current_state:
                return False, f"State mismatch at step {i}: expected {state}, got {self.current_state}"
            
            success, new_state = self.transition(event)
            if not success:
                return False, f"Invalid transition at step {i}: {state} + {event}"
            
            if new_state != path[i+1][0]:
                return False, f"Transition result mismatch at step {i}: expected {path[i+1][0]}, got {new_state}"
        
        return True, "Path verified"
    
    def get_valid_events(self):
        """Get the list of valid events for the current state."""
        events = []
        for transition in self.protocol_def["transitions"]:
            if transition["from"] == self.current_state:
                events.append(transition["event"])
        return events

class ProtocolValidator:
    """Validate protocol implementation against definition."""
    
    def __init__(self, protocol_name, protocol_def=None, logger=None):
        self.protocol_name = protocol_name
        self.protocol_def = protocol_def
        self.logger = logger or logging.getLogger(__name__)
        self.results = {}
        
        if not protocol_def:
            try:
                loader = ProtocolDefinitionLoader(logger=self.logger)
                self.protocol_def = loader.load_protocol(protocol_name)
            except Exception as e:
                self.logger.error(f"Error loading protocol {protocol_name}: {str(e)}")
                raise
        
        self.state_machine = ProtocolStateMachine(self.protocol_def, logger=self.logger)
    
    def validate_implementation(self, implementation, test_cases=None):
        """Validate that an implementation adheres to the protocol."""
        if test_cases is None:
            test_cases = self.generate_test_cases()
            
        results = []
        for test_case in test_cases:
            result = self.run_test_case(test_case, implementation)
            results.append({
                "test_case": test_case,
                "result": result
            })
        
        self.results = {
            "protocol": self.protocol_name,
            "implementation": getattr(implementation, "__name__", str(implementation)),
            "test_count": len(test_cases),
            "success_count": sum(1 for r in results if r["result"]["success"]),
            "failure_count": sum(1 for r in results if not r["result"]["success"]),
            "test_results": results
        }
        
        return self.results
    
    def generate_test_cases(self):
        """Generate test cases from the protocol definition."""
        test_cases = []
        
        # Generate test cases for each state
        for state in self.protocol_def["states"]:
            test_cases.append({
                "type": "state_validation",
                "state": state,
                "description": f"Validate state {state}"
            })
        
        # Generate test cases for each transition
        for transition in self.protocol_def["transitions"]:
            test_cases.append({
                "type": "transition_validation",
                "from": transition["from"],
                "event": transition["event"],
                "to": transition["to"],
                "description": f"Validate transition {transition['from']} + {transition['event']} -> {transition['to']}"
            })
        
        # Generate test cases for decision points
        for decision in self.protocol_def["decision_points"]:
            test_cases.append({
                "type": "decision_validation",
                "decision": decision,
                "description": f"Validate decision point {decision}"
            })
        
        # Generate test cases for fallback modes
        for fallback in self.protocol_def.get("fallback_modes", []):
            test_cases.append({
                "type": "fallback_validation",
                "fallback": fallback,
                "description": f"Validate fallback mode {fallback}"
            })
        
        return test_cases
    
    def run_test_case(self, test_case, implementation=None):
        """Run a single test case."""
        test_type = test_case["type"]
        
        # This implementation is a placeholder that should be expanded
        # based on the actual protocol verification needs
        if test_type == "state_validation":
            return self._validate_state(test_case, implementation)
        elif test_type == "transition_validation":
            return self._validate_transition(test_case, implementation)
        elif test_type == "decision_validation":
            return self._validate_decision(test_case, implementation)
        elif test_type == "fallback_validation":
            return self._validate_fallback(test_case, implementation)
        else:
            return {
                "success": False,
                "error": f"Unknown test case type: {test_type}"
            }
    
    def _validate_state(self, test_case, implementation):
        """Validate a state test case."""
        # This is a placeholder implementation
        return {
            "success": True,
            "details": f"State {test_case['state']} validation not implemented"
        }
    
    def _validate_transition(self, test_case, implementation):
        """Validate a transition test case."""
        # This is a placeholder implementation
        return {
            "success": True,
            "details": f"Transition {test_case['from']} + {test_case['event']} -> {test_case['to']} validation not implemented"
        }
    
    def _validate_decision(self, test_case, implementation):
        """Validate a decision point test case."""
        # This is a placeholder implementation
        return {
            "success": True,
            "details": f"Decision point {test_case['decision']} validation not implemented"
        }
    
    def _validate_fallback(self, test_case, implementation):
        """Validate a fallback mode test case."""
        # This is a placeholder implementation
        return {
            "success": True,
            "details": f"Fallback mode {test_case['fallback']} validation not implemented"
        }
    
    def generate_report(self, output_format="markdown"):
        """Generate a report of validation results."""
        if not self.results:
            return "No validation results available"
            
        if output_format == "json":
            return json.dumps(self.results, indent=2)
        elif output_format == "markdown":
            return self._generate_markdown_report()
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
    
    def _generate_markdown_report(self):
        """Generate a markdown report of validation results."""
        report = []
        report.append(f"# Protocol Validation Report: {self.protocol_name}")
        report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Implementation: {self.results['implementation']}")
        report.append("")
        
        report.append("## Summary")
        report.append(f"- Total tests: {self.results['test_count']}")
        report.append(f"- Successful tests: {self.results['success_count']}")
        report.append(f"- Failed tests: {self.results['failure_count']}")
        report.append(f"- Success rate: {self.results['success_count'] / self.results['test_count'] * 100:.2f}%")
        report.append("")
        
        report.append("## Test Results")
        
        # Group results by test type
        test_types = {}
        for result in self.results["test_results"]:
            test_type = result["test_case"]["type"]
            if test_type not in test_types:
                test_types[test_type] = []
            test_types[test_type].append(result)
        
        for test_type, results in test_types.items():
            report.append(f"### {test_type.replace('_', ' ').title()}")
            report.append(f"- Total: {len(results)}")
            report.append(f"- Successful: {sum(1 for r in results if r['result']['success'])}")
            report.append(f"- Failed: {sum(1 for r in results if not r['result']['success'])}")
            report.append("")
            
            report.append("| Test | Result | Details |")
            report.append("|------|--------|---------|")
            
            for result in results:
                test_case = result["test_case"]
                test_result = result["result"]
                description = test_case["description"]
                status = "✅ Pass" if test_result["success"] else "❌ Fail"
                details = test_result.get("details", "") or test_result.get("error", "")
                report.append(f"| {description} | {status} | {details} |")
            
            report.append("")
        
        return "\n".join(report)

def validate_protocol(protocol_name, implementation=None, logger=None):
    """
    Validate a protocol implementation.
    
    Args:
        protocol_name (str): Name of the protocol to validate
        implementation (object, optional): Implementation to validate
        logger (logging.Logger, optional): Logger to use
    
    Returns:
        dict: Validation results
    """
    validator = ProtocolValidator(protocol_name, logger=logger)
    results = validator.validate_implementation(implementation)
    return results 