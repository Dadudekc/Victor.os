"""
Tests for the query processor module.
"""

import pytest
from datetime import datetime, timezone, timedelta
from ..core.query_processor import QueryProcessor
import asyncio

@pytest.fixture
def query_processor():
    """Create a query processor instance for testing."""
    return QueryProcessor(max_context_age=3600)

@pytest.mark.asyncio
async def test_process_query_basic(query_processor):
    """Test basic query processing."""
    query = "What is the status?"
    user_id = "test_user"
    
    response = await query_processor.process_query(query, user_id)
    
    assert response["status"] == "success"
    assert response["query_type"] == "status"
    assert "timestamp" in response
    assert not response["context_used"]
    
@pytest.mark.asyncio
async def test_process_query_with_context(query_processor):
    """Test query processing with context."""
    query = "How do I create a new task?"
    user_id = "test_user"
    context = {"previous_action": "view_tasks"}
    
    response = await query_processor.process_query(query, user_id, context)
    
    assert response["status"] == "success"
    assert response["query_type"] == "information"
    assert response["context_used"]
    
def test_query_type_determination(query_processor):
    """Test query type determination."""
    # Information queries
    assert query_processor._determine_query_type("How do I do this?") == "information"
    assert query_processor._determine_query_type("What is the meaning of life?") == "information"
    
    # Action queries
    assert query_processor._determine_query_type("Create a new file") == "action"
    assert query_processor._determine_query_type("Make a backup") == "action"
    
    # Status queries
    assert query_processor._determine_query_type("Check the status") == "status"
    assert query_processor._determine_query_type("Verify the connection") == "status"
    
    # General queries
    assert query_processor._determine_query_type("Hello world") == "general"
    
def test_context_metadata_update(query_processor):
    """Test context metadata updates."""
    user_id = "test_user"
    
    # Initial update
    query_processor._update_context_metadata(user_id)
    metadata = query_processor.get_context_metadata(user_id)
    assert metadata["query_count"] == 0
    
    # Second update
    query_processor._update_context_metadata(user_id)
    metadata = query_processor.get_context_metadata(user_id)
    assert metadata["query_count"] == 1
    
def test_cleanup_old_contexts(query_processor):
    """Test cleanup of old contexts."""
    user_id = "test_user"
    
    # Add some history
    query_processor._query_history[user_id] = [
        {
            "query": "old query",
            "timestamp": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
            "context": {}
        },
        {
            "query": "recent query",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "context": {}
        }
    ]
    
    # Add metadata
    query_processor._context_metadata[user_id] = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "query_count": 2
    }
    
    # Clean up
    query_processor.cleanup_old_contexts()
    
    # Check results
    history = query_processor.get_user_history(user_id)
    assert len(history) == 1
    assert history[0]["query"] == "recent query"
    
    metadata = query_processor.get_context_metadata(user_id)
    assert metadata is not None
    
def test_get_user_history(query_processor):
    """Test getting user history."""
    user_id = "test_user"
    query = "Test query"
    
    # Add some history
    query_processor._query_history[user_id] = [
        {
            "query": query,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "context": {}
        }
    ]
    
    history = query_processor.get_user_history(user_id)
    assert len(history) == 1
    assert history[0]["query"] == query
    
    # Test non-existent user
    assert query_processor.get_user_history("non_existent") == []
    
def test_error_handling(query_processor):
    """Test error handling in query processing."""
    # Test with invalid query type
    query_processor._determine_query_type = lambda x: "invalid_type"
    
    response = query_processor.process_query("test", "test_user")
    assert response["status"] == "error"
    assert "error" in response 

@pytest.mark.asyncio
async def test_handle_information_query(query_processor):
    """Test handling of information queries."""
    query = "What is the current status of the monitoring system?"
    context = {
        "monitoring": {
            "status": "active",
            "type": "system",
            "features": ["logging", "alerts"]
        },
        "system": {
            "status": "operational",
            "components": ["monitoring", "logging"]
        }
    }
    
    response = await query_processor._handle_information_query(query, "test_user", context)
    
    assert response["status"] == "success"
    assert response["type"] == "information"
    assert "topics" in response["data"]
    assert "context_info" in response["data"]
    assert "recent_queries" in response["data"]
    assert "suggestions" in response["data"]
    assert "timestamp" in response["data"]
    
    # Check topics extraction
    topics = response["data"]["topics"]
    assert "monitoring" in topics
    assert "system" in topics
    
    # Check context info
    context_info = response["data"]["context_info"]
    assert "monitoring" in context_info
    assert "system" in context_info
    assert context_info["monitoring"]["status"] == "active"
    
    # Check suggestions
    suggestions = response["data"]["suggestions"]
    assert len(suggestions) <= 5
    assert any("status" in s.lower() for s in suggestions)
    assert any("features" in s.lower() for s in suggestions)

@pytest.mark.asyncio
async def test_handle_action_query(query_processor):
    """Test handling of action queries."""
    query = "start monitoring system"
    user_id = "test_user"
    context = {
        "system": {
            "status": "inactive",
            "components": {
                "monitoring": {"status": "inactive"},
                "logging": {"status": "active"}
            },
            "resources": {
                "cpu": 45,
                "memory": 60
            }
        }
    }
    
    response = await query_processor._handle_action_query(query, user_id, context)
    
    assert response["status"] == "success"
    assert response["type"] == "action"
    assert "data" in response
    assert response["data"]["query"] == query
    assert response["data"]["action"] == "start"
    assert "parameters" in response["data"]
    assert "prerequisites" in response["data"]
    assert "recent_actions" in response["data"]
    assert "timestamp" in response["data"]
    
    # Check parameters
    params = response["data"]["parameters"]
    assert params["target"] == "monitoring"
    assert "system" in params["options"]
    assert "raw_query" in params
    assert "timestamp" in params
    
    # Check prerequisites
    prereqs = response["data"]["prerequisites"]
    assert prereqs["status"] == "inactive"
    assert len(prereqs["checks"]) > 0
    assert len(prereqs["warnings"]) == 0
    
    # Check suggestions
    assert "suggestions" in response["data"]
    suggestions = response["data"]["suggestions"]
    assert len(suggestions) > 0
    assert any("check status" in s for s in suggestions)
    assert any("get logs" in s for s in suggestions)

@pytest.mark.asyncio
async def test_handle_status_query(query_processor):
    """Test handling of status queries."""
    query = "check status of monitoring system"
    user_id = "test_user"
    context = {
        "system": {
            "status": "active",
            "components": {
                "monitoring": {
                    "status": "active",
                    "metrics": {
                        "cpu": 45,
                        "memory": 60
                    }
                },
                "logging": {
                    "status": "warning",
                    "metrics": {
                        "cpu": 95,
                        "memory": 92
                    }
                }
            },
            "resources": {
                "cpu": 70,
                "memory": 75
            }
        }
    }
    
    response = await query_processor._handle_status_query(query, user_id, context)
    
    assert response["status"] == "success"
    assert response["type"] == "status"
    assert "data" in response
    assert response["data"]["query"] == query
    assert response["data"]["target"] == "monitoring"
    assert "status_info" in response["data"]
    assert "recent_checks" in response["data"]
    assert "timestamp" in response["data"]
    
    # Check status info
    status_info = response["data"]["status_info"]
    assert status_info["target"] == "monitoring"
    assert status_info["status"] == "active"
    assert "components" in status_info
    assert "metrics" in status_info
    assert "warnings" in status_info
    assert "last_updated" in status_info
    
    # Check metrics
    metrics = status_info["metrics"]
    assert "cpu" in metrics
    assert "memory" in metrics
    assert metrics["cpu"] == 45
    assert metrics["memory"] == 60
    
    # Check suggestions
    assert "suggestions" in response["data"]
    suggestions = response["data"]["suggestions"]
    assert len(suggestions) > 0

@pytest.mark.asyncio
async def test_handle_general_query(query_processor):
    """Test handling of general queries."""
    query = "how does the monitoring system work"
    user_id = "test_user"
    context = {
        "system": {
            "description": "A comprehensive monitoring system",
            "components": {
                "monitoring": {
                    "status": "active",
                    "features": ["metrics", "alerts", "dashboards"]
                },
                "logging": {
                    "status": "active",
                    "features": ["log collection", "analysis"]
                }
            },
            "help": {
                "guides": ["getting_started", "advanced_usage"],
                "faq": ["common_issues", "best_practices"],
                "tutorials": ["basic_setup", "custom_dashboards"]
            }
        }
    }
    
    response = await query_processor._handle_general_query(query, user_id, context)
    
    assert response["status"] == "success"
    assert response["type"] == "general"
    assert "data" in response
    assert response["data"]["query"] == query
    assert response["data"]["intent"] == "system_inquiry"
    assert "context" in response["data"]
    assert "recent_queries" in response["data"]
    assert "timestamp" in response["data"]
    
    # Check context
    context_data = response["data"]["context"]
    assert context_data["intent"] == "system_inquiry"
    assert "system" in context_data
    assert "description" in context_data["system"]
    assert "components" in context_data["system"]
    assert "features" in context_data["system"]
    
    # Check suggestions
    assert "suggestions" in response["data"]
    suggestions = response["data"]["suggestions"]
    assert len(suggestions) > 0
    assert any("learn more about" in s for s in suggestions)
    assert any("check system documentation" in s for s in suggestions)

def test_extract_topics(query_processor):
    """Test topic extraction from queries."""
    # Test basic topic extraction
    query = "What is the status of the monitoring system?"
    topics = query_processor._extract_topics(query)
    assert "monitoring" in topics
    assert "system" in topics
    assert "what" not in topics  # Stop word removed
    assert "is" not in topics    # Stop word removed
    
    # Test related words grouping
    query = "monitor monitoring monitored"
    topics = query_processor._extract_topics(query)
    assert len(topics) < 3  # Related words should be grouped
    
    # Test short words filtering
    query = "a an the in on at"
    topics = query_processor._extract_topics(query)
    assert len(topics) == 0  # All words should be filtered

def test_get_context_info(query_processor):
    """Test context information retrieval."""
    topics = ["monitoring", "system"]
    context = {
        "monitoring": {
            "status": "active",
            "type": "system"
        },
        "system": {
            "status": "operational",
            "components": ["monitoring", "logging"]
        },
        "unrelated": {
            "data": "value"
        }
    }
    
    info = query_processor._get_context_info(topics, context)
    
    # Check exact matches
    assert "monitoring" in info
    assert "system" in info
    assert "unrelated" not in info
    
    # Check nested search
    assert "monitoring.status" in info
    assert "system.components" in info
    
    # Check partial matches
    topics = ["monitor"]
    info = query_processor._get_context_info(topics, context)
    assert "monitoring" in info

def test_extract_action_params(query_processor):
    """Test extraction of action parameters."""
    # Test basic action extraction
    query = "start monitoring system"
    action, params = query_processor._extract_action_params(query)
    assert action == "start"
    assert params["target"] == "monitoring"
    assert "system" in params["options"]
    
    # Test action with no target
    query = "check"
    action, params = query_processor._extract_action_params(query)
    assert action == "check"
    assert params["target"] is None
    assert len(params["options"]) == 0
    
    # Test action with multiple options
    query = "set config debug level high"
    action, params = query_processor._extract_action_params(query)
    assert action == "set"
    assert params["target"] == "config"
    assert "debug" in params["options"]
    assert "level" in params["options"]
    assert "high" in params["options"]

def test_is_valid_action(query_processor):
    """Test action validation."""
    # Test valid actions
    assert query_processor._is_valid_action("start")
    assert query_processor._is_valid_action("stop")
    assert query_processor._is_valid_action("restart")
    assert query_processor._is_valid_action("check")
    assert query_processor._is_valid_action("get")
    assert query_processor._is_valid_action("set")
    assert query_processor._is_valid_action("update")
    assert query_processor._is_valid_action("delete")
    
    # Test invalid actions
    assert not query_processor._is_valid_action("invalid")
    assert not query_processor._is_valid_action("unknown")
    assert not query_processor._is_valid_action("")

def test_check_action_prerequisites(query_processor):
    """Test action prerequisite checking."""
    # Test start action with inactive system
    context = {
        "system": {
            "status": "inactive",
            "components": {
                "monitoring": {"status": "inactive"},
                "logging": {"status": "active"}
            },
            "resources": {
                "cpu": 45,
                "memory": 60
            }
        }
    }
    prereqs = query_processor._check_action_prerequisites("start", context)
    assert prereqs["status"] == "inactive"
    assert len(prereqs["checks"]) == 2
    assert len(prereqs["warnings"]) == 0
    
    # Test stop action with active system
    context["system"]["status"] = "active"
    context["components"]["monitoring"]["status"] = "active"
    prereqs = query_processor._check_action_prerequisites("stop", context)
    assert prereqs["status"] == "active"
    assert len(prereqs["checks"]) == 2
    assert len(prereqs["warnings"]) == 0
    
    # Test with high resource usage
    context["resources"]["cpu"] = 95
    context["resources"]["memory"] = 92
    prereqs = query_processor._check_action_prerequisites("start", context)
    assert len(prereqs["warnings"]) == 2
    assert any("CPU" in w for w in prereqs["warnings"])
    assert any("memory" in w for w in prereqs["warnings"])

def test_extract_status_target(query_processor):
    """Test extraction of status target."""
    # Test with explicit target
    query = "check status of monitoring system"
    target = query_processor._extract_status_target(query)
    assert target == "monitoring"
    
    # Test with different status keywords
    query = "what is the state of logging service"
    target = query_processor._extract_status_target(query)
    assert target == "logging"
    
    query = "show me the health of system"
    target = query_processor._extract_status_target(query)
    assert target == "system"
    
    # Test with no specific target
    query = "what is the status"
    target = query_processor._extract_status_target(query)
    assert target == "system"  # Default target

def test_get_status_info(query_processor):
    """Test getting status information."""
    # Test system status
    context = {
        "system": {
            "status": "active",
            "components": {
                "monitoring": {"status": "active"},
                "logging": {"status": "warning"}
            },
            "resources": {
                "cpu": 70,
                "memory": 75
            }
        }
    }
    
    status_info = query_processor._get_status_info("system", context)
    assert status_info["target"] == "system"
    assert status_info["status"] == "active"
    assert len(status_info["components"]) == 2
    assert "metrics" in status_info
    assert len(status_info["warnings"]) == 0
    
    # Test component status
    status_info = query_processor._get_status_info("monitoring", context)
    assert status_info["target"] == "monitoring"
    assert status_info["status"] == "active"
    assert len(status_info["components"]) == 0
    
    # Test with error status
    context["system"]["status"] = "error"
    status_info = query_processor._get_status_info("system", context)
    assert status_info["status"] == "error"
    assert len(status_info["warnings"]) > 0
    assert any("error state" in w for w in status_info["warnings"])
    
    # Test with high resource usage
    context["system"]["resources"]["cpu"] = 95
    context["system"]["resources"]["memory"] = 92
    status_info = query_processor._get_status_info("system", context)
    assert len(status_info["warnings"]) > 0
    assert any("CPU" in w for w in status_info["warnings"])
    assert any("memory" in w for w in status_info["warnings"])

def test_generate_status_suggestions(query_processor):
    """Test generation of status suggestions."""
    # Test suggestions for error status
    target = "monitoring"
    status_info = {
        "target": target,
        "status": "error",
        "warnings": []
    }
    recent_checks = []
    
    suggestions = query_processor._generate_status_suggestions(target, status_info, recent_checks)
    assert len(suggestions) > 0
    assert any("check logs" in s for s in suggestions)
    assert any("restart" in s for s in suggestions)
    
    # Test suggestions for warning status
    status_info["status"] = "warning"
    suggestions = query_processor._generate_status_suggestions(target, status_info, recent_checks)
    assert any("check configuration" in s for s in suggestions)
    assert any("monitor metrics" in s for s in suggestions)
    
    # Test suggestions with resource warnings
    status_info["warnings"] = ["High CPU usage"]
    suggestions = query_processor._generate_status_suggestions(target, status_info, recent_checks)
    assert any("CPU-intensive" in s for s in suggestions)
    assert any("optimize resource" in s for s in suggestions)
    
    # Test suggestions based on recent checks
    recent_checks = [{"target": target, "status": "active"}]
    suggestions = query_processor._generate_status_suggestions(target, status_info, recent_checks)
    assert any("compare with previous" in s for s in suggestions)
    assert any("check for status changes" in s for s in suggestions)

def test_generate_action_suggestions(query_processor):
    """Test generation of action suggestions."""
    # Test suggestions for start action
    action = "start"
    params = {"target": "monitoring", "options": ["system"]}
    prerequisites = {"status": "inactive", "checks": [], "warnings": []}
    recent_actions = []
    
    suggestions = query_processor._generate_action_suggestions(action, params, prerequisites, recent_actions)
    assert len(suggestions) > 0
    assert any("check status" in s for s in suggestions)
    assert any("get logs" in s for s in suggestions)
    
    # Test suggestions with warnings
    prerequisites["warnings"] = ["High CPU usage detected"]
    suggestions = query_processor._generate_action_suggestions(action, params, prerequisites, recent_actions)
    assert any("check system resources" in s for s in suggestions)
    assert any("verify component status" in s for s in suggestions)
    
    # Test suggestions based on recent actions
    recent_actions = [{"action": "start", "target": "monitoring"}]
    suggestions = query_processor._generate_action_suggestions(action, params, prerequisites, recent_actions)
    assert any("check if service is running" in s for s in suggestions)
    assert any("verify logs for errors" in s for s in suggestions)
    
    # Test suggestions for stop action
    action = "stop"
    recent_actions = [{"action": "stop", "target": "monitoring"}]
    suggestions = query_processor._generate_action_suggestions(action, params, prerequisites, recent_actions)
    assert any("verify service is stopped" in s for s in suggestions)
    assert any("check for cleanup tasks" in s for s in suggestions)

def test_generate_suggestions(query_processor):
    """Test suggestion generation."""
    topics = ["monitoring", "system"]
    context_info = {
        "monitoring": {
            "status": "active",
            "type": "system"
        },
        "system": {
            "status": "operational"
        }
    }
    recent_queries = [
        "What is the status of monitoring?",
        "How does the system work?"
    ]
    
    suggestions = query_processor._generate_suggestions(topics, context_info, recent_queries)
    
    # Check suggestion count
    assert len(suggestions) <= 5
    
    # Check topic-based suggestions
    assert any("status of monitoring" in s.lower() for s in suggestions)
    assert any("how does monitoring work" in s.lower() for s in suggestions)
    
    # Check context-based suggestions
    assert any("current status" in s.lower() for s in suggestions)
    assert any("features" in s.lower() for s in suggestions)
    
    # Check recent query-based suggestions
    assert any("recent changes" in s.lower() for s in suggestions)
    assert any("prerequisites" in s.lower() for s in suggestions)

def test_create_error_response(query_processor):
    """Test error response creation."""
    error_type = "test_error"
    message = "Test error message"
    
    response = query_processor._create_error_response(error_type, message)
    
    assert response["status"] == "error"
    assert response["type"] == error_type
    assert response["error"] == message
    assert "timestamp" in response 

def test_extract_general_intent(query_processor):
    """Test extraction of general intent."""
    processor = QueryProcessor()
    
    # Test system inquiry
    query = "how does the system work"
    intent = processor._extract_general_intent(query)
    assert intent == "system_inquiry"
    
    # Test help request
    query = "how can i configure the system"
    intent = processor._extract_general_intent(query)
    assert intent == "help_request"
    
    # Test configuration inquiry
    query = "what are the system settings"
    intent = processor._extract_general_intent(query)
    assert intent == "configuration_inquiry"
    
    # Test troubleshooting
    query = "the system is not working"
    intent = processor._extract_general_intent(query)
    assert intent == "troubleshooting"
    
    # Test performance inquiry
    query = "why is the system slow"
    intent = processor._extract_general_intent(query)
    assert intent == "performance_inquiry"
    
    # Test default intent
    query = "random query"
    intent = processor._extract_general_intent(query)
    assert intent == "general_inquiry"

def test_get_relevant_context(query_processor):
    """Test getting relevant context."""
    processor = QueryProcessor()
    
    # Test system inquiry context
    context = {
        "system": {
            "description": "A complex system",
            "components": {"monitoring": {}, "logging": {}},
            "features": ["feature1", "feature2"]
        }
    }
    relevant_context = processor._get_relevant_context("system_inquiry", context)
    assert relevant_context["intent"] == "system_inquiry"
    assert "system" in relevant_context
    assert "description" in relevant_context["system"]
    assert "components" in relevant_context["system"]
    assert "features" in relevant_context["system"]
    
    # Test help request context
    context = {
        "help": {
            "guides": ["guide1", "guide2"],
            "faq": ["faq1", "faq2"],
            "tutorials": ["tutorial1", "tutorial2"]
        }
    }
    relevant_context = processor._get_relevant_context("help_request", context)
    assert relevant_context["intent"] == "help_request"
    assert "help" in relevant_context
    assert "guides" in relevant_context["help"]
    assert "faq" in relevant_context["help"]
    assert "tutorials" in relevant_context["help"]
    
    # Test configuration inquiry context
    context = {
        "config": {
            "settings": {"setting1": "value1"},
            "options": {"option1": "value1"},
            "parameters": {"param1": "value1"}
        }
    }
    relevant_context = processor._get_relevant_context("configuration_inquiry", context)
    assert relevant_context["intent"] == "configuration_inquiry"
    assert "config" in relevant_context
    assert "settings" in relevant_context["config"]
    assert "options" in relevant_context["config"]
    assert "parameters" in relevant_context["config"]
    
    # Test troubleshooting context
    context = {
        "system": {
            "status": "error",
            "errors": ["error1", "error2"],
            "warnings": ["warning1", "warning2"]
        }
    }
    relevant_context = processor._get_relevant_context("troubleshooting", context)
    assert relevant_context["intent"] == "troubleshooting"
    assert "system" in relevant_context
    assert "status" in relevant_context["system"]
    assert "errors" in relevant_context["system"]
    assert "warnings" in relevant_context["system"]
    
    # Test performance inquiry context
    context = {
        "system": {
            "metrics": {"metric1": "value1"},
            "resources": {"resource1": "value1"},
            "performance": {"perf1": "value1"}
        }
    }
    relevant_context = processor._get_relevant_context("performance_inquiry", context)
    assert relevant_context["intent"] == "performance_inquiry"
    assert "system" in relevant_context
    assert "metrics" in relevant_context["system"]
    assert "resources" in relevant_context["system"]
    assert "performance" in relevant_context["system"]
    
def test_generate_general_suggestions(query_processor):
    """Test generation of general suggestions."""
    processor = QueryProcessor()
    
    # Test system inquiry suggestions
    intent = "system_inquiry"
    context = {
        "system": {
            "components": ["monitoring", "logging"]
        }
    }
    recent_queries = []
    
    suggestions = processor._generate_general_suggestions(intent, context, recent_queries)
    assert len(suggestions) > 0
    assert any("learn more about monitoring" in s for s in suggestions)
    assert any("learn more about logging" in s for s in suggestions)
    assert any("check system documentation" in s for s in suggestions)
    
    # Test help request suggestions
    intent = "help_request"
    context = {
        "help": {
            "guides": ["guide1"],
            "faq": ["faq1"],
            "tutorials": ["tutorial1"]
        }
    }
    suggestions = processor._generate_general_suggestions(intent, context, recent_queries)
    assert any("browse help guides" in s for s in suggestions)
    assert any("check frequently asked questions" in s for s in suggestions)
    assert any("view tutorials" in s for s in suggestions)
    
    # Test configuration inquiry suggestions
    intent = "configuration_inquiry"
    context = {
        "config": {
            "settings": {"setting1": "value1"},
            "options": {"option1": "value1"}
        }
    }
    suggestions = processor._generate_general_suggestions(intent, context, recent_queries)
    assert any("view current settings" in s for s in suggestions)
    assert any("explore configuration options" in s for s in suggestions)
    
    # Test troubleshooting suggestions
    intent = "troubleshooting"
    context = {
        "system": {
            "errors": ["error1"],
            "warnings": ["warning1"]
        }
    }
    suggestions = processor._generate_general_suggestions(intent, context, recent_queries)
    assert any("check error logs" in s for s in suggestions)
    assert any("review system warnings" in s for s in suggestions)
    assert any("run system diagnostics" in s for s in suggestions)
    
    # Test performance inquiry suggestions
    intent = "performance_inquiry"
    context = {
        "system": {
            "metrics": {"metric1": "value1"},
            "resources": {"resource1": "value1"}
        }
    }
    suggestions = processor._generate_general_suggestions(intent, context, recent_queries)
    assert any("view detailed metrics" in s for s in suggestions)
    assert any("check resource usage" in s for s in suggestions)
    assert any("run performance analysis" in s for s in suggestions)
    
    # Test suggestions based on recent queries
    recent_queries = [{"type": "status", "target": "system"}]
    suggestions = processor._generate_general_suggestions(intent, context, recent_queries)
    assert any("check current status" in s for s in suggestions)
    
    recent_queries = [{"type": "action", "action": "start"}]
    suggestions = processor._generate_general_suggestions(intent, context, recent_queries)
    assert any("verify action results" in s for s in suggestions)

def test_classify_query_type():
    """Test query type classification."""
    processor = QueryProcessor()
    
    # Test status queries
    assert processor._classify_query_type("What is the status of the system?", {}) == 'status'
    assert processor._classify_query_type("Check system health", {}) == 'status'
    assert processor._classify_query_type("Is the service running?", {}) == 'status'
    
    # Test action queries
    assert processor._classify_query_type("Start the monitoring service", {}) == 'action'
    assert processor._classify_query_type("Stop the system", {}) == 'action'
    assert processor._classify_query_type("Execute backup", {}) == 'action'
    
    # Test information queries
    assert processor._classify_query_type("What is the monitoring system?", {}) == 'information'
    assert processor._classify_query_type("How does the system work?", {}) == 'information'
    assert processor._classify_query_type("Tell me about the features", {}) == 'information'
    
    # Test general queries
    assert processor._classify_query_type("Hello", {}) == 'general'
    assert processor._classify_query_type("Good morning", {}) == 'general'

def test_handle_deviation():
    """Test deviation handling protocol."""
    processor = QueryProcessor()
    
    # Simulate a deviation
    error = Exception("Test error")
    processor._handle_deviation(error, "Test context")
    
    # Check deviation was logged
    assert processor.last_deviation is not None
    assert processor.last_deviation['error'] == "Test error"
    assert processor.last_deviation['context'] == "Test context"
    assert processor.last_deviation['cycles'] == 0
    
    # Check cycle count was reset
    assert processor.operational_cycles == 0

def test_create_error_response():
    """Test error response creation."""
    processor = QueryProcessor()
    
    # Create error response
    response = processor._create_error_response("Test error message")
    
    # Check response structure
    assert response['status'] == 'error'
    assert response['type'] == 'error_response'
    assert 'error' in response['data']
    assert 'timestamp' in response['data']
    assert response['data']['error'] == "Test error message"

def test_operational_cycles():
    """Test operational cycle counting."""
    processor = QueryProcessor()
    
    # Initial state
    assert processor.operational_cycles == 0
    
    # Process a query
    query = "What is the system status?"
    context = {"system": {"status": "active"}}
    asyncio.run(processor.process_query(query, "test_user", context))
    
    # Check cycle was incremented
    assert processor.operational_cycles == 1
    
    # Simulate deviation
    processor._handle_deviation(Exception("Test"), "Test")
    
    # Check cycle was reset
    assert processor.operational_cycles == 0 