import sys
import os
import logging
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QTabWidget
from PySide6.QtCore import QThread, Signal

# Assuming dreamscape_generator is importable
try:
    from dreamscape_generator import config as project_config
    # Import other managers as needed later
    from dreamscape_generator.core.MemoryManager import MemoryManager
    from dreamscape_generator.chatgpt_scraper import ChatGPTScraper # Needed for chat list
    from dreamscape_generator.story_generator import StoryGenerator
    # Import GUI tabs
    from .dreamscape_tab import DreamscapeTabWidget
except ImportError as e:
    print(f"Error: Failed to import dreamscape_generator components: {e}", file=sys.stderr)
    print("Please ensure dreamscape_generator is installed or PYTHONPATH is set correctly.", file=sys.stderr)
    sys.exit(1)

# Configure logging (consider a GUI-friendly handler later)
logging.basicConfig(level=project_config.LOG_LEVEL, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DreamscapeGUI")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dreamscape - AI-Powered Community Management")
        self.setGeometry(100, 100, 1200, 800) # Adjust size as needed

        # --- Initialize Backend Components ---
        # Handle potential errors during initialization
        try:
            logger.info("Initializing backend components...")
            # Ensure necessary directories exist (config might do this, but double-check)
            os.makedirs(project_config.EPISODE_DIR, exist_ok=True)
            os.makedirs(project_config.MEMORY_DIR, exist_ok=True) # If MemoryManager uses it

            # TODO: Add error handling for missing API keys or failed initializations
            self.memory_manager = MemoryManager() # Uses default path from config
            self.scraper = ChatGPTScraper(
                profile_path=project_config.SELENIUM_PROFILE_PATH,
                user_data_dir=project_config.SELENIUM_USER_DATA_DIR
            )
            # TODO: Initialize ContextManager, ExperienceParser, DiscordManager later
            # self.context_manager = ContextManager(...)
            # self.experience_parser = ExperienceParser()
            # self.discord_manager = StubDiscordManager() # Or the real one
            # self.story_generator = StoryGenerator(
            #     memory_manager=self.memory_manager,
            #     context_manager=self.context_manager,
            #     experience_parser=self.experience_parser,
            #     chat_scraper=self.scraper,
            #     # discord_manager=self.discord_manager
            # )
            logger.info("Backend components initialized (partially).") # Update when fully initialized
        except Exception as e:
            logger.error(f"Failed to initialize backend components: {e}", exc_info=True)
            # Optionally show an error message to the user here
            # For now, we might allow the GUI to load but features will fail.

        # --- Setup UI ---
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.tab_widget = QTabWidget()
        self.layout.addWidget(self.tab_widget)

        # Initialize and add tabs
        # Pass necessary backend components to the tabs
        self.dreamscape_tab = DreamscapeTabWidget(scraper=self.scraper) # Pass scraper for chat list
        # self.prompt_execution_tab = QWidget() # Placeholder
        # self.discord_tab = QWidget() # Placeholder
        # self.aide_tab = QWidget() # Placeholder
        # self.logs_tab = QWidget() # Placeholder - maybe use a dedicated logging handler
        # self.social_dashboard_tab = QWidget() # Placeholder

        # Add Dreamscape tab first
        self.tab_widget.addTab(self.dreamscape_tab, "Dreamscape")
        # self.tab_widget.addTab(self.prompt_execution_tab, "Prompt Execution")
        # Add other tabs here...

        # TODO: Add bottom status bar, buttons etc. if needed

    def closeEvent(self, event):
        # Clean up resources like scraper's browser
        logger.info("Closing application...")
        if hasattr(self, 'scraper') and self.scraper:
            self.scraper.close()
        # Add cleanup for threads if any are running
        super().closeEvent(event)


def run_gui():
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    run_gui() 