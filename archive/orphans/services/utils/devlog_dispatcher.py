"""
DevLog Dispatcher - Autonomous content publishing agent that watches for new content
and dispatches it to various platforms using the appropriate strategies.
"""

import hashlib  # noqa: I001
import json
import logging
from pathlib import Path
from queue import Queue, Empty
from threading import Thread
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from dreamos.core.config import AppConfig, LinkedInConfig, TwitterConfig
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger

# Attempt to import strategies (assuming similar paths as DevLogGenerator)
# FIXME: If these strategies are not found, the dispatcher will not function.
try:
    from dreamos.core.strategies.twitter_strategy import TwitterStrategy

    TWITTER_STRATEGY_AVAILABLE = True
except ImportError:
    TwitterStrategy = None  # type: ignore
    TWITTER_STRATEGY_AVAILABLE = False
    logger.error("TwitterStrategy not found. Twitter dispatching will be disabled.")

try:
    from dreamos.core.strategies.linkedin_strategy import LinkedInStrategy

    LINKEDIN_STRATEGY_AVAILABLE = True
except ImportError:
    LinkedInStrategy = None  # type: ignore
    LINKEDIN_STRATEGY_AVAILABLE = False
    logger.error("LinkedInStrategy not found. LinkedIn dispatching will be disabled.")

# Import DevLogAnalyzer
# FIXME: Ensure DevLogAnalyzer is correctly located and its dependencies (like pandas) are managed.
try:
    from dreamos.services.utils.devlog_analyzer import DevLogAnalyzer

    ANALYZER_AVAILABLE = True
except ImportError:
    DevLogAnalyzer = None  # type: ignore
    ANALYZER_AVAILABLE = False
    logger.error("DevLogAnalyzer not found. Analytics features will be disabled.")


class ContentHandler(FileSystemEventHandler):
    """Handles file system events for new content."""

    def __init__(self, dispatcher: "DevLogDispatcher"):
        self.dispatcher = dispatcher

    def on_created(self, event):
        if event.is_directory:
            return

        # Put a dictionary or a simple tuple/object identifying type and path
        item = None
        if event.src_path.endswith(".md"):
            logger.info(f"New blog post detected by handler: {event.src_path}")
            item = {"type": "blog", "path": event.src_path}
        elif event.src_path.endswith("-posts.json"):
            logger.info(f"New social content detected by handler: {event.src_path}")
            item = {"type": "social", "path": event.src_path}

        if item:
            try:
                self.dispatcher.content_queue.put(item)
                logger.debug(f"Queued item for processing: {item}")
            except Exception as e:
                logger.error(f"Failed to queue item {item}: {e}", exc_info=True)


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
        self.running = False
        self.thread: Optional[Thread] = None
        self.worker_thread: Optional[Thread] = None

        # Initialize paths from config (FIXME: ensure these paths exist in AppConfig.paths)
        self.posts_dir = config.paths.content_output_dir / "posts"
        self.social_dir = config.paths.content_output_dir / "social"
        # self.content_dir is not clearly defined, posts_dir and social_dir cover specifics

        # Ensure directories exist
        self.posts_dir.mkdir(parents=True, exist_ok=True)
        self.social_dir.mkdir(parents=True, exist_ok=True)

        self.strategies = self._initialize_strategies()

        if ANALYZER_AVAILABLE and DevLogAnalyzer is not None:
            self.analyzer = DevLogAnalyzer(config=config)
        else:
            self.analyzer = None  # type: ignore
            logger.warning("DevLogAnalyzer not available, analytics will be limited.")

        self.published: Dict[str, set] = {
            "blog": set(),
            "twitter": set(),
            "linkedin": set(),
            # Add other platforms if strategies are added
        }

        # Initialize Watchdog observer and handler
        self.observer = Observer()
        self.handler = ContentHandler(self)

        # Initialize APScheduler
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()

        logger.info(
            f"Initialized DevLog Dispatcher with strategies for: {list(self.strategies.keys())}"
        )
        logger.info(f"Watching for blog posts in: {self.posts_dir}")
        logger.info(f"Watching for social content in: {self.social_dir}")

    def _initialize_strategies(self) -> Dict[str, object]:
        """Initialize strategy instances based on configuration."""
        strategies = {}
        twitter_conf: Optional[TwitterConfig] = getattr(
            self.config.integrations, "twitter", None
        )
        if (
            TWITTER_STRATEGY_AVAILABLE
            and TwitterStrategy is not None
            and twitter_conf
            and twitter_conf.api_key
            and twitter_conf.api_secret_key
        ):
            try:
                strategies["twitter"] = TwitterStrategy(**twitter_conf.dict())
                logger.info("TwitterStrategy initialized.")
            except Exception as e:
                logger.error(
                    f"Failed to initialize TwitterStrategy: {e}", exc_info=True
                )
        else:
            logger.warning(
                "Twitter configuration missing, incomplete, or TwitterStrategy class not available. Skipping TwitterStrategy."
            )

        linkedin_conf: Optional[LinkedInConfig] = getattr(
            self.config.integrations, "linkedin", None
        )
        if (
            LINKEDIN_STRATEGY_AVAILABLE
            and LinkedInStrategy is not None
            and linkedin_conf
            and linkedin_conf.client_id
            and linkedin_conf.client_secret
        ):
            try:
                strategies["linkedin"] = LinkedInStrategy(**linkedin_conf.dict())
                logger.info("LinkedInStrategy initialized.")
            except Exception as e:
                logger.error(
                    f"Failed to initialize LinkedInStrategy: {e}", exc_info=True
                )
        else:
            logger.warning(
                "LinkedIn configuration missing, incomplete, or LinkedInStrategy class not available. Skipping LinkedInStrategy."
            )

        if not strategies:
            logger.warning(
                "No social media strategies were configured or initialized successfully."
            )

        return strategies

    def start(self):
        """Start watching for new content and processing the queue."""
        if self.running:
            logger.warning("DevLogDispatcher already running.")
            return
        self.running = True

        # Watchdog setup
        self.observer.schedule(self.handler, str(self.posts_dir), recursive=False)
        self.observer.schedule(self.handler, str(self.social_dir), recursive=True)
        self.observer.start()
        logger.info(
            f"Started watching for new content in {self.posts_dir} and {self.social_dir}"
        )

        # Start the content queue worker thread
        self.worker_thread = Thread(target=self._process_content_queue, daemon=True)
        self.worker_thread.start()
        logger.info("Started content queue worker thread.")

    def stop(self):
        """Stops the dispatcher, observer, and scheduler."""
        if not self.running:
            logger.warning("DevLogDispatcher not running or already stopped.")
            return
        self.running = False
        logger.info("Stopping DevLog Dispatcher...")

        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
            logger.info("Watchdog observer stopped.")

        if self.scheduler.running:
            try:
                self.scheduler.shutdown()
                logger.info("APScheduler stopped.")
            except Exception as e:
                logger.error(f"Error shutting down APScheduler: {e}")

        if self.worker_thread and self.worker_thread.is_alive():
            logger.info(
                "Stopping content queue worker thread... (will process remaining items if queue is not empty)"
            )
            self.content_queue.put(None)
            self.worker_thread.join(timeout=10)

        logger.info("DevLog Dispatcher stopped.")

    def _process_content_queue(self):
        """Worker method to process items from the content_queue."""
        logger.info("Content queue worker started.")
        while self.running:
            try:
                item = self.content_queue.get(timeout=1)
                if item is None:
                    logger.info("Content queue worker received stop signal.")
                    break

                content_type = item.get("type")
                content_path = item.get("path")

                if content_type == "blog":
                    self.handle_new_blog_post(content_path)
                elif content_type == "social":
                    self.handle_new_social_content(content_path)
                else:
                    logger.warning(f"Unknown content type in queue: {content_type}")

                self.content_queue.task_done()
            except Empty:
                continue
            except Exception as e:
                logger.error(
                    f"Error processing item from content queue: {e}", exc_info=True
                )
        logger.info("Content queue worker finished.")

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
                if publish_time:
                    publish_time = publish_time + timedelta(minutes=15)

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
        publish_time: datetime,
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
                trigger=DateTrigger(run_date=publish_time),
                id=post_id,
                name=f"Publish {platform} {post_type}",
            )

            logger.info(f"Scheduled post {post_id} for {publish_time}")

        except Exception as e:
            logger.error(f"Failed to schedule post {post_id}: {str(e)}")

    def _generate_post_id(self, file_path: str, content: str = "") -> str:
        """Generate a unique post ID."""
        hash_input = f"{file_path}:{content}:{datetime.now().isoformat()}"
        return hashlib.md5(hash_input.encode()).hexdigest()

    def _extract_tags(self, content: str) -> List[str]:
        """Extract hashtags from content."""
        words = content.split()
        return [word[1:] for word in words if word.startswith("#")]

    def _get_next_optimal_time(self, best_times: Dict[str, List[str]]) -> datetime:
        """Get the next optimal posting time."""
        now = datetime.now()
        current_day = now.strftime("%A")

        # Get best hours for current day
        best_hours = best_times.get(current_day, [])

        if not best_hours:
            # If no optimal times, schedule for next hour
            next_time = now.replace(minute=0, second=0, microsecond=0) + timedelta(
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
                tomorrow = now + timedelta(days=1)
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
            f"Cannot run DevLogDispatcher main: Failed to load AppConfig ({e}). Exiting."
        )
        return

    dummy_queue = Queue()
    dispatcher = DevLogDispatcher(config=app_config, content_queue=dummy_queue)

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
