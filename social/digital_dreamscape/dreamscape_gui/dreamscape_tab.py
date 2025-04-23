import sys
import os
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QCheckBox, QComboBox,
    QTextEdit, QTabWidget, QLabel, QSplitter, QSizePolicy, QGroupBox, QFormLayout, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal

# Assuming dreamscape_generator is importable
try:
    from dreamscape_generator import config as project_config
    from dreamscape_generator.chatgpt_scraper import ChatGPTScraper
except ImportError as e:
    # This should not happen if main_window imported correctly, but good practice
    print(f"Error: Failed to import dreamscape_generator components in tab: {e}", file=sys.stderr)
    sys.exit(1)

logger = logging.getLogger("DreamscapeGUI.Tab")

# --- Worker Threads ---
class ChatListWorker(QThread):
    """Worker thread to fetch chat list without blocking GUI."""
    finished = Signal(list) # Signal emitting the list of chats
    error = Signal(str)     # Signal emitting error messages

    def __init__(self, scraper: ChatGPTScraper):
        super().__init__()
        self.scraper = scraper

    def run(self):
        try:
            logger.info("ChatListWorker starting...")
            # Ensure scraper is ready (might need a dedicated setup method?)
            # For now, assume scraper is usable or get_all_chat_titles handles setup
            chat_list = self.scraper.get_all_chat_titles() # This is the blocking call
            logger.info(f"ChatListWorker finished, found {len(chat_list)} chats.")
            self.finished.emit(chat_list)
        except Exception as e:
            logger.error(f"Error fetching chat list in worker thread: {e}", exc_info=True)
            self.error.emit(f"Failed to fetch chat list: {e}")

# --- GUI Tab Widget ---
class DreamscapeTabWidget(QWidget):
    def __init__(self, scraper: ChatGPTScraper, parent=None):
        super().__init__(parent)
        self.scraper = scraper
        self.chat_list_worker = None # To hold the worker thread instance

        self._init_ui()
        self._load_initial_data()

    def _init_ui(self):
        # Main layout: Splitter for left controls and right display
        main_splitter = QSplitter(Qt.Horizontal)
        self.layout = QHBoxLayout(self)
        self.layout.addWidget(main_splitter)

        # --- Left Panel (Controls) ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setAlignment(Qt.AlignTop)

        # Episodes List Box
        episode_group = QGroupBox("Dreamscape Episodes")
        episode_layout = QVBoxLayout()
        self.episode_list = QListWidget()
        self.refresh_button = QPushButton("Refresh Episodes")
        episode_layout.addWidget(self.episode_list)
        episode_layout.addWidget(self.refresh_button)
        episode_group.setLayout(episode_layout)
        left_layout.addWidget(episode_group)

        # Generation Controls Box
        gen_controls_group = QGroupBox("Generation Controls")
        gen_controls_layout = QFormLayout()
        self.headless_checkbox = QCheckBox("Headless Mode")
        self.discord_checkbox = QCheckBox("Post to Discord")
        self.reverse_checkbox = QCheckBox("Reverse Order") # Still needs clarification
        self.model_combo = QComboBox()
        self.model_combo.addItems(["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]) # Example models
        # TODO: Populate from config?
        gen_controls_layout.addRow(self.headless_checkbox)
        gen_controls_layout.addRow(self.discord_checkbox)
        gen_controls_layout.addRow(self.reverse_checkbox)
        gen_controls_layout.addRow(QLabel("Model:"), self.model_combo)
        gen_controls_group.setLayout(gen_controls_layout)
        left_layout.addWidget(gen_controls_group)

        # Generation Action Buttons
        self.generate_button = QPushButton("Generate Episodes")
        self.cancel_button = QPushButton("Cancel Generation")
        self.cancel_button.setEnabled(False) # Initially disabled
        left_layout.addWidget(self.generate_button)
        left_layout.addWidget(self.cancel_button)

        # ChatGPT Context/Target Box
        chat_context_group = QGroupBox("ChatGPT Interaction")
        chat_context_layout = QVBoxLayout()
        self.send_context_button = QPushButton("Send Context to ChatGPT") # Needs clarification
        self.schedule_checkbox = QCheckBox("Schedule Auto-Updates")
        self.schedule_duration_combo = QComboBox()
        self.schedule_duration_combo.addItems(["1 day", "7 days", "30 days"]) # Example durations
        self.target_chat_combo = QComboBox()
        self.target_chat_combo.addItem("Loading chats...")
        self.target_chat_combo.setEnabled(False)
        self.save_schedule_button = QPushButton("Save Schedule")
        chat_context_layout.addWidget(self.send_context_button)
        chat_context_layout.addWidget(self.schedule_checkbox)
        chat_context_layout.addWidget(self.schedule_duration_combo)
        chat_context_layout.addWidget(QLabel("Target Chat:"))
        chat_context_layout.addWidget(self.target_chat_combo)
        chat_context_layout.addWidget(self.save_schedule_button)
        chat_context_group.setLayout(chat_context_layout)
        left_layout.addWidget(chat_context_group)

        # Prompt Box
        prompt_group = QGroupBox("Prompt")
        prompt_layout = QVBoxLayout()
        self.process_all_checkbox = QCheckBox("Process All Chats")
        self.prompt_textedit = QTextEdit()
        self.prompt_textedit.setPlaceholderText("Enter your prompt here... (Usage unclear)")
        prompt_layout.addWidget(self.process_all_checkbox)
        prompt_layout.addWidget(self.prompt_textedit)
        prompt_group.setLayout(prompt_layout)
        left_layout.addWidget(prompt_group)

        # Set left widget in splitter
        main_splitter.addWidget(left_widget)

        # --- Right Panel (Display Tabs) ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        self.display_tabs = QTabWidget()
        self.content_tab = QTextEdit()
        self.content_tab.setReadOnly(True)
        self.context_tab = QTextEdit()
        self.context_tab.setReadOnly(True)
        self.log_tab = QTextEdit()
        self.log_tab.setReadOnly(True)
        self.templates_tab = QTextEdit()
        self.templates_tab.setReadOnly(True)
        # TODO: Add template loading/editing?
        self.display_tabs.addTab(self.content_tab, "Content")
        self.display_tabs.addTab(self.context_tab, "Context")
        self.display_tabs.addTab(self.log_tab, "Log")
        self.display_tabs.addTab(self.templates_tab, "Templates")
        right_layout.addWidget(self.display_tabs)

        # Share button below tabs
        self.share_button = QPushButton("Share To Discord")
        right_layout.addWidget(self.share_button)

        # Set right widget in splitter
        main_splitter.addWidget(right_widget)

        # Adjust splitter sizes (optional)
        main_splitter.setSizes([350, 850]) # Adjust initial relative sizes

        # --- Connect Signals ---
        self.refresh_button.clicked.connect(self._load_episode_list)
        self.episode_list.currentItemChanged.connect(self._display_episode_content)
        self.target_chat_combo.currentIndexChanged.connect(self._on_target_chat_selected)
        # TODO: Connect Generate, Cancel, Share, etc.
        self.process_all_checkbox.stateChanged.connect(self._toggle_target_chat)
        self.send_context_button.clicked.connect(self._on_send_context)

    def _toggle_target_chat(self, state):
        """Enable/disable target chat dropdown based on 'Process All' checkbox."""
        enable_target = not self.process_all_checkbox.isChecked()
        self.target_chat_combo.setEnabled(enable_target)
        self.send_context_button.setEnabled(enable_target) # Assuming this relates to target chat
        # Enable Generate button differently based on selection
        self._update_generate_button_state()

    def _load_initial_data(self):
        """Load episodes and start chat list fetching on init."""
        self._load_episode_list()
        self._load_chat_list_async()
        self._toggle_target_chat(self.process_all_checkbox.isChecked()) # Set initial state

    def _load_episode_list(self):
        """Clears and reloads the list of episodes from the EPISODE_DIR."""
        logger.info(f"Refreshing episode list from: {project_config.EPISODE_DIR}")
        self.episode_list.clear()
        try:
            if not os.path.isdir(project_config.EPISODE_DIR):
                 logger.warning(f"Episode directory not found: {project_config.EPISODE_DIR}")
                 self.episode_list.addItem("Episode directory not found.")
                 return

            files = sorted(
                [f for f in os.listdir(project_config.EPISODE_DIR) if f.endswith('.json') and not f.endswith('.bak.json')],
                reverse=True # Show newest first by default
            )
            if not files:
                self.episode_list.addItem("No episodes found.")
            else:
                self.episode_list.addItems(files)
            logger.info(f"Found {len(files)} episodes.")
        except Exception as e:
            logger.error(f"Failed to load episode list: {e}", exc_info=True)
            self.episode_list.addItem("Error loading episodes.")

    def _display_episode_content(self, current, previous):
        """Loads and displays the content of the selected episode file."""
        if current is None:
            self.content_tab.clear()
            # Clear other tabs too?
            return

        filename = current.text()
        filepath = os.path.join(project_config.EPISODE_DIR, filename)
        logger.debug(f"Displaying content for: {filename}")
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Format and display
            content = f"Title: {data.get('metadata', {}).get('title', 'N/A')}\n"
            content += f"Source: {data.get('metadata', {}).get('source', 'N/A')}\n"
            content += f"Timestamp: {data.get('metadata', {}).get('timestamp_utc', 'N/A')}\n"
            content += f"Memory Updated: {data.get('metadata', {}).get('memory_updated', 'N/A')}\n"
            content += f"Memory Version: {data.get('metadata', {}).get('memory_version_after_update', 'N/A')}\n"
            content += "---\nNarrative:\n---\n"
            content += data.get("narrative", "[No Narrative]")
            content += "\n\n---\nExperience Update:\n---\n"
            content += json.dumps(data.get("experience_update"), indent=2) if data.get("experience_update") else "[No Update]"

            self.content_tab.setText(content)
            # TODO: Populate Context, Log (if applicable), Templates tabs

        except FileNotFoundError:
            logger.error(f"Selected episode file not found: {filepath}")
            self.content_tab.setText(f"Error: File not found\n{filepath}")
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON for episode file: {filepath}")
            self.content_tab.setText(f"Error: Invalid JSON file\n{filepath}")
        except Exception as e:
            logger.error(f"Failed to display episode content: {e}", exc_info=True)
            self.content_tab.setText(f"Error loading episode:\n{e}")

    def _load_chat_list_async(self):
        """Starts a background thread to load the chat list from the scraper."""
        if self.chat_list_worker and self.chat_list_worker.isRunning():
            logger.warning("Chat list worker already running.")
            return

        logger.info("Starting ChatListWorker thread...")
        self.target_chat_combo.clear()
        self.target_chat_combo.addItem("Loading chats...")
        self.target_chat_combo.setEnabled(False)
        # Make sure generate button is disabled while loading
        self.generate_button.setEnabled(False)

        self.chat_list_worker = ChatListWorker(self.scraper)
        self.chat_list_worker.finished.connect(self._update_chat_list_combo)
        self.chat_list_worker.error.connect(self._show_chat_list_error)
        self.chat_list_worker.start()

    def _update_chat_list_combo(self, chat_list):
        """Slot to update the Target Chat combo box when the worker finishes."""
        logger.info("Updating chat list combo box.")
        self.target_chat_combo.clear()
        if not chat_list:
            self.target_chat_combo.addItem("No chats found or scraper error.")
            self.target_chat_combo.setEnabled(False)
        else:
            # Store title and link (use UserData role for link)
            for chat in chat_list:
                title = chat.get("title", "Untitled Chat")
                link = chat.get("link", "")
                self.target_chat_combo.addItem(title, userData=link)
            self.target_chat_combo.setEnabled(not self.process_all_checkbox.isChecked()) # Enable if not 'process all'

        # Update button state now that list is loaded (or failed)
        self._update_generate_button_state()
        self.chat_list_worker = None # Clear worker reference

    def _show_chat_list_error(self, error_message):
        """Slot to handle errors reported by the chat list worker."""
        logger.error(f"Chat list worker error: {error_message}")
        self.target_chat_combo.clear()
        self.target_chat_combo.addItem(f"Error: {error_message[:50]}...") # Show truncated error
        self.target_chat_combo.setEnabled(False)
        # Update button state
        self._update_generate_button_state()
        self.chat_list_worker = None # Clear worker reference

    def _on_target_chat_selected(self, index):
        """Handle selection change in target chat combo."""
        # Enable generate button only if a valid chat is selected and 'process all' is off
        self._update_generate_button_state()
        # Potentially load context for the selected chat here?

    def _update_generate_button_state(self):
        """Enable/disable the Generate button based on current selections."""
        if self.process_all_checkbox.isChecked():
            # Enable if processing all chats (assuming scraper is available)
            can_generate = self.scraper is not None
        else:
            # Enable if a valid chat is selected in the dropdown
            current_index = self.target_chat_combo.currentIndex()
            current_link = self.target_chat_combo.itemData(current_index)
            # Check if index is valid (> -1) and has data (link), and not a placeholder item
            is_valid_selection = current_index > -1 and current_link is not None and "Loading" not in self.target_chat_combo.itemText(current_index) and "Error" not in self.target_chat_combo.itemText(current_index) and "No chats" not in self.target_chat_combo.itemText(current_index)
            can_generate = is_valid_selection

        # Disable if worker is running
        if self.chat_list_worker and self.chat_list_worker.isRunning():
             can_generate = False

        self.generate_button.setEnabled(can_generate)

    def _on_send_context(self):
        """Navigate to the selected chat link in the browser using the scraper."""
        current_index = self.target_chat_combo.currentIndex()
        link = self.target_chat_combo.itemData(current_index)
        if not link:
            return
        # Disable button while navigating
        self.send_context_button.setEnabled(False)
        success = self.scraper.safe_get(link)
        self.send_context_button.setEnabled(True)
        if not success:
            QMessageBox.warning(self, "Navigation Failed", f"Failed to navigate to chat: {link}")

    # --- Placeholder methods for future connections ---
    # def _start_generation(self):
    #     # Get settings, create StoryGenerator worker, start thread
    #     pass

    # def _cancel_generation(self):
    #     # Signal the worker thread to stop
    #     pass

    # def _share_to_discord(self):
    #     pass

    # def _update_log(self, message):
    #     # Append message to self.log_tab
    #     pass 