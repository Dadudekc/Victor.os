# src/dreamscape/core/content_models.py
# Pydantic models representing Dreamscape content structures.
from typing import List, Optional

from pydantic import BaseModel, Field


class ContentPlan(BaseModel):
    """Represents a plan for generating a piece of content."""

    topic: str = Field(..., description="The main subject of the content.")
    outline: List[str] = Field(
        ..., description="An ordered list of section headings or key points."
    )
    keywords: Optional[List[str]] = Field(
        default=None, description="Optional list of keywords for SEO or tagging."
    )
    target_audience: Optional[str] = Field(
        default=None, description="Optional description of the intended audience."
    )
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "topic": "Integrating AgentBus with Dreamscape",
                    "outline": [
                        "Introduction: Why connect Dreamscape?",
                        "AgentBus Basics Recap",
                        "Event Schemas for Dreamscape",
                        "Planner Agent Integration",
                        "Writer Agent Integration",
                        "Publishing Workflow",
                        "Conclusion",
                    ],
                    "keywords": ["AgentBus", "Dreamscape", "Integration", "Events"],
                    "target_audience": "Dream.OS Developers",
                }
            ]
        }
    }


class ContentDraft(BaseModel):
    """Represents a generated draft of content based on a plan."""

    title: str = Field(..., description="The generated title for the content.")
    body: str = Field(
        ..., description="The main generated text content, likely markdown or HTML."
    )
    plan: ContentPlan = Field(
        ..., description="The ContentPlan used to generate this draft."
    )
    version: int = Field(default=1, description="Version number of the draft.")
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "title": "Exploring AgentBus Integration with Dreamscape",
                    "body": "## Introduction: Why connect Dreamscape?\n\n[Placeholder content...]\n\n## AgentBus Basics Recap\n\n[Placeholder content...]",
                    "plan": {
                        "topic": "Integrating AgentBus with Dreamscape",
                        "outline": ["Introduction...", "AgentBus Basics..."],
                        "keywords": ["AgentBus", "Integration"],
                        "target_audience": "Developers",
                    },
                    "version": 1,
                }
            ]
        }
    }
