# src/dreamscape/config.py
from typing import Optional
from pydantic import BaseModel, Field

class DreamscapePlannerAgentConfig(BaseModel):
    agent_id: str = Field(
        "dreamscape_planner_001", description="Agent ID for the planner"
    )
    llm_model: str = Field("gpt-3.5-turbo", description="LLM model to use for planning")
    max_tokens: int = Field(500, description="Max tokens for planning LLM response")

class DreamscapeWriterAgentConfig(BaseModel):
    agent_id: str = Field(
        "dreamscape_writer_001", description="Agent ID for the writer"
    )
    llm_model: str = Field(
        "gpt-4-turbo-preview",
        description="LLM model to use for writing (potentially different)",
    )  # Example: different model
    max_tokens: int = Field(
        2000, description="Max tokens for writing LLM response"
    )  # Example: more tokens

class DreamscapeConfig(BaseModel):
    # NOTE (Captain-Agent-5): This config section appears specific to a
    # 'Dreamscape' planner/writer application. Review if this is still actively
    # used or belongs in the core configuration vs. an application-specific layer.
    planner_agent: DreamscapePlannerAgentConfig = Field(
        default_factory=DreamscapePlannerAgentConfig
    )
    writer_agent: DreamscapeWriterAgentConfig = Field(
        default_factory=DreamscapeWriterAgentConfig
    ) 