"""
Tests for the agent traits module
"""

import json
import pytest
from pathlib import Path

from dreamos.tools.agent_bootstrap_runner.agent_traits import (
    AgentTraits,
    TraitsConfigError
)

@pytest.fixture
def mock_traits_file(tmp_path):
    """Create a mock traits configuration file"""
    traits_data = {
        "Agent-2": {
            "charter": "Documentation and compliance agent",
            "tone": "concise",
            "devlog_style": "field report",
            "validation_policy": "strict",
            "prompt_context": {
                "focus_areas": ["documentation", "compliance"],
                "response_style": "bullet points"
            }
        }
    }
    
    traits_file = tmp_path / "agent_traits.json"
    traits_file.write_text(json.dumps(traits_data))
    return traits_file

class TestAgentTraits:
    """Tests for AgentTraits class"""
    
    def test_initialization_defaults(self):
        """Test initialization with default values"""
        traits = AgentTraits("Agent-2")
        
        # Check default values
        assert traits.agent_id == "Agent-2"
        assert traits.config_dir == Path("runtime/config")
        assert traits.traits["tone"] == "neutral"
        assert traits.traits["devlog_style"] == "standard"
        assert traits.traits["validation_policy"] == "normal"
        
    def test_load_custom_traits(self, tmp_path, mock_traits_file):
        """Test loading custom traits from file"""
        # Initialize with custom config directory
        traits = AgentTraits("Agent-2", config_dir=tmp_path)
        
        # Check that custom traits were loaded
        assert traits.traits["tone"] == "concise"
        assert traits.traits["devlog_style"] == "field report"
        assert traits.traits["validation_policy"] == "strict"
        assert "focus_areas" in traits.traits["prompt_context"]
        
    def test_invalid_traits_file(self, tmp_path):
        """Test handling of invalid traits file"""
        # Create invalid JSON file
        traits_file = tmp_path / "agent_traits.json"
        traits_file.write_text("{invalid json")
        
        # Initialize traits - should use defaults
        traits = AgentTraits("Agent-2", config_dir=tmp_path)
        
        # Check that defaults were used
        assert traits.traits["tone"] == "neutral"
        assert traits.traits["devlog_style"] == "standard"
        
    def test_missing_traits_file(self, tmp_path):
        """Test handling of missing traits file"""
        traits = AgentTraits("Agent-2", config_dir=tmp_path)
        
        # Check that defaults were used
        assert traits.traits["tone"] == "neutral"
        assert traits.traits["devlog_style"] == "standard"
        
    def test_validate_traits(self):
        """Test traits validation"""
        traits = AgentTraits("Agent-2")
        
        # Test valid traits
        valid_traits = {
            "charter": "Test charter",
            "tone": "formal",
            "devlog_style": "standard",
            "validation_policy": "normal"
        }
        assert traits._validate_traits(valid_traits)
        
        # Test missing required field
        invalid_traits = {
            "tone": "formal",
            "devlog_style": "standard"
        }
        assert not traits._validate_traits(invalid_traits)
        
        # Test invalid tone
        invalid_tone = {
            "charter": "Test charter",
            "tone": "invalid",
            "devlog_style": "standard",
            "validation_policy": "normal"
        }
        assert not traits._validate_traits(invalid_tone)
        
    def test_get_prompt_context(self, tmp_path, mock_traits_file):
        """Test getting formatted prompt context"""
        traits = AgentTraits("Agent-2", config_dir=tmp_path)
        context = traits.get_prompt_context()
        
        # Check structure
        assert "agent_traits" in context
        assert "identity" in context["agent_traits"]
        assert "behavior" in context["agent_traits"]
        assert "custom_context" in context["agent_traits"]
        
        # Check values
        behavior = context["agent_traits"]["behavior"]
        assert behavior["tone"] == "concise"
        assert behavior["devlog_style"] == "field report"
        
    def test_apply_validation_policy(self):
        """Test validation policy application"""
        traits = AgentTraits("Agent-2")
        
        # Test strict policy
        traits.traits["validation_policy"] = "strict"
        strict_settings = traits.apply_validation_policy()
        assert strict_settings["require_schema_validation"]
        assert strict_settings["require_format_check"]
        assert strict_settings["max_retries"] == 2
        
        # Test lenient policy
        traits.traits["validation_policy"] = "lenient"
        lenient_settings = traits.apply_validation_policy()
        assert not lenient_settings["require_schema_validation"]
        assert not lenient_settings["require_format_check"]
        assert lenient_settings["max_retries"] == 5
        
        # Test normal policy
        traits.traits["validation_policy"] = "normal"
        normal_settings = traits.apply_validation_policy()
        assert normal_settings["require_schema_validation"]
        assert not normal_settings["require_format_check"]
        assert normal_settings["max_retries"] == 3
        
    def test_to_dict(self, tmp_path, mock_traits_file):
        """Test conversion to dictionary"""
        traits = AgentTraits("Agent-2", config_dir=tmp_path)
        traits_dict = traits.to_dict()
        
        # Check that it's a copy
        assert traits_dict is not traits.traits
        
        # Check values
        assert traits_dict["tone"] == "concise"
        assert traits_dict["devlog_style"] == "field report"
        assert "focus_areas" in traits_dict["prompt_context"] 