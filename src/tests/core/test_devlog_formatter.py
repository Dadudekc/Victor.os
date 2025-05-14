"""
Test suite for DevlogFormatter

Validates the formatting and file operations of the DevlogFormatter class,
ensuring reliable logging of ethos-related events.
"""

import json
import os
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, mock_open
import time

from dreamos.core.devlog_formatter import DevlogFormatter

@pytest.fixture
def temp_log_dir(tmp_path):
    """Create a temporary directory for test logs."""
    log_dir = tmp_path / "test_logs"
    log_dir.mkdir()
    return log_dir

@pytest.fixture
def formatter(temp_log_dir):
    """Create a DevlogFormatter instance with test directory."""
    return DevlogFormatter(str(temp_log_dir))

@pytest.fixture
def sample_violation():
    """Sample ethos violation data."""
    return {
        "severity": "high",
        "principle": "human_agency",
        "details": "Agent attempted to override user decision",
        "recommendation": "Implement user confirmation step"
    }

@pytest.fixture
def sample_compliance_report():
    """Sample compliance report data."""
    return {
        "timestamp": datetime.now().isoformat(),
        "metrics": {
            "human_agency": 0.85,
            "transparency": 0.92,
            "safety": 0.78
        },
        "recommendations": [
            "Increase safety compliance monitoring",
            "Add additional transparency checks"
        ]
    }

@pytest.fixture
def sample_identity_update():
    """Sample identity update data."""
    return {
        "agent_id": "test_agent",
        "changes": {
            "capabilities": ["new_capability"],
            "personality_traits": ["more_empathetic"]
        },
        "reason": "User feedback indicated need for improvement"
    }

class TestDevlogFormatter:
    """Test suite for DevlogFormatter class."""
    
    def test_init_default_path(self):
        """Test initialization with default path."""
        formatter = DevlogFormatter()
        assert formatter.devlog_path == Path("runtime/logs/empathy")
        
    def test_init_custom_path(self, temp_log_dir):
        """Test initialization with custom path."""
        formatter = DevlogFormatter(str(temp_log_dir))
        assert formatter.devlog_path == temp_log_dir
        
    def test_format_violation(self, formatter, sample_violation):
        """Test violation formatting."""
        formatted = formatter.format_violation(sample_violation)
        
        # Check required components
        assert "🛑 ETHOS VIOLATION" in formatted
        assert "human_agency" in formatted
        assert "Agent attempted to override user decision" in formatted
        assert "Implement user confirmation step" in formatted
        
    def test_format_violation_edge_cases(self, formatter):
        """Test violation formatting with edge cases."""
        # Empty violation
        empty_violation = {}
        formatted = formatter.format_violation(empty_violation)
        assert "⚠️ ETHOS VIOLATION" in formatted
        assert "unknown" in formatted
        
        # Missing fields
        partial_violation = {"severity": "critical"}
        formatted = formatter.format_violation(partial_violation)
        assert "💥 ETHOS VIOLATION" in formatted
        assert "unknown" in formatted
        
    def test_format_compliance_report(self, formatter, sample_compliance_report):
        """Test compliance report formatting."""
        formatted = formatter.format_compliance_report(sample_compliance_report)
        
        # Check required components
        assert "📊 ETHOS COMPLIANCE REPORT" in formatted
        assert "human_agency: 85.00%" in formatted
        assert "transparency: 92.00%" in formatted
        assert "safety: 78.00%" in formatted
        assert "Increase safety compliance monitoring" in formatted
        
    def test_format_identity_update(self, formatter, sample_identity_update):
        """Test identity update formatting."""
        formatted = formatter.format_identity_update(sample_identity_update)
        
        # Check required components
        assert "🔄 AGENT IDENTITY UPDATE" in formatted
        assert "test_agent" in formatted
        assert "new_capability" in formatted
        assert "more_empathetic" in formatted
        assert "User feedback indicated need for improvement" in formatted
        
    def test_write_devlog(self, formatter, temp_log_dir):
        """Test writing to devlog."""
        content = "Test log entry"
        formatter.write_devlog(content, "test")
        
        # Check file creation
        log_files = list(temp_log_dir.glob("test_*.md"))
        assert len(log_files) == 1
        
        # Check content
        with open(log_files[0], 'r', encoding='utf-8') as f:
            assert f.read() == content
            
    def test_format_and_write_violation(self, formatter, temp_log_dir, sample_violation):
        """Test formatting and writing violation."""
        formatter.format_and_write_violation(sample_violation)
        
        # Check file creation
        log_files = list(temp_log_dir.glob("violation_*.md"))
        assert len(log_files) == 1
        
        # Check content
        with open(log_files[0], 'r', encoding='utf-8') as f:
            content = f.read()
            assert "🛑 ETHOS VIOLATION" in content
            assert "human_agency" in content
            
    def test_get_recent_violations(self, formatter, temp_log_dir):
        """Test retrieving recent violations."""
        # Create test violation files
        # Ensure distinct modification times by sleeping briefly
        base_time_for_files = datetime(2024, 1, 1, 0, 0, 0)
        for i in range(15):
            # Create files with slightly offset names to help if mtime is identical
            # And also ensure their content reflects their intended order
            file_time = base_time_for_files + timedelta(seconds=i)
            timestamp_str = file_time.strftime("%Y%m%d_%H%M%S")
            file_path = temp_log_dir / f"violation_{timestamp_str}_{i:02d}.md"
            with open(file_path, "w", encoding='utf-8') as f:
                f.write(f"Test violation {i}") # Content is "Test violation 0", "Test violation 1", ...
            # Explicitly set mtime if possible, or rely on slight delay from loop and naming
            # For simplicity, we'll rely on the loop taking some time and unique names.
            # If issues persist, os.utime might be needed.
            if i < 14 : # Don't sleep after the last file
                 time.sleep(0.01) # Small delay

        # Test limit
        violations = formatter.get_recent_violations(limit=10)
        assert len(violations) == 10
        
        # Test ordering
        # violations[0] should be the most recent one, which is "Test violation 14"
        assert "Test violation 14" in violations[0]
        assert "Test violation 13" in violations[1] # The next one
        
    def test_get_compliance_history(self, formatter, temp_log_dir):
        """Test retrieving compliance history."""
        # Create test compliance files
        base_time = datetime.now()
        for i in range(10):
            timestamp = (base_time - timedelta(days=i)).strftime("%Y%m%d_%H%M%S")
            with open(temp_log_dir / f"compliance_{timestamp}.md", "w", encoding='utf-8') as f:
                f.write(f"Test compliance {i}")
                
        # Test history retrieval
        history = formatter.get_compliance_history(days=7)
        assert len(history) == 7
        
        # Test ordering
        assert "Test compliance 0" in history[0]
        
    def test_duplicate_log_avoidance(self, formatter, temp_log_dir):
        """Test that duplicate logs are not created."""
        content = "Test log entry"
        
        # Write same content twice
        formatter.write_devlog(content, "test")
        formatter.write_devlog(content, "test")
        
        # Check only one file exists
        log_files = list(temp_log_dir.glob("test_*.md"))
        assert len(log_files) == 1
        
    def test_malformed_data_handling(self, formatter):
        """Test handling of malformed data."""
        # Test with None
        assert formatter.format_violation(None) is not None
        
        # Test with invalid types
        assert formatter.format_compliance_report({"metrics": "invalid"}) is not None
        
        # Test with missing required fields
        assert formatter.format_identity_update({}) is not None
        
    @pytest.mark.skip(reason="os.chmod for directory read-only is unreliable on Windows for preventing file creation within.")
    def test_file_permission_handling(self, formatter, temp_log_dir):
        """Test handling of file permission issues."""
        # Make directory read-only
        os.chmod(temp_log_dir, 0o444)
        
        with pytest.raises(PermissionError):
            formatter.write_devlog("Test", "test")
            
        # Restore permissions
        os.chmod(temp_log_dir, 0o755) 