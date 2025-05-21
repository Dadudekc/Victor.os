import re
import logging
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime

logger = logging.getLogger(__name__)

class QueryValidator:
    """Validates and sanitizes user queries."""
    
    def __init__(self):
        """Initialize the query validator."""
        self.max_query_length = 1000
        self.min_query_length = 2
        self.allowed_chars = re.compile(r'^[a-zA-Z0-9\s\.,\?!@#$%^&*()\-_=+\[\]{};:\'"<>/\\]+$')
        self.sensitive_patterns = [
            r'\b(password|secret|key|token)\b',
            r'\b\d{16,19}\b',  # Credit card numbers
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'  # Email addresses
        ]
        
        # Define validation patterns
        self.patterns = {
            "action": re.compile(r'^(start|stop|restart|check|get|set|update|delete)\s+[a-zA-Z0-9_]+', re.IGNORECASE),
            "status": re.compile(r'^(what|how|show|display|get)\s+(is|are|was|were)\s+(the\s+)?(status|state|condition)', re.IGNORECASE),
            "information": re.compile(r'^(what|how|why|when|where|who|which|tell|explain|describe)', re.IGNORECASE),
            "general": re.compile(r'.*')  # Default pattern
        }
        
        # Define sanitization rules
        self.sanitization_rules = [
            (r'[<>]', ''),  # Remove HTML-like tags
            (r'[^\w\s\.,\?!-]', ''),  # Keep only alphanumeric, basic punctuation
            (r'\s+', ' '),  # Normalize whitespace
        ]
        
        # Compile sanitization patterns
        self.sanitization_patterns = [(re.compile(pattern), repl) for pattern, repl in self.sanitization_rules]
    
    def validate_query(self, query: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Validate a query.
        
        Args:
            query: The query to validate
            
        Returns:
            Tuple of (is_valid, query_type, error_message)
        """
        if not query:
            return False, None, "Empty query"
            
        if len(query) < self.min_query_length:
            return False, None, f"Query too short (minimum {self.min_query_length} characters)"
            
        if len(query) > self.max_query_length:
            return False, None, f"Query too long (maximum {self.max_query_length} characters)"
            
        if not self.allowed_chars.match(query):
            return False, None, "Query contains invalid characters"
            
        # Determine query type
        query_type = self._determine_query_type(query)
        
        return True, query_type, None
    
    def sanitize_query(self, query: str) -> str:
        """Sanitize a query.
        
        Args:
            query: The query to sanitize
            
        Returns:
            Sanitized query
        """
        if not query:
            return ""
            
        # Remove sensitive information
        sanitized = query
        for pattern in self.sensitive_patterns:
            sanitized = re.sub(pattern, '[REDACTED]', sanitized)
            
        # Remove excessive whitespace
        sanitized = ' '.join(sanitized.split())
        
        # Truncate if too long
        if len(sanitized) > self.max_query_length:
            sanitized = sanitized[:self.max_query_length]
            
        return sanitized
    
    def _determine_query_type(self, query: str) -> str:
        """Determine the type of query.
        
        Args:
            query: The query to analyze
            
        Returns:
            Query type (action, status, information, or general)
        """
        query = query.lower()
        
        # Check for status queries
        if any(word in query for word in ['status', 'state', 'condition', 'health']):
            return 'status'
            
        # Check for action queries
        if any(word in query for word in ['start', 'stop', 'run', 'execute']):
            return 'action'
            
        # Check for information queries
        if any(word in query for word in ['what', 'how', 'why', 'when', 'where']):
            return 'information'
            
        return 'general'
    
    def extract_parameters(self, query: str, query_type: str) -> Dict[str, Any]:
        """Extract parameters from a query.
        
        Args:
            query: The query to analyze
            query_type: The type of query
            
        Returns:
            Dictionary of extracted parameters
        """
        try:
            params = {
                "raw_query": query,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if query_type == "action":
                # Extract action and target
                match = self.patterns["action"].match(query)
                if match:
                    parts = query.split()
                    params["action"] = parts[0].lower()
                    params["target"] = parts[1] if len(parts) > 1 else None
            
            elif query_type == "status":
                # Extract status target
                match = self.patterns["status"].match(query)
                if match:
                    parts = query.split()
                    params["target"] = parts[-1] if len(parts) > 2 else None
            
            elif query_type == "information":
                # Extract topic
                match = self.patterns["information"].match(query)
                if match:
                    parts = query.split()
                    params["topic"] = parts[1] if len(parts) > 1 else None
            
            return params
            
        except Exception as e:
            logger.error(f"Error extracting parameters: {str(e)}")
            return {"raw_query": query, "error": str(e)}
    
    def validate_parameters(self, params: Dict[str, Any], query_type: str) -> Tuple[bool, Optional[str]]:
        """Validate extracted parameters.
        
        Args:
            params: The parameters to validate
            query_type: The type of query
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not params:
            return True, None
            
        # Validate based on query type
        if query_type == 'action':
            return self._validate_action_params(params)
        elif query_type == 'status':
            return self._validate_status_params(params)
        elif query_type == 'information':
            return self._validate_information_params(params)
            
        return True, None

    def _validate_action_params(self, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate parameters for action queries."""
        required = ['action', 'target']
        for field in required:
            if field not in params:
                return False, f"Missing required parameter: {field}"
        return True, None

    def _validate_status_params(self, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate parameters for status queries."""
        if 'target' not in params:
            return False, "Missing required parameter: target"
        return True, None

    def _validate_information_params(self, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate parameters for information queries."""
        if 'topic' not in params:
            return False, "Missing required parameter: topic"
        return True, None 