import pytest
import os
import json
import tempfile
from datetime import datetime, timezone
from src.apps.agent_004.core.metrics import QueryMetrics

@pytest.fixture
def metrics_dir():
    """Create a temporary directory for metrics."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

@pytest.fixture
def query_metrics(metrics_dir):
    """Create a QueryMetrics instance with temporary directory."""
    return QueryMetrics(metrics_dir=metrics_dir)

def test_init_creates_directory(query_metrics, metrics_dir):
    """Test that initialization creates metrics directory."""
    assert os.path.exists(metrics_dir)

def test_record_query(query_metrics):
    """Test recording a query."""
    query = "What is the status?"
    query_type = "status"
    response_time = 0.5
    
    query_metrics.record_query(query, query_type, response_time)
    
    assert query_metrics.query_counts[query_type] == 1
    assert query_metrics.query_types[query_type] == 1
    assert len(query_metrics.response_times[query_type]) == 1
    assert query_metrics.response_times[query_type][0] == response_time

def test_record_query_with_context(query_metrics):
    """Test recording a query with context usage."""
    query = "What is the status?"
    query_type = "status"
    response_time = 0.5
    
    query_metrics.record_query(query, query_type, response_time, context_used=True)
    
    assert query_metrics.context_usage[query_type] == 1

def test_record_query_with_error(query_metrics):
    """Test recording a query with error."""
    query = "What is the status?"
    query_type = "status"
    response_time = 0.5
    error = "Invalid query format"
    
    query_metrics.record_query(query, query_type, response_time, error=error)
    
    assert query_metrics.error_counts[query_type] == 1

def test_get_metrics_summary(query_metrics):
    """Test getting metrics summary."""
    # Record some test data
    query_metrics.record_query("status query", "status", 0.5)
    query_metrics.record_query("info query", "information", 0.3)
    query_metrics.record_query("error query", "action", 0.4, error="Invalid action")
    
    summary = query_metrics.get_metrics_summary()
    
    assert summary["total_queries"] == 3
    assert "status" in summary["query_type_distribution"]
    assert "information" in summary["query_type_distribution"]
    assert "action" in summary["query_type_distribution"]
    assert "last_updated" in summary
    assert isinstance(summary["last_updated"], str)

def test_metrics_persistence(query_metrics, metrics_dir):
    """Test that metrics are persisted to disk."""
    # Record some test data
    query_metrics.record_query("test query", "test", 0.5)
    
    # Create new instance to load persisted data
    new_metrics = QueryMetrics(metrics_dir=metrics_dir)
    
    assert new_metrics.query_counts["test"] == 1
    assert new_metrics.query_types["test"] == 1

def test_reset_metrics(query_metrics):
    """Test resetting metrics."""
    # Record some test data
    query_metrics.record_query("test query", "test", 0.5)
    
    # Reset metrics
    query_metrics.reset_metrics()
    
    assert query_metrics.query_counts["test"] == 0
    assert query_metrics.query_types["test"] == 0
    assert len(query_metrics.response_times["test"]) == 0
    assert query_metrics.error_counts["test"] == 0
    assert query_metrics.context_usage["test"] == 0

def test_error_handling(query_metrics, metrics_dir):
    """Test error handling in metrics operations."""
    # Test with invalid directory
    invalid_metrics = QueryMetrics(metrics_dir="/invalid/path")
    
    # Should not raise exception
    invalid_metrics.record_query("test", "test", 0.5)
    invalid_metrics._save_metrics()
    
    # Test with invalid data
    query_metrics.record_query("test", "test", 0.5)
    metrics_file = os.path.join(metrics_dir, "query_metrics.json")
    
    # Corrupt the metrics file
    with open(metrics_file, "w") as f:
        f.write("invalid json")
    
    # Should not raise exception when loading
    new_metrics = QueryMetrics(metrics_dir=metrics_dir)
    assert new_metrics.query_counts["test"] == 0  # Should start fresh after error 