"""
Re-exports key functions/classes for easier import from the GUI layer.
"""

# Functions from the new generation engine stub
from .generation_engine import build_context, generate_episode  # noqa: F401

# Method from the scraper, aliased for the GUI's expectation
# Note: This imports the *class* if send_prompt is a method,
# but we need the function. Let's alias the scraper's send_prompt method.
# This assumes the user will instantiate the scraper and call the method.
# However, the GUI code expects a function.
# Let's adjust the generation_engine to handle this.

# *** Revised thinking: The __init__.py should export the functions the GUI *actually* needs. ***
# build_context and generate_episode are correctly handled by the above line.
# send_prompt_to_chatgpt is NOT directly called by the GUI in the latest GUI code.
# The GUI calls generate_episode, which *internally* uses the scraper.
# Therefore, we only need to export build_context and generate_episode.

# Let's simplify the export:
__all__ = ["build_context", "generate_episode"]
