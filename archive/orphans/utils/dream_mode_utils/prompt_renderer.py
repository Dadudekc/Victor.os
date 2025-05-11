# dream_mode/utils/prompt_renderer.py

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

logger = logging.getLogger("PromptRenderer")


class PromptRenderer:
    """Loads and renders Jinja2 templates from a specified directory."""

    def __init__(self, template_dir: str | Path):
        self.template_dir = Path(template_dir)
        if not self.template_dir.is_dir():
            logger.error(f"Template directory not found: {self.template_dir}")
            # Raise an error or handle appropriately depending on desired behavior
            raise FileNotFoundError(
                f"Template directory does not exist: {self.template_dir}"
            )

        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            trim_blocks=True,  # Removes first newline after a block
            lstrip_blocks=True,  # Strips leading whitespace from lines
        )
        logger.info(
            f"PromptRenderer initialized with template directory: {self.template_dir}"
        )

    def render(self, template_name: str, context: dict) -> str | None:
        """Renders the specified template with the given context."""
        try:
            template = self.env.get_template(template_name)
            rendered_prompt = template.render(context)
            logger.debug(f"Successfully rendered template '{template_name}'")
            return rendered_prompt
        except TemplateNotFound:
            logger.error(
                f"Template not found: '{template_name}' in {self.template_dir}"
            )
            return None
        except Exception as e:
            logger.error(
                f"Error rendering template '{template_name}': {e}", exc_info=True
            )
            return None
