"""
Template engine for rendering fragments and other templated content.
"""

import logging
from typing import Any, Dict

import jinja2

logger = logging.getLogger(__name__)


class TemplateEngine:
    """Wraps Jinja2 for rendering template strings."""

    def __init__(self):
        # Basic Jinja2 environment
        self.env = jinja2.Environment(
            loader=jinja2.DictLoader({}),  # No file loading by default
            autoescape=jinja2.select_autoescape(["html", "xml"]),  # Basic autoescaping
            undefined=jinja2.StrictUndefined,  # Raise errors for undefined variables
        )
        logger.info("TemplateEngine initialized with basic Jinja2 environment.")

    def render(self, template_string: str, context: Dict[str, Any]) -> str:
        """
        Renders a template string with the given context.

        Args:
            template_string (str): The Jinja2 template string.
            context (Dict[str, Any]): A dictionary containing variables for the template.

        Returns:
            str: The rendered output string.

        Raises:
            jinja2.TemplateError: If there is an error during template parsing or rendering.
            Exception: For other unexpected errors.
        """  # noqa: E501
        if not isinstance(template_string, str):
            logger.error("Template must be a string.")
            raise TypeError("Template must be a string.")

        try:
            template = self.env.from_string(template_string)
            rendered_output = template.render(context)
            logger.debug(
                f"Successfully rendered template string. Output length: {len(rendered_output)}"  # noqa: E501
            )
            return rendered_output
        except jinja2.TemplateError as e:
            logger.error(f"Jinja2 template error: {e}", exc_info=True)
            # Return a formatted error message instead of raising?
            # Or re-raise for the caller to handle
            raise  # Re-raise Jinja2 errors
        except Exception as e:
            logger.error(
                f"Unexpected error during template rendering: {e}", exc_info=True
            )
            raise  # Re-raise other errors


# Example Usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    engine = TemplateEngine()

    template1 = "Hello, {{ name }}! You have {{ count }} messages."
    context1 = {"name": "Dreamer", "count": 5}

    template2 = """
    Fragment: {{ fragment.name | default('Untitled') }}
    Author: {{ fragment.author | default('N/A') }}
    Rank: {{ fragment.rank }}
    Tags: {{ fragment.tags | join(', ') }}

    {{ fragment.core_text }}
    """
    context2 = {
        "fragment": {
            "name": "Test Fragment",
            "author": "AI Assistant",
            "rank": "A",
            "tags": ["test", "example"],
            "core_text": "This is the core text of the test fragment.",
        }
    }

    template_invalid = "Hello, {{ name "  # Syntax error
    context_invalid = {"name": "Test"}

    print("--- Rendering Template 1 ---")
    try:
        output1 = engine.render(template1, context1)
        print(output1)
    except Exception as e:
        print(f"Error: {e}")

    print("\n--- Rendering Template 2 (Fragment) ---")
    try:
        output2 = engine.render(template2, context2)
        print(output2)
    except Exception as e:
        print(f"Error: {e}")

    print("\n--- Rendering Invalid Template ---")
    try:
        output3 = engine.render(template_invalid, context_invalid)
        print(output3)
    except Exception as e:
        print(f"Error: {e}")
