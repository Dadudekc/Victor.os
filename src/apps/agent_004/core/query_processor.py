"""
Query processing and context management for Agent-4.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone, timedelta
from .metrics import QueryMetrics
from .query_validator import QueryValidator
import time

logger = logging.getLogger(__name__)

class QueryProcessor:
    """Handles query processing and context management."""
    
    def __init__(self, max_context_age: int = 3600):
        """Initialize the query processor.
        
        Args:
            max_context_age: Maximum age of context entries in seconds (default: 1 hour)
        """
        self.max_context_age = max_context_age
        self.user_history = {}
        self.context_metadata = {}
        self.metrics = QueryMetrics()
        self.validator = QueryValidator()
        self.query_handlers = {
            'information': self._handle_information_query,
            'action': self._handle_action_query,
            'status': self._handle_status_query,
            'general': self._handle_general_query
        }
        self.operational_cycles = 0
        self.last_deviation = None
        
    async def process_query(self, query: str, user_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a user query.
        
        Args:
            query: The query to process
            user_id: The ID of the user
            context: Optional context data
            
        Returns:
            The response for the query
        """
        start_time = time.time()
        try:
            # Classify query type
            query_type = self._classify_query_type(query, context)
            
            # Get appropriate handler
            handler = self.query_handlers.get(query_type, self._handle_general_query)
            
            # Process query
            response = await handler(query, user_id, context)
            
            # Increment operational cycles
            self.operational_cycles += 1
            
            # Record metrics
            response_time = time.time() - start_time
            self.metrics.record_query(
                query=query,
                query_type=query_type,
                response_time=response_time,
                context_used=context is not None,
                error=response.get("error")
            )
            
            return response
            
        except Exception as e:
            self._handle_deviation(e, "Query processing error")
            response_time = time.time() - start_time
            self.metrics.record_query(
                query=query,
                query_type="error",
                response_time=response_time,
                error=str(e)
            )
            return self._create_error_response(str(e))
            
    def _classify_query_type(self, query: str, context: dict) -> str:
        """
        Classify the type of query based on content and context.
        
        Args:
            query: The query string to classify
            context: Context information for classification
            
        Returns:
            str: Query type ('information', 'action', 'status', or 'general')
        """
        query = query.lower().strip()
        
        # Check for status queries
        status_keywords = ['status', 'state', 'condition', 'health', 'running', 'active']
        if any(keyword in query for keyword in status_keywords):
            return 'status'
            
        # Check for action queries
        action_keywords = ['start', 'stop', 'restart', 'run', 'execute', 'perform', 'do']
        if any(keyword in query for keyword in action_keywords):
            return 'action'
            
        # Check for information queries
        info_keywords = ['what', 'how', 'why', 'when', 'where', 'who', 'which', 'tell me about']
        if any(keyword in query for keyword in info_keywords):
            return 'information'
            
        # Default to general query
        return 'general'

    def _handle_deviation(self, error: Exception, context: str):
        """
        Handle operational deviations according to protocol.
        
        Args:
            error: The error that caused the deviation
            context: Context information about the deviation
        """
        # Log deviation
        self.last_deviation = {
            'timestamp': datetime.now().isoformat(),
            'error': str(error),
            'context': context,
            'cycles': self.operational_cycles
        }
        
        # Reset cycle count
        self.operational_cycles = 0
        
        # Log to system diagnostics
        logger.error(f"Operational deviation: {context}", exc_info=error)

    def _create_error_response(self, error_message: str) -> dict:
        """
        Create a standardized error response.
        
        Args:
            error_message: The error message to include
            
        Returns:
            dict: Error response object
        """
        return {
            'status': 'error',
            'type': 'error_response',
            'data': {
                'error': error_message,
                'timestamp': datetime.now().isoformat()
            }
        }
        
    def _determine_query_type(self, query: str) -> str:
        """Determine the type of query.
        
        Args:
            query: The query to analyze
            
        Returns:
            The determined query type
        """
        query = query.lower()
        
        if any(word in query for word in ["help", "how", "what", "why", "when", "where"]):
            return "information"
        elif any(word in query for word in ["do", "make", "create", "generate"]):
            return "action"
        elif any(word in query for word in ["status", "check", "verify"]):
            return "status"
        else:
            return "general"
            
    async def _handle_query_type(self, query_type: str, query: str, user_id: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle a query based on its type.
        
        Args:
            query_type: The type of query
            query: The query to handle
            user_id: The ID of the user
            context: Optional context data
            
        Returns:
            The response for the query
        """
        if query_type == "information":
            return await self._handle_information_query(query, user_id, context)
        elif query_type == "action":
            return await self._handle_action_query(query, user_id, context)
        elif query_type == "status":
            return await self._handle_status_query(query, user_id, context)
        else:
            return await self._handle_general_query(query, user_id, context)
            
    async def _handle_information_query(self, query: str, user_id: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle information-seeking queries.
        
        Args:
            query: The query to handle
            user_id: The ID of the user
            context: Optional context data
            
        Returns:
            The response for the query
        """
        try:
            # Extract key topics and entities
            topics = self._extract_topics(query)
            
            # Check context for relevant information
            context_info = self._get_context_info(topics, context) if context else {}
            
            # Get user history for context
            user_history = self.get_user_history(user_id)
            recent_queries = [entry["query"] for entry in user_history[-5:]] if user_history else []
            
            # Build response with context integration
            response = {
                "status": "success",
                "type": "information",
                "data": {
                    "query": query,
                    "topics": topics,
                    "context_info": context_info,
                    "recent_queries": recent_queries,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            # Add suggestions if available
            suggestions = self._generate_suggestions(topics, context_info, recent_queries)
            if suggestions:
                response["data"]["suggestions"] = suggestions
            
            return response
            
        except Exception as e:
            logger.error(f"Error handling information query: {str(e)}")
            return self._create_error_response("information_query_error", str(e))
            
    def _extract_topics(self, query: str) -> List[str]:
        """Extract key topics from a query.
        
        Args:
            query: The query to analyze
            
        Returns:
            List of extracted topics
        """
        # Convert to lowercase and split
        words = query.lower().split()
        
        # Remove common stop words
        stop_words = {"what", "how", "why", "when", "where", "who", "which", "is", "are", "was", "were", "the", "a", "an", "in", "on", "at", "to", "for", "with", "by", "about", "like", "through", "over", "before", "between", "after", "since", "without", "under", "within", "along", "following", "across", "behind", "beyond", "plus", "except", "but", "up", "down", "from", "of", "and", "or", "if", "then", "else", "when"}
        
        # Extract meaningful words
        topics = [word for word in words if word not in stop_words and len(word) > 2]
        
        # Group related words
        related_words = []
        for i, word in enumerate(topics):
            if i > 0 and len(word) > 3 and word[:3] == topics[i-1][:3]:
                related_words.append(word)
            else:
                related_words.append(word)
        
        return related_words
        
    def _get_context_info(self, topics: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """Get relevant information from context based on topics.
        
        Args:
            topics: List of topics to look for
            context: Context data to search
            
        Returns:
            Dictionary of relevant context information
        """
        relevant_info = {}
        
        # Search for exact matches
        for topic in topics:
            if topic in context:
                relevant_info[topic] = context[topic]
                
        # Search for partial matches
        for key, value in context.items():
            if any(topic in key.lower() for topic in topics):
                relevant_info[key] = value
                
        # Search nested dictionaries
        def search_nested(d: Dict, topics: List[str], path: str = "") -> Dict:
            results = {}
            for k, v in d.items():
                current_path = f"{path}.{k}" if path else k
                if isinstance(v, dict):
                    nested_results = search_nested(v, topics, current_path)
                    results.update(nested_results)
                elif any(topic in str(k).lower() or topic in str(v).lower() for topic in topics):
                    results[current_path] = v
            return results
            
        nested_info = search_nested(context, topics)
        relevant_info.update(nested_info)
        
        return relevant_info
        
    def _generate_suggestions(self, topics: List[str], context_info: Dict[str, Any], recent_queries: List[str]) -> List[str]:
        """Generate relevant suggestions based on topics and context.
        
        Args:
            topics: List of topics from the query
            context_info: Relevant context information
            recent_queries: Recent queries from user history
            
        Returns:
            List of suggested queries
        """
        suggestions = []
        
        # Generate suggestions based on topics
        for topic in topics:
            if topic in context_info:
                suggestions.append(f"What is the status of {topic}?")
                suggestions.append(f"How does {topic} work?")
                suggestions.append(f"Tell me more about {topic}")
                
        # Generate suggestions based on context
        for key, value in context_info.items():
            if isinstance(value, dict) and "status" in value:
                suggestions.append(f"What is the current status of {key}?")
            if isinstance(value, dict) and "type" in value:
                suggestions.append(f"What are the features of {key}?")
                
        # Generate suggestions based on recent queries
        if recent_queries:
            last_query = recent_queries[-1]
            if "status" in last_query.lower():
                suggestions.append("What are the recent changes?")
                suggestions.append("What are the next steps?")
            elif "how" in last_query.lower():
                suggestions.append("What are the prerequisites?")
                suggestions.append("What are the alternatives?")
                
        return list(set(suggestions))[:5]  # Return up to 5 unique suggestions

    async def _handle_action_query(self, query: str, user_id: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle action-oriented queries.
        
        Args:
            query: The query to handle
            user_id: The ID of the user
            context: Optional context data
            
        Returns:
            The response for the query
        """
        try:
            # Extract action and parameters
            action, params = self._extract_action_params(query)
            
            # Validate action against allowed actions
            if not self._is_valid_action(action):
                return self._create_error_response("invalid_action", f"Action '{action}' not recognized")
            
            # Check context for action prerequisites
            prerequisites = self._check_action_prerequisites(action, context) if context else {}
            
            # Get user history for context
            user_history = self.get_user_history(user_id)
            recent_actions = [entry for entry in user_history[-5:] if entry.get("type") == "action"] if user_history else []
            
            # Build response with action details
            response = {
                "status": "success",
                "type": "action",
                "data": {
                    "query": query,
                    "action": action,
                    "parameters": params,
                    "prerequisites": prerequisites,
                    "recent_actions": recent_actions,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            # Add suggestions if available
            suggestions = self._generate_action_suggestions(action, params, prerequisites, recent_actions)
            if suggestions:
                response["data"]["suggestions"] = suggestions
            
            return response
            
        except Exception as e:
            logger.error(f"Error handling action query: {str(e)}")
            return self._create_error_response("action_query_error", str(e))
            
    def _extract_action_params(self, query: str) -> Tuple[str, Dict[str, Any]]:
        """Extract action and parameters from query.
        
        Args:
            query: The query to analyze
            
        Returns:
            Tuple of (action, parameters)
        """
        # Convert to lowercase and split
        words = query.lower().split()
        
        # Extract action (first word)
        action = words[0] if words else ""
        
        # Extract target (second word)
        target = words[1] if len(words) > 1 else None
        
        # Extract options (words after target)
        options = words[2:] if len(words) > 2 else []
        
        # Build parameters
        params = {
            "raw_query": query,
            "target": target,
            "options": options,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return action, params
        
    def _is_valid_action(self, action: str) -> bool:
        """Check if action is valid.
        
        Args:
            action: The action to validate
            
        Returns:
            True if action is valid, False otherwise
        """
        # Define allowed actions
        allowed_actions = {
            "start": ["monitoring", "logging", "system"],
            "stop": ["monitoring", "logging", "system"],
            "restart": ["monitoring", "logging", "system"],
            "check": ["status", "health", "logs"],
            "get": ["status", "logs", "metrics"],
            "set": ["config", "option", "parameter"],
            "update": ["config", "status", "data"],
            "delete": ["log", "data", "config"]
        }
        
        return action in allowed_actions
        
    def _check_action_prerequisites(self, action: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Check prerequisites for an action.
        
        Args:
            action: The action to check
            context: Context data to check against
            
        Returns:
            Dictionary of prerequisite checks
        """
        prerequisites = {
            "status": "unknown",
            "checks": [],
            "warnings": []
        }
        
        # Check system status
        if "system" in context and "status" in context["system"]:
            system_status = context["system"]["status"]
            prerequisites["status"] = system_status
            
            # Add status-based checks
            if action in ["start", "restart"] and system_status == "active":
                prerequisites["warnings"].append(f"System is already {system_status}")
            elif action in ["stop"] and system_status == "inactive":
                prerequisites["warnings"].append(f"System is already {system_status}")
                
        # Check component status
        if "components" in context:
            for component, status in context["components"].items():
                if isinstance(status, dict) and "status" in status:
                    prerequisites["checks"].append({
                        "component": component,
                        "status": status["status"],
                        "required": "active" if action in ["start", "restart"] else "inactive"
                    })
                    
        # Check resource availability
        if "resources" in context:
            resources = context["resources"]
            if "cpu" in resources and resources["cpu"] > 90:
                prerequisites["warnings"].append("High CPU usage detected")
            if "memory" in resources and resources["memory"] > 90:
                prerequisites["warnings"].append("High memory usage detected")
                
        return prerequisites
        
    def _generate_action_suggestions(self, action: str, params: Dict[str, Any], prerequisites: Dict[str, Any], recent_actions: List[Dict[str, Any]]) -> List[str]:
        """Generate relevant action suggestions.
        
        Args:
            action: The current action
            params: Action parameters
            prerequisites: Prerequisite checks
            recent_actions: Recent action history
            
        Returns:
            List of suggested actions
        """
        suggestions = []
        
        # Generate suggestions based on action
        if action in ["start", "stop"]:
            suggestions.append(f"check status of {params.get('target', 'system')}")
            suggestions.append(f"get logs for {params.get('target', 'system')}")
            
        # Generate suggestions based on prerequisites
        if prerequisites["warnings"]:
            suggestions.append("check system resources")
            suggestions.append("verify component status")
            
        # Generate suggestions based on recent actions
        if recent_actions:
            last_action = recent_actions[-1]
            if last_action["action"] == "start":
                suggestions.append("check if service is running")
                suggestions.append("verify logs for errors")
            elif last_action["action"] == "stop":
                suggestions.append("verify service is stopped")
                suggestions.append("check for cleanup tasks")
                
        return list(set(suggestions))[:5]  # Return up to 5 unique suggestions

    async def _handle_status_query(self, query: str, user_id: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle status-oriented queries.
        
        Args:
            query: The query to handle
            user_id: The ID of the user
            context: Optional context data
            
        Returns:
            The response for the query
        """
        try:
            # Extract status target
            target = self._extract_status_target(query)
            
            # Get status information
            status_info = self._get_status_info(target, context) if context else {}
            
            # Get user history for context
            user_history = self.get_user_history(user_id)
            recent_status_checks = [entry for entry in user_history[-5:] if entry.get("type") == "status"] if user_history else []
            
            # Build response with status details
            response = {
                "status": "success",
                "type": "status",
                "data": {
                    "query": query,
                    "target": target,
                    "status_info": status_info,
                    "recent_checks": recent_status_checks,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            # Add suggestions if available
            suggestions = self._generate_status_suggestions(target, status_info, recent_status_checks)
            if suggestions:
                response["data"]["suggestions"] = suggestions
            
            return response
            
        except Exception as e:
            logger.error(f"Error handling status query: {str(e)}")
            return self._create_error_response("status_query_error", str(e))
            
    def _extract_status_target(self, query: str) -> str:
        """Extract status target from query.
        
        Args:
            query: The query to analyze
            
        Returns:
            The extracted status target
        """
        # Convert to lowercase and split
        words = query.lower().split()
        
        # Look for status-related keywords
        status_keywords = ["status", "state", "condition", "health"]
        target_keywords = ["system", "monitoring", "logging", "service", "component"]
        
        # Find the target word after a status keyword
        for i, word in enumerate(words):
            if word in status_keywords and i + 1 < len(words):
                next_word = words[i + 1]
                if next_word in target_keywords:
                    return next_word
                    
        # If no specific target found, return "system" as default
        return "system"
        
    def _get_status_info(self, target: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get status information for a target.
        
        Args:
            target: The target to get status for
            context: Context data to check
            
        Returns:
            Dictionary of status information
        """
        status_info = {
            "target": target,
            "status": "unknown",
            "components": [],
            "metrics": {},
            "warnings": [],
            "last_updated": datetime.utcnow().isoformat()
        }
        
        # Check system status
        if target == "system" and "system" in context:
            system = context["system"]
            if "status" in system:
                status_info["status"] = system["status"]
                
            # Add component statuses
            if "components" in system:
                for component, info in system["components"].items():
                    if isinstance(info, dict) and "status" in info:
                        status_info["components"].append({
                            "name": component,
                            "status": info["status"]
                        })
                        
            # Add resource metrics
            if "resources" in system:
                status_info["metrics"] = system["resources"]
                
        # Check specific component status
        elif target in context.get("components", {}):
            component = context["components"][target]
            if isinstance(component, dict):
                if "status" in component:
                    status_info["status"] = component["status"]
                if "metrics" in component:
                    status_info["metrics"] = component["metrics"]
                    
        # Add warnings based on status
        if status_info["status"] == "error":
            status_info["warnings"].append(f"{target} is in error state")
        elif status_info["status"] == "warning":
            status_info["warnings"].append(f"{target} has warnings")
            
        # Add resource warnings
        if "metrics" in status_info:
            metrics = status_info["metrics"]
            if "cpu" in metrics and metrics["cpu"] > 90:
                status_info["warnings"].append("High CPU usage")
            if "memory" in metrics and metrics["memory"] > 90:
                status_info["warnings"].append("High memory usage")
                
        return status_info
        
    def _generate_status_suggestions(self, target: str, status_info: Dict[str, Any], recent_checks: List[Dict[str, Any]]) -> List[str]:
        """Generate relevant status suggestions.
        
        Args:
            target: The status target
            status_info: Status information
            recent_checks: Recent status checks
            
        Returns:
            List of suggested actions
        """
        suggestions = []
        
        # Generate suggestions based on status
        if status_info["status"] == "error":
            suggestions.append(f"check {target} logs for errors")
            suggestions.append(f"restart {target}")
        elif status_info["status"] == "warning":
            suggestions.append(f"check {target} configuration")
            suggestions.append(f"monitor {target} metrics")
            
        # Generate suggestions based on warnings
        for warning in status_info["warnings"]:
            if "CPU" in warning:
                suggestions.append("check CPU-intensive processes")
                suggestions.append("optimize resource usage")
            elif "memory" in warning:
                suggestions.append("check memory leaks")
                suggestions.append("optimize memory usage")
                
        # Generate suggestions based on recent checks
        if recent_checks:
            last_check = recent_checks[-1]
            if last_check.get("target") == target:
                suggestions.append(f"compare with previous {target} status")
                suggestions.append("check for status changes")
                
        return list(set(suggestions))[:5]  # Return up to 5 unique suggestions

    async def _handle_general_query(self, query: str, user_id: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle general queries.
        
        Args:
            query: The query to handle
            user_id: The ID of the user
            context: Optional context data
            
        Returns:
            The response for the query
        """
        try:
            # Extract general intent
            intent = self._extract_general_intent(query)
            
            # Get relevant context
            relevant_context = self._get_relevant_context(intent, context) if context else {}
            
            # Get user history for context
            user_history = self.get_user_history(user_id)
            recent_queries = [entry for entry in user_history[-5:]] if user_history else []
            
            # Build response with intent analysis
            response = {
                "status": "success",
                "type": "general",
                "data": {
                    "query": query,
                    "intent": intent,
                    "context": relevant_context,
                    "recent_queries": recent_queries,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            # Add suggestions if available
            suggestions = self._generate_general_suggestions(intent, relevant_context, recent_queries)
            if suggestions:
                response["data"]["suggestions"] = suggestions
            
            return response
            
        except Exception as e:
            logger.error(f"Error handling general query: {str(e)}")
            return self._create_error_response("general_query_error", str(e))
            
    def _extract_general_intent(self, query: str) -> str:
        """Extract general intent from query.
        
        Args:
            query: The query to analyze
            
        Returns:
            The extracted intent
        """
        # Convert to lowercase
        query = query.lower()
        
        # Define intent patterns
        intent_patterns = {
            "system_inquiry": [
                "how does", "how do", "what is", "what are",
                "explain", "describe", "tell me about"
            ],
            "help_request": [
                "help", "how to", "how can i", "what should i",
                "guide", "tutorial", "instructions"
            ],
            "configuration_inquiry": [
                "configure", "setup", "settings", "options",
                "parameters", "config", "configuration"
            ],
            "troubleshooting": [
                "error", "issue", "problem", "not working",
                "failed", "broken", "trouble", "fix"
            ],
            "performance_inquiry": [
                "performance", "speed", "slow", "fast",
                "optimize", "efficient", "resource"
            ]
        }
        
        # Check for intent patterns
        for intent, patterns in intent_patterns.items():
            if any(pattern in query for pattern in patterns):
                return intent
                
        # Default to general inquiry if no specific intent found
        return "general_inquiry"
        
    def _get_relevant_context(self, intent: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get relevant context based on intent.
        
        Args:
            intent: The query intent
            context: Full context data
            
        Returns:
            Dictionary of relevant context
        """
        relevant_context = {
            "intent": intent,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Add context based on intent
        if intent == "system_inquiry":
            if "system" in context:
                relevant_context["system"] = {
                    "description": context["system"].get("description", ""),
                    "components": context["system"].get("components", {}),
                    "features": context["system"].get("features", [])
                }
                
        elif intent == "help_request":
            if "help" in context:
                relevant_context["help"] = {
                    "guides": context["help"].get("guides", []),
                    "faq": context["help"].get("faq", []),
                    "tutorials": context["help"].get("tutorials", [])
                }
                
        elif intent == "configuration_inquiry":
            if "config" in context:
                relevant_context["config"] = {
                    "settings": context["config"].get("settings", {}),
                    "options": context["config"].get("options", {}),
                    "parameters": context["config"].get("parameters", {})
                }
                
        elif intent == "troubleshooting":
            if "system" in context:
                relevant_context["system"] = {
                    "status": context["system"].get("status", ""),
                    "errors": context["system"].get("errors", []),
                    "warnings": context["system"].get("warnings", [])
                }
                
        elif intent == "performance_inquiry":
            if "system" in context:
                relevant_context["system"] = {
                    "metrics": context["system"].get("metrics", {}),
                    "resources": context["system"].get("resources", {}),
                    "performance": context["system"].get("performance", {})
                }
                
        return relevant_context
        
    def _generate_general_suggestions(self, intent: str, context: Dict[str, Any], recent_queries: List[Dict[str, Any]]) -> List[str]:
        """Generate relevant general suggestions.
        
        Args:
            intent: The query intent
            context: Relevant context data
            recent_queries: Recent query history
            
        Returns:
            List of suggested actions
        """
        suggestions = []
        
        # Generate suggestions based on intent
        if intent == "system_inquiry":
            if "system" in context and "components" in context["system"]:
                for component in context["system"]["components"]:
                    suggestions.append(f"learn more about {component}")
            suggestions.append("check system documentation")
            suggestions.append("view system architecture")
            
        elif intent == "help_request":
            if "help" in context:
                if "guides" in context["help"]:
                    suggestions.append("browse help guides")
                if "faq" in context["help"]:
                    suggestions.append("check frequently asked questions")
                if "tutorials" in context["help"]:
                    suggestions.append("view tutorials")
                    
        elif intent == "configuration_inquiry":
            if "config" in context:
                if "settings" in context["config"]:
                    suggestions.append("view current settings")
                if "options" in context["config"]:
                    suggestions.append("explore configuration options")
                    
        elif intent == "troubleshooting":
            if "system" in context:
                if "errors" in context["system"]:
                    suggestions.append("check error logs")
                if "warnings" in context["system"]:
                    suggestions.append("review system warnings")
            suggestions.append("run system diagnostics")
            
        elif intent == "performance_inquiry":
            if "system" in context:
                if "metrics" in context["system"]:
                    suggestions.append("view detailed metrics")
                if "resources" in context["system"]:
                    suggestions.append("check resource usage")
            suggestions.append("run performance analysis")
            
        # Generate suggestions based on recent queries
        if recent_queries:
            last_query = recent_queries[-1]
            if last_query.get("type") == "status":
                suggestions.append("check current status")
            elif last_query.get("type") == "action":
                suggestions.append("verify action results")
                
        return list(set(suggestions))[:5]  # Return up to 5 unique suggestions

    def cleanup_old_contexts(self):
        """Clean up old context entries."""
        current_time = datetime.now(timezone.utc)
        
        # Clean up query history
        for user_id in list(self.user_history.keys()):
            self.user_history[user_id] = [
                entry for entry in self.user_history[user_id]
                if (current_time - datetime.fromisoformat(entry["timestamp"])) < timedelta(seconds=self.max_context_age)
            ]
            
            # Remove user if no history remains
            if not self.user_history[user_id]:
                del self.user_history[user_id]
                
        # Clean up context metadata
        for user_id in list(self.context_metadata.keys()):
            if (current_time - datetime.fromisoformat(self.context_metadata[user_id]["last_updated"])) > timedelta(seconds=self.max_context_age):
                del self.context_metadata[user_id]
                
    def get_user_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Get query history for a user.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            List of query history entries
        """
        return self.user_history.get(user_id, [])
        
    def get_context_metadata(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get context metadata for a user.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            Context metadata if available
        """
        return self.context_metadata.get(user_id) 