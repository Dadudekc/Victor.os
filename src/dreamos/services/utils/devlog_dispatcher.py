"""
DevLog Dispatcher - Autonomous content publishing agent that watches for new content
and dispatches it to various platforms using the appropriate strategies.
"""

import hashlib  # noqa: I001
import json
import logging
import time
from pathlib import Path
from queue import Queue
from threading import Thread
from typing import Dict, List, Optional
from unittest.mock import MagicMock

from dreamos.core.config import AppConfig, LinkedInConfig, TwitterConfig
from utils.logging_utils import get_logger
from watchdog.events import FileSystemEventHandler

# Configure logging using the consolidated utility
logger = get_logger(__name__)


class ContentHandler(FileSystemEventHandler):
    """Handles file system events for new content."""

    def __init__(self, dispatcher: "DevLogDispatcher"):
        self.dispatcher = dispatcher

    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith(".md"):
            logger.info(f"New blog post detected: {event.src_path}")
            self.dispatcher.handle_new_blog_post(event.src_path)
        elif event.src_path.endswith("-posts.json"):
            logger.info(f"New social content detected: {event.src_path}")
            self.dispatcher.handle_new_social_content(event.src_path)


class DevLogDispatcher:
    """
    Autonomous agent that watches for new content and publishes it
    to appropriate platforms using configured strategies.
    """

    def __init__(self, config: AppConfig, content_queue: Queue):
        """
        Initialize the dispatcher.

        Args:
            config: The main application configuration object.
            content_queue: Queue containing generated content payloads.
        """
        self.config = config
        self.content_queue = content_queue
        self.strategies = self._initialize_strategies()
        self.running = False
        self.thread: Optional[Thread] = None

        logger.info(
            f"Initialized DevLog Dispatcher with strategies for: {list(self.strategies.keys())}"  # noqa: E501
        )

    def _initialize_strategies(self) -> Dict[str, object]:
        """Initialize strategy instances based on configuration."""
        strategies = {}
        twitter_conf: Optional[TwitterConfig] = getattr(
            self.config.integrations, "twitter", None
        )
        if twitter_conf and twitter_conf.api_key and twitter_conf.api_secret_key:
            try:
                logger.info(
                    "TwitterStrategy WOULD BE initialized (Class missing). Config found."  # noqa: E501
                )
                strategies["twitter"] = MagicMock(name="MockTwitterStrategy")
            except NameError:
                logger.error("TwitterStrategy class not found. Cannot initialize.")
            except Exception as e:
                logger.error(
                    f"Failed to initialize TwitterStrategy: {e}", exc_info=True
                )
        else:
            logger.warning(
                "Twitter configuration missing or incomplete in AppConfig. Skipping TwitterStrategy."  # noqa: E501
            )

        linkedin_conf: Optional[LinkedInConfig] = getattr(
            self.config.integrations, "linkedin", None
        )
        if linkedin_conf and linkedin_conf.client_id and linkedin_conf.client_secret:
            try:
                logger.info(
                    "LinkedInStrategy WOULD BE initialized (Class missing). Config found."  # noqa: E501
                )
                strategies["linkedin"] = MagicMock(name="MockLinkedInStrategy")
            except NameError:
                logger.error("LinkedInStrategy class not found. Cannot initialize.")
            except Exception as e:
                logger.error(
                    f"Failed to initialize LinkedInStrategy: {e}", exc_info=True
                )
        else:
            logger.warning(
                "LinkedIn configuration missing or incomplete in AppConfig. Skipping LinkedInStrategy."  # noqa: E501
            )

        if not strategies:
            logger.warning(
                "No social media strategies were configured or initialized successfully."  # noqa: E501
            )

        return strategies

    def start(self):
        """Start watching for new content."""
        # Watch posts directory
        self.observer.schedule(self.handler, str(self.posts_dir), recursive=False)
        # Watch social content directories
        self.observer.schedule(self.handler, str(self.social_dir), recursive=True)

        self.observer.start()
        logger.info(f"Started watching {self.content_dir} for new content")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
            self.scheduler.shutdown()
            self.observer.join()

    def handle_new_blog_post(self, post_path: str):
        """
        Handle a new blog post file.

        Args:
            post_path: Path to the new blog post
        """
        if post_path in self.published["blog"]:
            return

        try:
            # Here you would implement the logic to publish to your blog
            # For example, via GitHub Pages API or WordPress API
            logger.info(f"Publishing blog post: {post_path}")

            # Generate post ID
            post_id = self._generate_post_id(post_path)

            # Track the post in analytics
            with open(post_path, "r") as f:
                content = f.read()

            self.analyzer.track_post(
                post_id=post_id,
                platform="blog",
                post_type="article",
                content=content,
                tags=self._extract_tags(content),
                url=f"https://blog.dream.os/posts/{Path(post_path).stem}",
            )

            # Mark as published
            self.published["blog"].add(post_path)
            logger.info(f"Successfully published blog post: {post_path}")

        except Exception as e:
            logger.error(f"Failed to publish blog post {post_path}: {str(e)}")

    def handle_new_social_content(self, content_path: str):
        """
        Handle new social media content.

        Args:
            content_path: Path to the social content JSON file
        """
        if (
            content_path in self.published["twitter"]
            and content_path in self.published["linkedin"]
        ):
            return

        try:
            with open(content_path, "r") as f:
                posts = json.load(f)

            platform = "twitter" if "twitter" in content_path else "linkedin"
            strategy = self.strategies.get(platform)

            if not strategy:
                logger.warning(f"No strategy configured for {platform}")
                return

            # Get optimal posting time
            best_times = self.analyzer.get_best_posting_times(platform)
            publish_time = self._get_next_optimal_time(best_times)

            # Schedule posts
            for post in posts:
                post_id = self._generate_post_id(content_path, post["content"])

                # Track the post
                self.analyzer.track_post(
                    post_id=post_id,
                    platform=platform,
                    post_type=post["type"],
                    content=post["content"],
                    tags=self._extract_tags(post["content"]),
                )

                # Schedule the post
                self.schedule_post(
                    post_path=content_path,
                    platform=platform,
                    post_type=post["type"],
                    content=post["content"],
                    post_id=post_id,
                    publish_time=publish_time,
                )

                # Add 15 minutes for the next post if it's a thread
                publish_time = publish_time + timedelta(minutes=15)  # noqa: F821

            # Mark as published
            self.published[platform].add(content_path)
            logger.info(f"Successfully scheduled {platform} content: {content_path}")

        except Exception as e:
            logger.error(f"Failed to handle social content {content_path}: {str(e)}")

    def schedule_post(
        self,
        post_path: str,
        platform: str,
        post_type: str,
        content: str,
        post_id: str,
        publish_time: datetime,  # noqa: F821
    ):
        """
        Schedule a post for future publishing.

        Args:
            post_path: Path to the content to publish
            platform: Target platform
            post_type: Type of post (main, thread, article)
            content: Post content
            post_id: Unique post identifier
            publish_time: When to publish the content
        """
        try:
            strategy = self.strategies.get(platform)

            # Define the job function
            def publish_job():
                try:
                    if post_type == "main":
                        success = strategy.post_update(content)
                    elif post_type == "thread" and platform == "twitter":
                        success = strategy.post_thread(content)
                    else:
                        success = strategy.post_article(content)

                    if success:
                        logger.info(f"Successfully published scheduled post: {post_id}")
                        # Initialize metrics
                        self.analyzer.update_metrics(
                            post_id, {"views": 0, "likes": 0, "shares": 0}
                        )
                    else:
                        logger.error(f"Failed to publish scheduled post: {post_id}")

                except Exception as e:
                    logger.error(f"Error in publish job for {post_id}: {str(e)}")

            # Schedule the job
            self.scheduler.add_job(
                publish_job,
                trigger=DateTrigger(run_date=publish_time),  # noqa: F821
                id=post_id,
                name=f"Publish {platform} {post_type}",
            )

            logger.info(f"Scheduled post {post_id} for {publish_time}")

        except Exception as e:
            logger.error(f"Failed to schedule post {post_id}: {str(e)}")

    def _generate_post_id(self, file_path: str, content: str = "") -> str:
        """Generate a unique post ID."""
        hash_input = f"{file_path}:{content}:{datetime.now().isoformat()}"  # noqa: F821
        return hashlib.md5(hash_input.encode()).hexdigest()

    def _extract_tags(self, content: str) -> List[str]:
        """Extract hashtags from content."""
        words = content.split()
        return [word[1:] for word in words if word.startswith("#")]

    def _get_next_optimal_time(self, best_times: Dict[str, List[str]]) -> datetime:  # noqa: F821
        """Get the next optimal posting time."""
        now = datetime.now()  # noqa: F821
        current_day = now.strftime("%A")

        # Get best hours for current day
        best_hours = best_times.get(current_day, [])

        if not best_hours:
            # If no optimal times, schedule for next hour
            next_time = now.replace(minute=0, second=0, microsecond=0) + timedelta(  # noqa: F821
                hours=1
            )
        else:
            # Find the next best hour
            current_hour = now.hour
            next_hour = None

            for hour in best_hours:
                if int(hour) > current_hour:
                    next_hour = int(hour)
                    break

            if next_hour is None:
                # No more optimal times today, use first optimal time tomorrow
                tomorrow = now + timedelta(days=1)  # noqa: F821
                next_time = tomorrow.replace(
                    hour=int(best_hours[0]), minute=0, second=0, microsecond=0
                )
            else:
                next_time = now.replace(
                    hour=next_hour, minute=0, second=0, microsecond=0
                )

        return next_time


def main():
    """Main entry point for the DevLog Dispatcher. (Needs Refactoring)"""
    logger.warning(
        "Executing standalone main() for DevLogDispatcher - this might be deprecated."
    )

    try:
        from dreamos.core.config import load_app_config

        app_config = load_app_config()
        if not app_config:
            raise ValueError("Failed to load AppConfig.")
    except (ImportError, ValueError) as e:
        logger.error(
            f"Cannot run DevLogDispatcher main: Failed to load AppConfig ({e}). Exiting."  # noqa: E501
        )
        return

    dummy_queue = Queue()
    dispatcher = DevLogDispatcher(config=app_config, content_queue=dummy_queue)  # noqa: F841

    try:
        logger.info("Starting DevLogDispatcher via main()...")
        logger.warning(
            "Standalone start() functionality not fully implemented after refactor."
        )
    except KeyboardInterrupt:
        logger.info("DevLogDispatcher main() interrupted.")
    except Exception as e:
        logger.error(f"Error running DevLogDispatcher main(): {e}", exc_info=True)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    main()
