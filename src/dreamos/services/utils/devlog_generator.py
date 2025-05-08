"""
DevLog Content Generator - Transform ChatGPT conversations into engaging developer content.
Processes chat history into structured blog posts, technical articles, and social media content.
"""  # noqa: E501

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dreamos.utils.common_utils import get_utc_iso_timestamp

# import markdown # Removed as per Vulture
from jinja2 import Environment, FileSystemLoader

from dreamos.core.config import AppConfig # Use absolute path for clarity
# from ..config import settings  # Using relative import consistently # REMOVE THIS IMPORT
from ..core.strategies.linkedin_strategy import LinkedInStrategy

# from utils.chatgpt_scraper import ChatGPTScraper # This causes circular import, remove if ChatGPTScraper doesn't need DevLogGenerator  # noqa: E501
# from utils.strategies import TwitterStrategy, LinkedInStrategy # Incorrect import
# Correct imports assuming strategies are in social/core/strategies/
from ..core.strategies.twitter_strategy import TwitterStrategy
# from .logging_utils import get_logger  # Import get_logger
from dreamos.services.utils.logging_utils import get_logger # UPDATED IMPORT

# Configure logging using the consolidated utility
logger = get_logger(__name__)  # Use __name__ for module-level logger


@dataclass
class ContentBlock:
    """Represents a block of content from the conversation."""

    type: str  # 'question', 'explanation', 'code', 'error', 'solution'
    content: str
    metadata: Dict[str, Any]
    timestamp: datetime


@dataclass
class DevLogPost:
    """Represents a structured blog post from a conversation."""

    title: str
    description: str
    date: datetime
    tags: List[str]
    content_blocks: List[ContentBlock]
    code_snippets: List[Dict[str, str]]
    challenges: List[str]
    solutions: List[str]
    key_learnings: List[str]


class DevLogGenerator:
    """Transforms ChatGPT conversations into various content formats."""

    def __init__(self, config: AppConfig, strategies: Optional[Dict[str, Any]] = None):
        """
        Initialize the generator.

        Args:
            config: The application configuration object.
            strategies: Optional dictionary of strategies for different platforms.
                        If None, strategies will be loaded from config.
        """
        self.config = config
        # TODO: Confirm template directory source (config or hardcoded relative to project root?)
        # Using AppConfig for template path
        if not config or not config.paths or not config.paths.templates:
            raise ValueError("AppConfig with paths.templates must be provided.")

        self.template_dir = config.paths.templates.resolve()

        if not self.template_dir.is_dir():
             logger.error(
                 f"Template directory specified in config does not exist or is not a directory: {self.template_dir}"
             )
             # Optionally raise an error or proceed with caution
             # raise FileNotFoundError(f"Template directory not found: {self.template_dir}")

        # Ensure template_dir is passed as a string or Path object to FileSystemLoader
        try:
             self.env = Environment(
                 loader=FileSystemLoader(str(self.template_dir)), autoescape=True
             )  # Enable autoescape for security
             # Add timestamp function to Jinja globals
             self.env.globals["iso_timestamp_utc"] = get_utc_iso_timestamp
             logger.info("Initialized DevLog Generator")
             logger.info(
                 f"Jinja Environment configured with template path: {self.template_dir}"
             )
        except Exception as e:
             logger.error(f"Failed to initialize Jinja environment: {e}", exc_info=True)
             # Raise or handle appropriately
             raise RuntimeError("Failed to setup Jinja environment") from e
        
        if strategies is None:
            self.strategies = self._load_strategies_from_config()
        else:
            self.strategies = strategies
        logger.info(f"DevLogGenerator initialized with {len(self.strategies)} strategies.")

    def _load_strategies_from_config(self) -> Dict[str, Any]:
        """Loads publishing strategies from the AppConfig."""
        loaded_strategies = {}
        # Example: Assuming AppConfig has direct attributes like 'twitter_config', 'linkedin_config'
        #          or a nested structure like 'config.strategy_settings.twitter'
        #          Adjust the paths below based on the actual AppConfig structure.

        # Twitter Strategy
        # FIXME: Ensure AppConfig has these attributes (e.g., config.twitter_config)
        #        and that they contain the necessary parameters for strategy instantiation.
        #        The original 'settings.TWITTER_CONFIG.get("api_key")' implies a dict structure.
        twitter_conf = getattr(self.config, "twitter_config", None)
        if twitter_conf and isinstance(twitter_conf, dict) and twitter_conf.get("api_key"): # Check if configured
            try:
                loaded_strategies["twitter"] = TwitterStrategy(**twitter_conf)
                logger.info("Initialized TwitterStrategy from config.")
            except Exception as e:
                logger.error(f"Failed to initialize TwitterStrategy from config: {e}")
        
        # LinkedIn Strategy
        # FIXME: Ensure AppConfig has these attributes (e.g., config.linkedin_config)
        linkedin_conf = getattr(self.config, "linkedin_config", None)
        if linkedin_conf and isinstance(linkedin_conf, dict) and linkedin_conf.get("client_id"): # Check if configured
            try:
                loaded_strategies["linkedin"] = LinkedInStrategy(**linkedin_conf)
                logger.info("Initialized LinkedInStrategy from config.")
            except Exception as e:
                logger.error(f"Failed to initialize LinkedInStrategy from config: {e}")
        
        # Add other strategies similarly
        if not loaded_strategies:
            logger.warning("No publishing strategies were loaded from the configuration.")
        return loaded_strategies

    def process_conversation(self, chat_data: Dict[str, Any]) -> DevLogPost:
        """
        Process a single conversation into a structured blog post.

        Args:
            chat_data: Raw chat data from scraper

        Returns:
            DevLogPost: Structured blog post
        """
        # Extract messages and metadata
        messages = chat_data.get("messages", [])

        # Initialize content blocks
        content_blocks = []
        code_snippets = []
        challenges = []
        solutions = []
        key_learnings = []

        # Process each message
        for msg in messages:
            block = self._process_message(msg)
            if block:
                content_blocks.append(block)

                # Categorize content
                if block.type == "code":
                    code_snippets.append(
                        {
                            "code": block.content,
                            "language": block.metadata.get("language", ""),
                            "description": block.metadata.get("description", ""),
                        }
                    )
                elif block.type == "error":
                    challenges.append(block.content)
                elif block.type == "solution":
                    solutions.append(block.content)

                # Extract key learnings from explanations
                if block.type == "explanation" and block.metadata.get(
                    "is_learning", False
                ):
                    key_learnings.append(block.content)

        # Generate title and description
        title = self._generate_title(content_blocks)
        description = self._generate_description(content_blocks)

        # Create DevLogPost
        return DevLogPost(
            title=title,
            description=description,
            date=datetime.now(),
            tags=self._extract_tags(content_blocks),
            content_blocks=content_blocks,
            code_snippets=code_snippets,
            challenges=challenges,
            solutions=solutions,
            key_learnings=key_learnings,
        )

    def _process_message(self, message: Dict[str, Any]) -> Optional[ContentBlock]:
        """Process a single message into a content block."""
        content = message.get("content", "").strip()
        if not content:
            return None

        # Determine message type and metadata
        metadata = {}
        msg_type = "explanation"  # default type

        # Check for code blocks
        if "```" in content:
            msg_type = "code"
            metadata["language"] = self._detect_language(content)

        # Check for errors/exceptions
        elif any(err in content.lower() for err in ["error", "exception", "failed"]):
            msg_type = "error"

        # Check for solutions
        elif any(sol in content.lower() for sol in ["solution", "fixed", "resolved"]):
            msg_type = "solution"

        # Check for questions
        elif content.strip().endswith("?"):
            msg_type = "question"

        # Extract additional metadata
        metadata.update(self._extract_metadata(content))

        return ContentBlock(
            type=msg_type,
            content=content,
            metadata=metadata,
            timestamp=datetime.fromisoformat(
                message.get("timestamp", datetime.now().isoformat())
            ),
        )

    def generate_blog_post(self, post: DevLogPost, output_file: str) -> bool:
        """
        Generate a blog post in markdown format.

        Args:
            post: Structured blog post data
            output_file: Output markdown file path

        Returns:
            bool: True if successful
        """
        try:
            template = self.env.get_template("blog_post.md.j2")
            content = template.render(post=post)

            # Add frontmatter
            import frontmatter  # Local import if not used elsewhere heavily

            post_with_frontmatter = frontmatter.Post(
                content,
                title=post.title,
                date=post.date.strftime("%Y-%m-%d"),
                tags=post.tags,
                description=post.description,
            )

            # Save to file
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            frontmatter.dump(post_with_frontmatter, output_file)

            logger.info(f"Generated blog post: {output_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to generate blog post: {str(e)}")
            return False

    def generate_social_content(
        self, post: DevLogPost, platform: str
    ) -> List[Dict[str, str]]:
        """
        Generate social media content from the blog post.

        Args:
            post: Structured blog post data
            platform: Target platform (twitter, linkedin, etc.)

        Returns:
            List[Dict[str, str]]: List of social media posts
        """
        try:
            template = self.env.get_template(f"{platform}_post.j2")
            posts = []

            # Generate main post
            main_post = template.render(
                post=post,
                title=post.title,
                description=post.description,
                key_learnings=post.key_learnings[:3],  # Top 3 learnings
                tags=post.tags,
                url=f"https://blog.dream.os/posts/{post.date.strftime('%Y-%m-%d')}-{post.title.lower().replace(' ', '-')}",  # noqa: E501
            )
            posts.append({"type": "main", "content": main_post})

            # Generate thread for key learnings if more than 3
            if len(post.key_learnings) > 3:
                thread_template = self.env.get_template(f"{platform}_thread.j2")
                thread = thread_template.render(
                    learnings=post.key_learnings[3:],
                    tags=post.tags,
                    total=len(post.key_learnings[3:]),
                )
                posts.append({"type": "thread", "content": thread})

            return posts

        except Exception as e:
            logger.error(f"Failed to generate social content: {str(e)}")
            return []

    def _generate_title(self, blocks: List[ContentBlock]) -> str:
        """Generate a title from content blocks."""
        # Find the first question or main topic
        for block in blocks:
            if block.type == "question":
                return block.content.strip("?")
        # Fallback title
        timestamp_str = (
            blocks[0].timestamp.strftime("%Y-%m-%d")
            if blocks
            else datetime.now().strftime("%Y-%m-%d")
        )
        return f"Development Log: {timestamp_str}"

    def _generate_description(self, blocks: List[ContentBlock]) -> str:
        """Generate a description from content blocks."""
        # Combine key points from explanations
        explanations = [b.content for b in blocks if b.type == "explanation"]
        desc = " ".join(explanations)
        return (desc[:197] + "...") if len(desc) > 200 else desc

    def _extract_tags(self, blocks: List[ContentBlock]) -> List[str]:
        """Extract relevant tags from content."""
        tags = set()

        # Common programming languages to detect
        languages = {
            "python",
            "javascript",
            "typescript",
            "java",
            "cpp",
            "c++",
            "ruby",
            "go",
            "rust",
            "php",
            "swift",
            "kotlin",
            "scala",
            "html",
            "css",
        }

        for block in blocks:
            # Extract from code blocks
            if block.type == "code":
                lang = block.metadata.get("language", "").lower()
                if lang in languages:
                    tags.add(lang)

            # Extract from content
            if block.type in ["explanation", "question"]:
                # Split content into words and clean them
                words = block.content.lower().split()
                for word in words:
                    # Remove special characters from word
                    clean_word = "".join(c for c in word if c.isalnum())

                    # Add programming languages
                    if clean_word in languages:
                        tags.add(clean_word)

                    # Add hashtags (but filter out function parameters)
                    if (
                        word.startswith(("#", "@"))
                        and "(" not in word
                        and ")" not in word
                    ):
                        tag = word.strip("#@")
                        if tag and not any(c in tag for c in "()=,"):
                            tags.add(tag)

        # Add some common categories based on content
        if any("api" in block.content.lower() for block in blocks):
            tags.add("api")
        if any("test" in block.content.lower() for block in blocks):
            tags.add("testing")
        if any("error" in block.content.lower() for block in blocks):
            tags.add("debugging")

        return sorted(list(tags))

    def _detect_language(self, content: str) -> str:
        """Detect programming language from code block."""
        if "```" not in content:
            return ""

        # Extract language identifier
        start = content.find("```") + 3
        end = content.find("\n", start)
        if start < end:
            return content[start:end].strip()
        return ""

    def _extract_metadata(self, content: str) -> Dict[str, Any]:
        """Extract additional metadata from content."""
        metadata = {}
        # Add metadata extraction logic here
        return metadata

    def auto_publish(
        self,
        chat_data: Dict[str, Any],
        # dispatcher: 'DevLogDispatcher', # Dispatcher likely passed separately or obtained via service locator  # noqa: E501
        blog_output_dir: str = "content/posts",
        social_output_dir: str = "content/social",
    ) -> bool:
        """
        Automatically process conversation and publish content across platforms.
        Note: Publishing logic (dispatcher) is separated. This generates files.

        Args:
            chat_data: Raw chat data from scraper
            blog_output_dir: Output directory for blog posts
            social_output_dir: Output directory for social content

        Returns:
            bool: True if all generation steps succeeded
        """
        try:
            # Process conversation into structured post
            post = self.process_conversation(chat_data)

            # Generate blog post
            blog_file = (
                Path(blog_output_dir)
                / f"{post.date.strftime('%Y-%m-%d')}-{post.title.lower().replace(' ', '-')}.md"  # noqa: E501
            )
            if not self.generate_blog_post(post, str(blog_file)):
                logger.error("Failed to generate blog post")
                return False

            # Generate social content for each platform
            for platform, strategy in self.strategies.items():
                social_content = self.generate_social_content(post, platform)
                if social_content:
                    # Save social content to trigger dispatcher later
                    social_file = (
                        Path(social_output_dir)
                        / f"{post.date.strftime('%Y-%m-%d')}-{platform}-posts.json"
                    )
                    social_file.parent.mkdir(parents=True, exist_ok=True)

                    with open(social_file, "w") as f:
                        json.dump(social_content, f, indent=2)

                    logger.info(f"Generated {platform} content: {social_file}")

            logger.info(
                "Successfully generated content from conversation for potential dispatch."  # noqa: E501
            )
            return True

        except Exception as e:
            logger.error(f"Failed to auto-generate content: {str(e)}")
            return False


# --- Main Execution Example ---
# DELETE THIS FUNCTION
# def initialize_strategies():
#     strategies = {}
#     # Use settings from config.settings
#     if settings.TWITTER_CONFIG.get("api_key"):  # Check if configured
#         strategies["twitter"] = TwitterStrategy(**settings.TWITTER_CONFIG)
#     if settings.LINKEDIN_CONFIG.get("client_id"):  # Check if configured
#         strategies["linkedin"] = LinkedInStrategy(**settings.LINKEDIN_CONFIG)
#     # Add other strategies similarly
#     return strategies


# {{ EDIT START: Update main_example to show config requirement (still commented out) }}
# def main_example():
#     logger.info("Running DevLog Generator Example")
#
#     # --- Requires proper AppConfig setup --- #
#     # try:
#     #     app_config = AppConfig.load() # Or load from a specific path
#     # except Exception as e:
#     #     logger.error(f"Failed to load AppConfig: {e}. Cannot run example.")
#     #     return
#     # --- End AppConfig Setup --- #
#
#     # Strategies are now loaded internally by DevLogGenerator if not provided
#     # generator = DevLogGenerator(config=app_config) 
#
#     # ... (rest of example assumes generator is created and might need mock chat_data)
# {{ EDIT END }}
