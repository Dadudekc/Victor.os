import pytest
from src.apps.agent_004.core.query_validator import QueryValidator

@pytest.fixture
def validator():
    """Create a QueryValidator instance."""
    return QueryValidator()

def test_validate_query_action(validator):
    """Test validation of action queries."""
    # Valid action queries
    assert validator.validate_query("start monitoring")[0] is True
    assert validator.validate_query("stop system")[0] is True
    assert validator.validate_query("check status")[0] is True
    
    # Invalid action queries
    assert validator.validate_query("invalid action")[0] is False
    assert validator.validate_query("start")[0] is False

def test_validate_query_status(validator):
    """Test validation of status queries."""
    # Valid status queries
    assert validator.validate_query("what is the status")[0] is True
    assert validator.validate_query("how is the system state")[0] is True
    assert validator.validate_query("show the condition")[0] is True
    
    # Invalid status queries
    assert validator.validate_query("status")[0] is False
    assert validator.validate_query("what status")[0] is False

def test_validate_query_information(validator):
    """Test validation of information queries."""
    # Valid information queries
    assert validator.validate_query("what is the system")[0] is True
    assert validator.validate_query("how does it work")[0] is True
    assert validator.validate_query("tell me about the status")[0] is True
    
    # Invalid information queries
    assert validator.validate_query("system")[0] is False
    assert validator.validate_query("work")[0] is False

def test_validate_query_general(validator):
    """Test validation of general queries."""
    # Valid general queries
    assert validator.validate_query("hello")[0] is True
    assert validator.validate_query("help")[0] is True
    assert validator.validate_query("what's up")[0] is True

def test_validate_query_length(validator):
    """Test validation of query length."""
    # Too short
    assert validator.validate_query("a")[0] is False
    assert validator.validate_query("")[0] is False
    
    # Too long
    long_query = "a" * 1001
    assert validator.validate_query(long_query)[0] is False

def test_sanitize_query(validator):
    """Test query sanitization."""
    # Test HTML removal
    assert validator.sanitize_query("<script>alert('test')</script>") == "scriptalerttestscript"
    
    # Test special character removal
    assert validator.sanitize_query("test@#$%^&*()") == "test"
    
    # Test whitespace normalization
    assert validator.sanitize_query("  test  query  ") == "test query"
    
    # Test basic punctuation preservation
    assert validator.sanitize_query("test, query!") == "test, query!"

def test_extract_parameters_action(validator):
    """Test parameter extraction for action queries."""
    params = validator.extract_parameters("start monitoring", "action")
    
    assert params["action"] == "start"
    assert params["target"] == "monitoring"
    assert "timestamp" in params
    assert "raw_query" in params

def test_extract_parameters_status(validator):
    """Test parameter extraction for status queries."""
    params = validator.extract_parameters("what is the status of monitoring", "status")
    
    assert params["target"] == "monitoring"
    assert "timestamp" in params
    assert "raw_query" in params

def test_extract_parameters_information(validator):
    """Test parameter extraction for information queries."""
    params = validator.extract_parameters("what is monitoring", "information")
    
    assert params["topic"] == "is"
    assert "timestamp" in params
    assert "raw_query" in params

def test_validate_parameters_action(validator):
    """Test parameter validation for action queries."""
    # Valid parameters
    params = {"action": "start", "target": "monitoring"}
    assert validator.validate_parameters(params, "action")[0] is True
    
    # Invalid parameters
    params = {"action": "start"}
    assert validator.validate_parameters(params, "action")[0] is False
    
    params = {"target": "monitoring"}
    assert validator.validate_parameters(params, "action")[0] is False

def test_validate_parameters_status(validator):
    """Test parameter validation for status queries."""
    # Valid parameters
    params = {"target": "monitoring"}
    assert validator.validate_parameters(params, "status")[0] is True
    
    # Invalid parameters
    params = {}
    assert validator.validate_parameters(params, "status")[0] is False

def test_validate_parameters_information(validator):
    """Test parameter validation for information queries."""
    # Valid parameters
    params = {"topic": "monitoring"}
    assert validator.validate_parameters(params, "information")[0] is True
    
    # Invalid parameters
    params = {}
    assert validator.validate_parameters(params, "information")[0] is False

def test_error_handling(validator):
    """Test error handling in validator methods."""
    # Test validation with invalid input
    assert validator.validate_query(None)[0] is False
    
    # Test sanitization with invalid input
    assert validator.sanitize_query(None) == ""
    
    # Test parameter extraction with invalid input
    params = validator.extract_parameters(None, "action")
    assert "error" in params
    
    # Test parameter validation with invalid input
    assert validator.validate_parameters(None, "action")[0] is False 