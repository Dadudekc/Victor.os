"""
Test suite for DevlogFormatter

Validates the formatting and file operations of the DevlogFormatter class,
ensuring reliable logging of ethos-related events.
"""

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

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
        # Create test compliance files with controlled dates and mtimes
        # Mock datetime.now() to a fixed point for consistent cutoff calculation
        mock_now = datetime(2024, 3, 15, 12, 0, 0) # Fixed "now"

        with patch('dreamos.core.devlog_formatter.datetime') as mock_datetime_module:
            mock_datetime_module.now.return_value = mock_now
            mock_datetime_module.fromtimestamp = datetime.fromtimestamp # Keep original fromtimestamp
            mock_datetime_module.date = datetime.date # Keep original date type

            # Create 10 files, one for each day from "mock_now" down to "mock_now - 9 days"
            # Ensure their mtimes are also set to these exact start-of-day timestamps
            for i in range(10): # i from 0 (today) to 9 (9 days ago)
                # Target date for this file
                file_date_target = (mock_now - timedelta(days=i)).date()
                # Timestamp for the file name (e.g., "compliance_20240315_120000.md")
                # We use mock_now's time for consistency in filename, but mtime is key
                file_actual_timestamp = mock_now - timedelta(days=i)
                filename_timestamp_str = file_actual_timestamp.strftime("%Y%m%d_%H%M%S")

                file_path = temp_log_dir / f"compliance_{filename_timestamp_str}_{i:02d}.md"
                
                with open(file_path, "w", encoding='utf-8') as f:
                    f.write(f"Test compliance {i} (Date: {file_date_target.isoformat()})")
                
                # Set the modification time to the start of the target day
                mtime_target = datetime.combine(file_date_target, datetime.min.time()).timestamp()
                os.utime(file_path, (mtime_target, mtime_target))

            # Test history retrieval for last 7 days
            # Based on mock_now (2024-03-15), days=7 should include:
            # 2024-03-15 (i=0)
            # 2024-03-14 (i=1)
            # 2024-03-13 (i=2)
            # 2024-03-12 (i=3)
            # 2024-03-11 (i=4)
            # 2024-03-10 (i=5)
            # 2024-03-09 (i=6)
            # Cutoff date should be 2024-03-09
            history = formatter.get_compliance_history(days=7)
            assert len(history) == 7, f"Expected 7 files, got {len(history)}. Cutoff date used by formatter: {mock_now.date() - timedelta(days=7-1)}"
        
            # Test ordering (newest first)
            # File for i=0 (2024-03-15) should be first in history
            assert f"Test compliance 0 (Date: {(mock_now - timedelta(days=0)).date().isoformat()})" in history[0]
            # File for i=6 (2024-03-09) should be last in the 7-day history
            assert f"Test compliance 6 (Date: {(mock_now - timedelta(days=6)).date().isoformat()})" in history[6]

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