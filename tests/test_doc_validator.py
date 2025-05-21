#!/usr/bin/env python3
"""
Tests for the Dream.OS Documentation Validator.
"""

import os
import pytest
from pathlib import Path
from src.dreamos.tools.validation.doc_validator import DocValidator

@pytest.fixture
def temp_docs_dir(tmp_path):
    """Creates a temporary docs directory with test files."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    
    # Create test files
    (docs_dir / "agents" / "onboarding").mkdir(parents=True)
    (docs_dir / "agents" / "capabilities").mkdir(parents=True)
    (docs_dir / "agents" / "protocols").mkdir(parents=True)
    (docs_dir / "agents" / "faqs").mkdir(parents=True)
    
    # Create a valid test file
    valid_file = docs_dir / "agents" / "onboarding" / "UNIFIED_AGENT_ONBOARDING_GUIDE.md"
    valid_file.write_text("""# Test Guide
**Version:** 1.0
**Last Updated:** 2024-03-19
**Status:** ACTIVE

## Section 1
Content here.

## Section 2
More content.
""")
    
    # Create a file with broken link
    broken_link_file = docs_dir / "agents" / "capabilities" / "AGENT_CAPABILITIES.md"
    broken_link_file.write_text("""# Capabilities
**Version:** 1.0
**Last Updated:** 2024-03-19
**Status:** ACTIVE

[Broken Link](nonexistent.md)
""")
    
    # Create a file with invalid heading hierarchy
    invalid_headings_file = docs_dir / "agents" / "protocols" / "TEST_PROTOCOL.md"
    invalid_headings_file.write_text("""# Protocol
**Version:** 1.0
**Last Updated:** 2024-03-19
**Status:** ACTIVE

## Section 1
### Section 1.1
#### Section 1.1.1
# Invalid Jump
""")
    
    return docs_dir

def test_validate_file_structure(temp_docs_dir):
    """Tests file structure validation."""
    validator = DocValidator(docs_root=str(temp_docs_dir))
    missing_files = validator.validate_file_structure()
    
    # Should report all required files as missing except the ones we created
    assert "agents/onboarding/UNIFIED_AGENT_ONBOARDING_GUIDE.md" not in missing_files
    assert "agents/capabilities/AGENT_CAPABILITIES.md" not in missing_files
    assert "agents/protocols/AGENT_OPERATIONAL_LOOP_PROTOCOL.md" in missing_files

def test_validate_markdown_file(temp_docs_dir):
    """Tests markdown file validation."""
    validator = DocValidator(docs_root=str(temp_docs_dir))
    
    # Test valid file
    valid_file = temp_docs_dir / "agents" / "onboarding" / "UNIFIED_AGENT_ONBOARDING_GUIDE.md"
    results = validator.validate_markdown_file(valid_file)
    assert not results["errors"]
    
    # Test file with broken link
    broken_link_file = temp_docs_dir / "agents" / "capabilities" / "AGENT_CAPABILITIES.md"
    results = validator.validate_markdown_file(broken_link_file)
    assert any("Broken link" in error for error in results["errors"])
    
    # Test file with invalid heading hierarchy
    invalid_headings_file = temp_docs_dir / "agents" / "protocols" / "TEST_PROTOCOL.md"
    results = validator.validate_markdown_file(invalid_headings_file)
    assert any("Invalid heading hierarchy" in error for error in results["errors"])

def test_generate_report(temp_docs_dir):
    """Tests report generation."""
    validator = DocValidator(docs_root=str(temp_docs_dir))
    results = {
        "missing_files": ["test/missing.md"],
        "file_issues": {
            "test/file.md": {
                "errors": ["Missing required section: version"]
            }
        }
    }
    
    report = validator.generate_report(results)
    assert "Missing Required Files:" in report
    assert "test/missing.md" in report
    assert "File-Specific Issues:" in report
    assert "Missing required section: version" in report

def test_validate_all(temp_docs_dir):
    """Tests complete validation process."""
    validator = DocValidator(docs_root=str(temp_docs_dir))
    results = validator.validate_all()
    
    assert isinstance(results, dict)
    assert "missing_files" in results
    assert "file_issues" in results
    assert isinstance(results["file_issues"], dict) 