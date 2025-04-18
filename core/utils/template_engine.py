"""General purpose template engine for rendering prompts and other templates."""
import os
import logging
from typing import Dict, Any
from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound

logger = logging.getLogger(__name__)

class TemplateEngine:
    """Engine for rendering Jinja2 templates from a specified directory."""
    
    def __init__(self, template_dir: str = None):
        """
        Initialize the template engine.
        
        Args:
            template_dir (str, optional): Path to the template directory. 
                                         Defaults to '<project_root>/templates'.
        """
        if template_dir:
            self.template_dir = os.path.abspath(template_dir)
        else:
            # Default: Go up two levels from core/utils/ to project root, then find 'templates'
            self.template_dir = os.path.abspath(os.path.join(
                os.path.dirname(__file__), '..', '..', 'templates' 
            ))
        
        logger.info(f"Initializing TemplateEngine with template directory: {self.template_dir}")
        self._ensure_template_dir()
        self._setup_environment()
        
    def _ensure_template_dir(self) -> None:
        """Ensure template directory exists."""
        if not os.path.isdir(self.template_dir):
            logger.warning(f"Template directory not found: {self.template_dir}. Creating it.")
            try:
                os.makedirs(self.template_dir, exist_ok=True)
            except OSError as e:
                 logger.error(f"Failed to create template directory {self.template_dir}: {e}", exc_info=True)
                 raise # Re-raise if directory creation fails
        
    def _setup_environment(self) -> None:
        """Set up the Jinja2 environment."""
        try:
            self.env = Environment(
                loader=FileSystemLoader(self.template_dir),
                undefined=StrictUndefined, # Raise errors for undefined variables
                trim_blocks=True,
                lstrip_blocks=True,
                autoescape=False # Typically False for code/prompt generation
            )
            logger.debug("Jinja2 environment configured.")
        except Exception as e:
             logger.error(f"Failed to set up Jinja2 environment for {self.template_dir}: {e}", exc_info=True)
             raise
        
    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render a template with given context."""
        logger.debug(f"Rendering template '{template_name}' with context keys: {list(context.keys())}")
        try:
            template = self.env.get_template(template_name)
            rendered_content = template.render(**context)
            logger.info(f"Successfully rendered template '{template_name}'.")
            return rendered_content
        except TemplateNotFound:
            logger.error(f"Template '{template_name}' not found in directory {self.template_dir}.")
            raise
        except Exception as e:
            logger.error(f"Error rendering template '{template_name}': {e}", exc_info=True)
            raise
            
    def add_filter(self, name: str, filter_func: callable) -> None:
        """Add a custom filter to the environment."""
        self.env.filters[name] = filter_func
        logger.debug(f"Added custom filter '{name}' to Jinja2 environment.")
        
    def add_global(self, name: str, value: Any) -> None:
        """Add a global variable to the environment."""
        self.env.globals[name] = value
        logger.debug(f"Added global variable '{name}' to Jinja2 environment.")

# Optional: Create a default instance if widely used across modules
# Be mindful of initialization path if created here at import time.
# default_template_engine = TemplateEngine() 