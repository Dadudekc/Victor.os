"""
Agent Resume Manager

Handles agent coordination and message processing.
"""

import json
import logging
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from queue import Queue
import threading
try:
    import pyautogui  # type: ignore
except Exception:  # pragma: no cover - optional dependency may not be available
    pyautogui = None

try:
    import pyperclip  # type: ignore
except Exception:  # pragma: no cover - optional dependency may not be available
    pyperclip = None

try:
    from PIL import ImageChops, Image  # type: ignore
except Exception:  # pragma: no cover - optional dependency may not be available
    ImageChops, Image = None, None

try:
    import pygetwindow as gw  # type: ignore
except Exception:  # pragma: no cover - optional dependency may not be available
    gw = None
import hashlib
import os
import re
import gzip
import shutil
import schedule

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('agent_resume')

class AgentResume:
    def __init__(self, agent_id: str, headless: bool = False):
        self.agent_id = agent_id
        self.headless = headless
        self.state = self._load_state()
        self.last_cycle = time.time()
        
    def _load_state(self) -> Dict[str, Any]:
        """Load agent state from status.json"""
        status_path = Path(f"runtime/agent_comms/agent_mailboxes/{self.agent_id}/status.json")
        if status_path.exists():
            with open(status_path) as f:
                return json.load(f)
        return {
            "agent_id": self.agent_id,
            "status": "INITIALIZING",
            "current_task": None,
            "task_status": None,
            "last_updated": None,
            "tasks_completed": 0,
            "tasks_total": 0,
            "message_count": 0,
            "messages": {"total": 0, "unread": 0}
        }
    
    def run_cycle(self) -> Optional[Dict[str, Any]]:
        """Run one cycle of the agent loop"""
        try:
            # Skip GUI operations in headless mode
            if not self.headless:
                # GUI operations would go here
                pass
                
            # Process inbox
            inbox_path = Path(f"runtime/agent_comms/agent_mailboxes/{self.agent_id}/inbox")
            if inbox_path.exists():
                messages = [f for f in inbox_path.iterdir() if f.is_file() and f.name != ".keep"]
                self.state["message_count"] = len(messages)
                self.state["messages"]["total"] = len(messages)
                self.state["messages"]["unread"] = len([m for m in messages if m.stat().st_mtime > self.last_cycle])
            
            # Update state
            self.state["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            self._save_state()
            
            self.last_cycle = time.time()
            return self.state
            
        except Exception as e:
            print(f"Error in agent cycle: {e}")
            return None
    
    def _save_state(self):
        """Save current state to status.json"""
        status_path = Path(f"runtime/agent_comms/agent_mailboxes/{self.agent_id}/status.json")
        with open(status_path, 'w') as f:
            json.dump(self.state, f, indent=2)
        
    def start_queue_processor(self):
        """Start the queue processing thread."""
        self.queue_thread = threading.Thread(target=self._process_queue_loop)
        self.queue_thread.daemon = True
        self.queue_thread.start()
        
    def stop_queue_processor(self):
        """Stop the queue processing thread."""
        if hasattr(self, 'queue_thread'):
            self.queue_thread.join(timeout=5)
            
    def _process_queue_loop(self):
        """Process messages in the queue."""
        while True:
            try:
                # Process high priority messages first
                self._process_priority_queue('high')
                
                # Then medium priority
                self._process_priority_queue('medium')
                
                # Finally low priority
                self._process_priority_queue('low')
                
                time.sleep(1)  # Prevent CPU spinning
                
            except Exception as e:
                logger.error(f"Error in queue processing loop: {e}")
                time.sleep(5)  # Back off on error
                
    def _process_priority_queue(self, priority: str):
        """Process messages in a specific priority queue."""
        while True:
            message = self.queue_manager.get_next_message(priority)
            if not message:
                break
                
            try:
                if message.get('type') == 'task':
                    self._process_task_message(message)
                elif message.get('type') == 'coordination':
                    self._process_coordination_message(message)
                else:
                    logger.warning(f"Unknown message type: {message.get('type')}")
                    
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                
    def _process_task_message(self, message: dict):
        """Process a task message."""
        try:
            task_id = message.get('task_id')
            agent_id = message.get('agent_id')
            action = message.get('action')
            
            if action == 'assign':
                self.assign_task(task_id, agent_id)
            elif action == 'update':
                self.update_task_status(
                    task_id,
                    message.get('status'),
                    agent_id,
                    message.get('details')
                )
            else:
                logger.warning(f"Unknown task action: {action}")
                
        except Exception as e:
            logger.error(f"Error processing task message: {e}")
            
    def _process_coordination_message(self, message: dict):
        """Process a coordination message."""
        try:
            sender = message.get('sender')
            content = message.get('content')
            
            # Update coordination structure
            self.update_coordination_structure()
            
            # Process message based on type
            if message.get('subtype') == 'health':
                self.process_health_update(message)
            elif message.get('subtype') == 'infrastructure':
                self.process_infrastructure_ping(message)
            else:
                logger.warning(f"Unknown coordination subtype: {message.get('subtype')}")
                
        except Exception as e:
            logger.error(f"Error processing coordination message: {e}")
            
    def update_coordination_structure(self):
        """Update the coordination structure."""
        try:
            # Update agent roles and relationships
            # Update task assignments
            # Update resource allocation
            # Update system initialization
            pass
            
        except Exception as e:
            logger.error(f"Error updating coordination structure: {e}")
            
    def get_queue_status(self) -> Dict:
        """Get the current status of all queues."""
        try:
            return {
                'high': len(self.queue_manager.queue['high']),
                'medium': len(self.queue_manager.queue['medium']),
                'low': len(self.queue_manager.queue['low'])
            }
        except Exception as e:
            logger.error(f"Error getting queue status: {e}")
            return {'high': 0, 'medium': 0, 'low': 0}
            
    def send_message(self, recipient: str, message_type: str, content: dict, priority: int = 1):
        """Send a message to an agent."""
        try:
            message = {
                'type': message_type,
                'content': content,
                'timestamp': datetime.now().isoformat(),
                'sender': 'system'
            }
            
            # Determine priority queue
            queue = 'high' if priority == 1 else ('medium' if priority == 2 else 'low')
            
            # Add to queue
            self.queue_manager.add_message(queue, message)
            
            logger.info(f"Added message to {queue} queue for {recipient}")
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            
    def process_system_health_update(self, health_data: dict):
        """Process a system health update."""
        try:
            # Update infrastructure
            self._handle_infrastructure_update(health_data)
            
            # Update health monitoring
            self._handle_health_monitoring(health_data)
            
            # Update performance
            self._handle_performance_update(health_data)
            
            # Check for critical issues
            if self._check_critical_health(health_data.get('system_health', {}), 
                                         health_data.get('resource_usage', {})):
                self._send_health_alert(health_data.get('system_health', {}),
                                      health_data.get('resource_usage', {}))
                
            # Check for performance issues
            if self._check_performance_issues(health_data.get('resource_usage', {})):
                self._send_performance_alert(health_data.get('resource_usage', {}))
                
            # Update metrics
            self._update_health_metrics(health_data.get('system_health', {}),
                                      health_data.get('resource_usage', {}))
            self._update_performance_metrics(health_data.get('resource_usage', {}))
            
        except Exception as e:
            logger.error(f"Error processing system health update: {e}")
            
    def process_health_update(self, message_data: dict):
        """Process a health update message."""
        try:
            health_data = message_data.get('content', {})
            
            # Process system health
            self.process_system_health_update(health_data)
            
            # Update monitoring status
            self._update_monitoring_status(health_data)
            
            # Notify affected agents
            self._notify_affected_agents(health_data)
            
        except Exception as e:
            logger.error(f"Error processing health update: {e}")
            
    def _handle_infrastructure_update(self, health_data: dict):
        """Handle infrastructure updates."""
        try:
            # Update infrastructure status
            self._update_infrastructure_status(health_data)
            
        except Exception as e:
            logger.error(f"Error handling infrastructure update: {e}")
            
    def _handle_health_monitoring(self, health_data: dict):
        """Handle health monitoring updates."""
        try:
            # Update health metrics
            self._update_health_metrics(health_data.get('system_health', {}),
                                      health_data.get('resource_usage', {}))
            
        except Exception as e:
            logger.error(f"Error handling health monitoring: {e}")
            
    def _handle_performance_update(self, health_data: dict):
        """Handle performance updates."""
        try:
            # Update performance metrics
            self._update_performance_metrics(health_data.get('resource_usage', {}))
            
        except Exception as e:
            logger.error(f"Error handling performance update: {e}")
            
    def _check_critical_health(self, system_health: dict, resource_usage: dict) -> bool:
        """Check for critical health issues."""
        try:
            # Check system health
            if system_health.get('status') == 'critical':
                return True
                
            # Check resource usage
            if resource_usage.get('cpu', 0) > 90 or resource_usage.get('memory', 0) > 90:
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error checking critical health: {e}")
            return False
            
    def _check_performance_issues(self, resource_usage: dict) -> bool:
        """Check for performance issues."""
        try:
            # Check CPU usage
            if resource_usage.get('cpu', 0) > 80:
                return True
                
            # Check memory usage
            if resource_usage.get('memory', 0) > 80:
                return True
                
            # Check disk usage
            if resource_usage.get('disk', 0) > 80:
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error checking performance issues: {e}")
            return False
            
    def _send_health_alert(self, system_health: dict, resource_usage: dict):
        """Send a health alert."""
        try:
            alert = {
                'type': 'health_alert',
                'content': {
                    'system_health': system_health,
                    'resource_usage': resource_usage,
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            # Send to all agents
            for agent_id in self.queue_manager.registry.keys():
                self.send_message(agent_id, 'alert', alert, priority=1)
                
        except Exception as e:
            logger.error(f"Error sending health alert: {e}")
            
    def _send_performance_alert(self, resource_usage: dict):
        """Send a performance alert."""
        try:
            alert = {
                'type': 'performance_alert',
                'content': {
                    'resource_usage': resource_usage,
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            # Send to all agents
            for agent_id in self.queue_manager.registry.keys():
                self.send_message(agent_id, 'alert', alert, priority=2)
                
        except Exception as e:
            logger.error(f"Error sending performance alert: {e}")
            
    def _update_health_metrics(self, system_health: dict, resource_usage: dict):
        """Update health metrics."""
        try:
            # Update metrics in registry
            pass
            
        except Exception as e:
            logger.error(f"Error updating health metrics: {e}")
            
    def _update_performance_metrics(self, resource_usage: dict):
        """Update performance metrics."""
        try:
            # Update metrics in registry
            pass
            
        except Exception as e:
            logger.error(f"Error updating performance metrics: {e}")
            
    def process_infrastructure_ping(self, message_data: dict):
        """Process an infrastructure ping message."""
        try:
            ping_data = message_data.get('content', {})
            
            # Handle infrastructure ping
            self._handle_infrastructure_ping(ping_data)
            
            # Handle infrastructure notification
            self._handle_infrastructure_notification(ping_data)
            
            # Update infrastructure status
            self._update_infrastructure_status(ping_data)
            
        except Exception as e:
            logger.error(f"Error processing infrastructure ping: {e}")
            
    def _handle_infrastructure_ping(self, ping_data: dict):
        """Handle infrastructure ping."""
        try:
            # Process ping data
            pass
            
        except Exception as e:
            logger.error(f"Error handling infrastructure ping: {e}")
            
    def _handle_infrastructure_notification(self, ping_data: dict):
        """Handle infrastructure notification."""
        try:
            # Process notification data
            pass
            
        except Exception as e:
            logger.error(f"Error handling infrastructure notification: {e}")
            
    def _update_infrastructure_status(self, updates: dict):
        """Update infrastructure status."""
        try:
            # Update status in registry
            pass
            
        except Exception as e:
            logger.error(f"Error updating infrastructure status: {e}")
            
    def _notify_affected_agents(self, updates: dict):
        """Notify affected agents of updates."""
        try:
            # Get affected agents
            affected_agents = self._get_affected_agents(updates)
            
            # Send notifications
            for agent_id in affected_agents:
                impact = self._get_update_impact(updates, agent_id)
                self.send_message(
                    agent_id,
                    'notification',
                    {'impact': impact, 'updates': updates},
                    priority=2
                )
                
        except Exception as e:
            logger.error(f"Error notifying affected agents: {e}")
            
    def _get_affected_agents(self, updates: dict) -> List[str]:
        """Get list of agents affected by updates."""
        try:
            affected = []
            
            # Check each agent
            for agent_id in self.queue_manager.registry.keys():
                if self._get_update_impact(updates, agent_id):
                    affected.append(agent_id)
                    
            return affected
            
        except Exception as e:
            logger.error(f"Error getting affected agents: {e}")
            return []
            
    def _get_update_impact(self, updates: dict, agent: str) -> str:
        """Get impact of updates on an agent."""
        try:
            # Check impact on agent
            return 'high' if updates.get('critical') else 'low'
            
        except Exception as e:
            logger.error(f"Error getting update impact: {e}")
            return 'unknown'
            
    def _update_monitoring_status(self, updates: dict):
        """Update monitoring status."""
        try:
            # Update status in registry
            pass
            
        except Exception as e:
            logger.error(f"Error updating monitoring status: {e}")
            
    def process_feedback_loop(self, agent_id: str, feedback_data: dict):
        """Process feedback loop data."""
        try:
            # Get agent role
            role = self._get_agent_role(agent_id)
            
            # Process feedback based on role
            if role == 'captain':
                self._process_captain_feedback(feedback_data)
            elif role == 'infrastructure':
                self._process_infrastructure_feedback(feedback_data)
            elif role == 'testing':
                self._process_testing_feedback(feedback_data)
            elif role == 'development':
                self._process_development_feedback(feedback_data)
            elif role == 'monitoring':
                self._process_monitoring_feedback(feedback_data)
            elif role == 'security':
                self._process_security_feedback(feedback_data)
            elif role == 'integration':
                self._process_integration_feedback(feedback_data)
            elif role == 'performance':
                self._process_performance_feedback(feedback_data)
            else:
                logger.warning(f"Unknown agent role: {role}")
                
        except Exception as e:
            logger.error(f"Error processing feedback loop: {e}")
            
    def _get_agent_role(self, agent_id: str) -> str:
        """Get an agent's role."""
        try:
            # Get role from registry
            return self.queue_manager.registry.get(agent_id, {}).get('role', 'unknown')
            
        except Exception as e:
            logger.error(f"Error getting agent role: {e}")
            return 'unknown'
            
    def _process_captain_feedback(self, feedback_data: dict):
        """Process captain feedback."""
        try:
            # Update system direction
            self._update_system_direction(feedback_data.get('direction', {}))
            
            # Update task assignments
            self._update_task_assignments(feedback_data.get('assignments', {}))
            
            # Resolve conflicts
            self._resolve_conflicts(feedback_data.get('conflicts', {}))
            
        except Exception as e:
            logger.error(f"Error processing captain feedback: {e}")
            
    def _process_infrastructure_feedback(self, feedback_data: dict):
        """Process infrastructure feedback."""
        try:
            # Update infrastructure
            self._update_infrastructure(feedback_data.get('changes', {}))
            
            # Update resource allocation
            self._update_resource_allocation(feedback_data.get('allocation', {}))
            
            # Update system initialization
            self._update_system_initialization(feedback_data.get('init', {}))
            
        except Exception as e:
            logger.error(f"Error processing infrastructure feedback: {e}")
            
    def _process_testing_feedback(self, feedback_data: dict):
        """Process testing feedback."""
        try:
            # Update test results
            self._update_test_results(feedback_data.get('results', {}))
            
            # Update quality metrics
            self._update_quality_metrics(feedback_data.get('metrics', {}))
            
            # Update validation status
            self._update_validation_status(feedback_data.get('status', {}))
            
        except Exception as e:
            logger.error(f"Error processing testing feedback: {e}")
            
    def _process_development_feedback(self, feedback_data: dict):
        """Process development feedback."""
        try:
            # Update code changes
            self._update_code_changes(feedback_data.get('changes', {}))
            
            # Update feature status
            self._update_feature_status(feedback_data.get('features', {}))
            
            # Update bug fixes
            self._update_bug_fixes(feedback_data.get('fixes', {}))
            
        except Exception as e:
            logger.error(f"Error processing development feedback: {e}")
            
    def _process_monitoring_feedback(self, feedback_data: dict):
        """Process monitoring feedback."""
        try:
            # Update system health
            self._update_system_health(feedback_data.get('health', {}))
            
            # Update maintenance status
            self._update_maintenance_status(feedback_data.get('maintenance', {}))
            
        except Exception as e:
            logger.error(f"Error processing monitoring feedback: {e}")
            
    def _process_security_feedback(self, feedback_data: dict):
        """Process security feedback."""
        try:
            # Update security status
            self._update_security_status(feedback_data.get('security', {}))
            
            # Update compliance status
            self._update_compliance_status(feedback_data.get('compliance', {}))
            
            # Update vulnerability reports
            self._update_vulnerability_reports(feedback_data.get('vulnerabilities', {}))
            
        except Exception as e:
            logger.error(f"Error processing security feedback: {e}")
            
    def _process_integration_feedback(self, feedback_data: dict):
        """Process integration feedback."""
        try:
            # Update API status
            self._update_api_status(feedback_data.get('api', {}))
            
            # Update integration status
            self._update_integration_status(feedback_data.get('integration', {}))
            
            # Update interface status
            self._update_interface_status(feedback_data.get('interface', {}))
            
        except Exception as e:
            logger.error(f"Error processing integration feedback: {e}")
            
    def _process_performance_feedback(self, feedback_data: dict):
        """Process performance feedback."""
        try:
            # Update optimization status
            self._update_optimization_status(feedback_data.get('optimization', {}))
            
            # Update resource efficiency
            self._update_resource_efficiency(feedback_data.get('efficiency', {}))
            
            # Update system tuning
            self._update_system_tuning(feedback_data.get('tuning', {}))
            
        except Exception as e:
            logger.error(f"Error processing performance feedback: {e}")
            
    def _update_system_direction(self, direction: dict):
        """Update system direction."""
        try:
            # Update direction in registry
            pass
            
        except Exception as e:
            logger.error(f"Error updating system direction: {e}")
            
    def _update_task_assignments(self, assignments: dict):
        """Update task assignments."""
        try:
            # Update assignments in registry
            pass
            
        except Exception as e:
            logger.error(f"Error updating task assignments: {e}")
            
    def _resolve_conflicts(self, resolution: dict):
        """Resolve conflicts."""
        try:
            # Update conflict resolution in registry
            pass
            
        except Exception as e:
            logger.error(f"Error resolving conflicts: {e}")
            
    def _update_infrastructure(self, changes: dict):
        """Update infrastructure."""
        try:
            # Update infrastructure in registry
            pass
            
        except Exception as e:
            logger.error(f"Error updating infrastructure: {e}")
            
    def _update_resource_allocation(self, allocation: dict):
        """Update resource allocation."""
        try:
            # Update allocation in registry
            pass
            
        except Exception as e:
            logger.error(f"Error updating resource allocation: {e}")
            
    def _update_system_initialization(self, init_data: dict):
        """Update system initialization."""
        try:
            # Update initialization in registry
            pass
            
        except Exception as e:
            logger.error(f"Error updating system initialization: {e}")
            
    def _update_test_results(self, results: dict):
        """Update test results."""
        try:
            # Update results in registry
            pass
            
        except Exception as e:
            logger.error(f"Error updating test results: {e}")
            
    def _update_quality_metrics(self, metrics: dict):
        """Update quality metrics."""
        try:
            # Update metrics in registry
            pass
            
        except Exception as e:
            logger.error(f"Error updating quality metrics: {e}")
            
    def _update_validation_status(self, status: dict):
        """Update validation status."""
        try:
            # Update status in registry
            pass
            
        except Exception as e:
            logger.error(f"Error updating validation status: {e}")
            
    def _update_code_changes(self, changes: dict):
        """Update code changes."""
        try:
            # Update changes in registry
            pass
            
        except Exception as e:
            logger.error(f"Error updating code changes: {e}")
            
    def _update_feature_status(self, status: dict):
        """Update feature status."""
        try:
            # Update status in registry
            pass
            
        except Exception as e:
            logger.error(f"Error updating feature status: {e}")
            
    def _update_bug_fixes(self, fixes: dict):
        """Update bug fixes."""
        try:
            # Update fixes in registry
            pass
            
        except Exception as e:
            logger.error(f"Error updating bug fixes: {e}")
            
    def _update_system_health(self, health: dict):
        """Update system health."""
        try:
            # Update health in registry
            pass
            
        except Exception as e:
            logger.error(f"Error updating system health: {e}")
            
    def _update_maintenance_status(self, status: dict):
        """Update maintenance status."""
        try:
            # Update status in registry
            pass
            
        except Exception as e:
            logger.error(f"Error updating maintenance status: {e}")
            
    def _update_security_status(self, status: dict):
        """Update security status."""
        try:
            # Update status in registry
            pass
            
        except Exception as e:
            logger.error(f"Error updating security status: {e}")
            
    def _update_compliance_status(self, status: dict):
        """Update compliance status."""
        try:
            # Update status in registry
            pass
            
        except Exception as e:
            logger.error(f"Error updating compliance status: {e}")
            
    def _update_vulnerability_reports(self, reports: dict):
        """Update vulnerability reports."""
        try:
            # Update reports in registry
            pass
            
        except Exception as e:
            logger.error(f"Error updating vulnerability reports: {e}")
            
    def _update_api_status(self, status: dict):
        """Update API status."""
        try:
            # Update status in registry
            pass
            
        except Exception as e:
            logger.error(f"Error updating API status: {e}")
            
    def _update_integration_status(self, status: dict):
        """Update integration status."""
        try:
            # Update status in registry
            pass
            
        except Exception as e:
            logger.error(f"Error updating integration status: {e}")
            
    def _update_interface_status(self, status: dict):
        """Update interface status."""
        try:
            # Update status in registry
            pass
            
        except Exception as e:
            logger.error(f"Error updating interface status: {e}")
            
    def _update_optimization_status(self, status: dict):
        """Update optimization status."""
        try:
            # Update status in registry
            pass
            
        except Exception as e:
            logger.error(f"Error updating optimization status: {e}")
            
    def _update_resource_efficiency(self, efficiency: dict):
        """Update resource efficiency."""
        try:
            # Update efficiency in registry
            pass
            
        except Exception as e:
            logger.error(f"Error updating resource efficiency: {e}")
            
    def _update_system_tuning(self, tuning: dict):
        """Update system tuning."""
        try:
            # Update tuning in registry
            pass
            
        except Exception as e:
            logger.error(f"Error updating system tuning: {e}")
            
    def send_cell_phone_message(self, from_agent: str, to_agent: str, message: str, priority: int = 2):
        """Send a cell phone message."""
        try:
            # Format message
            formatted_message = {
                'type': 'cell_phone',
                'content': {
                    'from': from_agent,
                    'to': to_agent,
                    'message': message,
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            # Send message
            self.send_message(to_agent, 'cell_phone', formatted_message, priority)
            
            logger.info(f"Sent cell phone message from {from_agent} to {to_agent}")
            
        except Exception as e:
            logger.error(f"Error sending cell phone message: {e}")
            
    def process_cell_phone_message(self, message: dict):
        """Process a cell phone message."""
        try:
            content = message.get('content', {})
            from_agent = content.get('from')
            to_agent = content.get('to')
            message_text = content.get('message')
            timestamp = content.get('timestamp')
            
            # Deliver message
            self._deliver_cell_phone_message(from_agent, to_agent, message_text, timestamp)
            
            # Process response
            self._process_agent_response(message)
            
        except Exception as e:
            logger.error(f"Error processing cell phone message: {e}")
            
    def _deliver_cell_phone_message(self, from_agent: str, to_agent: str, content: str, timestamp: str):
        """Deliver a cell phone message."""
        try:
            # Format message for delivery
            message = {
                'type': 'cell_phone',
                'content': {
                    'from': from_agent,
                    'to': to_agent,
                    'message': content,
                    'timestamp': timestamp
                }
            }
            
            # Add to queue
            self.queue_manager.add_message('high', message)
            
            logger.info(f"Delivered cell phone message from {from_agent} to {to_agent}")
            
        except Exception as e:
            logger.error(f"Error delivering cell phone message: {e}")
            
    def get_cell_phone_status(self, agent_id: str) -> dict:
        """Get cell phone status for an agent."""
        try:
            # Get status from registry
            status = self.queue_manager.registry.get(agent_id, {})
            
            # Add queue status
            status['queue'] = self.get_queue_status()
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting cell phone status: {e}")
            return {}
            
    def _process_agent_response(self, message: dict):
        """Process an agent response."""
        try:
            content = message.get('content', {})
            agent_id = content.get('from')
            response = content.get('message')
            
            # Validate response
            is_valid, reason = self.response_validator.validate_response(
                agent_id,
                response,
                content.get('timestamp')
            )
            
            if is_valid:
                # Add to history
                self.response_history.add_response(agent_id, response)
            else:
                logger.warning(f"Invalid response from {agent_id}: {reason}")
                
        except Exception as e:
            logger.error(f"Error processing agent response: {e}")
            
    def stop(self):
        """Stop all components."""
        try:
            # Stop queue processor
            self.stop_queue_processor()
            
            # Stop response detector
            self.response_detector.stop_detection()
            
            logger.info("Stopped all components")
            
        except Exception as e:
            logger.error(f"Error stopping components: {e}")
            
    def distribute_task(self, task_data: dict):
        """Distribute a task to agents."""
        try:
            task_id = task_data.get('task_id')
            agents = task_data.get('agents', [])
            priority = task_data.get('priority', 2)
            
            # Send task to each agent
            for agent_id in agents:
                self.assign_task(task_id, agent_id, priority)
                
            logger.info(f"Distributed task {task_id} to {len(agents)} agents")
            
        except Exception as e:
            logger.error(f"Error distributing task: {e}")
            
    def assign_task(self, task_id: str, agent_id: str, priority: int = 1):
        """Assign a task to an agent."""
        try:
            # Format task message
            message = {
                'type': 'task',
                'content': {
                    'task_id': task_id,
                    'agent_id': agent_id,
                    'action': 'assign',
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            # Send message
            self.send_message(agent_id, 'task', message, priority)
            
            logger.info(f"Assigned task {task_id} to {agent_id}")
            
        except Exception as e:
            logger.error(f"Error assigning task: {e}")
            
    def update_task_status(self, task_id: str, status: str, agent_id: str, details: str = None):
        """Update task status."""
        try:
            # Format status message
            message = {
                'type': 'task',
                'content': {
                    'task_id': task_id,
                    'agent_id': agent_id,
                    'action': 'update',
                    'status': status,
                    'details': details,
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            # Send message
            self.send_message(agent_id, 'task', message, priority=2)
            
            logger.info(f"Updated task {task_id} status to {status} for {agent_id}")
            
        except Exception as e:
            logger.error(f"Error updating task status: {e}")
            
def main():
    """Main entry point."""
    try:
        # Create agent resume
        resume = AgentResume("agent_id", True)
        
        # Start queue processor
        resume.start_queue_processor()
        
        # Keep running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Stopping agent resume...")
        resume.stop()
    except Exception as e:
        logger.error(f"Error in main: {e}")
        if 'resume' in locals():
            resume.stop()
            
if __name__ == "__main__":
    main() 