"""
PyQt5 GUI Tab for the Dream Fragment Forge.

Allows users to create, edit, and manage narrative fragments (quotes, lore, memories)
within the Dream.OS system.
"""

import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit, 
    QPushButton, QComboBox, QFormLayout, QSizePolicy, QFileDialog,
    QCompleter, QGroupBox, QSpinBox
)
from PyQt5.QtCore import Qt, QStringListModel
from PyQt5.QtGui import QFont
from datetime import datetime # Import datetime for save ID
import os # Import os for basename

# Placeholder for Template Engine and Memory Manager (to be imported from core)
# from core.rendering import TemplateEngine 
# from core.memory import MemoryManager

# Type hinting imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from core.memory.memory_manager import MemoryManager
    from core.rendering.template_engine import TemplateEngine

logger = logging.getLogger(__name__)

class FragmentForgeTab(QWidget):
    """GUI Tab Widget for interacting with the Dream Fragment Forge."""

    def __init__(self, memory_manager: 'MemoryManager', template_engine: 'TemplateEngine', parent=None):
        """
        Initializes the FragmentForgeTab.
        
        Args:
            memory_manager (MemoryManager): Instance of the memory manager.
            template_engine (TemplateEngine): Instance of the template engine.
            parent: Parent widget.
        """
        super().__init__(parent)
        # Store backend instances
        if not memory_manager:
             raise ValueError("MemoryManager instance is required.")
        if not template_engine:
             raise ValueError("TemplateEngine instance is required.")
             
        self.memory_manager = memory_manager
        self.template_engine = template_engine
        
        # --- Autocompletion Models (Example - Populate these from memory/config) ---
        self.tags_model = QStringListModel([
            "proxy", "dream.lore", "core", "memory", "trigger", "reflection", 
            "system.state", "user.input", "event" 
        ])
        self.activation_model = QStringListModel([
            "Boot", "Full Sync", "Recovery", "Idle", "User Prompt", "Error State", 
            "Task Complete", "Task Start"
        ])
        self.tone_model = QStringListModel([
            "resilient", "prophetic", "melancholy", "urgent", "informative", 
            "reflective", "warning", "instructional", "inquisitive"
        ])
        self.narrative_role_model = QStringListModel([
            "Proxy Origin", "System Core Belief", "User Reflection", "Task Context", 
            "Error Handling", "Onboarding Tip", "World Lore"
        ])
        
        self._init_ui()
        self._connect_signals()
        logger.info("FragmentForgeTab initialized with backend components.")
        
    def _init_ui(self):
        """Initialize the UI layout and widgets."""
        main_layout = QHBoxLayout(self)
        
        # --- Left Side: Input Form ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(15) # Add spacing between elements

        # Quote Input
        quote_group = QGroupBox("Fragment Core")
        quote_layout = QVBoxLayout()
        self.quote_input = QTextEdit()
        self.quote_input.setPlaceholderText("Enter or paste the core quote, lore text, or memory fragment here...")
        self.quote_input.setMinimumHeight(100)
        quote_layout.addWidget(QLabel("Core Text:"))
        quote_layout.addWidget(self.quote_input)
        quote_group.setLayout(quote_layout)
        left_layout.addWidget(quote_group)

        # Metadata Form
        metadata_group = QGroupBox("Metadata")
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setSpacing(10)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., Proxy's Burden, System Startup Phrase")
        form_layout.addRow("Fragment Name:", self.name_input)

        self.author_input = QLineEdit()
        self.author_input.setPlaceholderText("e.g., Konstantin Josef Jireček, System, User")
        form_layout.addRow("Author/Source:", self.author_input)

        # Tags with Autocompletion
        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("Comma-separated tags (e.g., proxy, dream.lore, core)")
        tags_completer = QCompleter(self.tags_model, self)
        tags_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.tags_input.setCompleter(tags_completer)
        form_layout.addRow("Tags:", self.tags_input)

        # Rank and Resonance (Side-by-side)
        rank_resonance_layout = QHBoxLayout()
        self.rank_combo = QComboBox()
        self.rank_combo.addItems(["S", "A", "B", "C", "D", "System", "User"]) # Example Ranks
        self.rank_combo.setToolTip("Importance or tier of the fragment")
        rank_resonance_layout.addWidget(QLabel("Rank:"))
        rank_resonance_layout.addWidget(self.rank_combo)
        rank_resonance_layout.addSpacing(20)
        self.resonance_spinbox = QSpinBox()
        self.resonance_spinbox.setRange(0, 100)
        self.resonance_spinbox.setSuffix("%")
        self.resonance_spinbox.setToolTip("Estimated personal or system resonance percentage")
        rank_resonance_layout.addWidget(QLabel("Resonance:"))
        rank_resonance_layout.addWidget(self.resonance_spinbox)
        rank_resonance_layout.addStretch()
        form_layout.addRow(rank_resonance_layout)

        # Activation Triggers with Autocompletion
        self.activation_input = QLineEdit()
        self.activation_input.setPlaceholderText("Comma-separated triggers (e.g., Boot, Full Sync)")
        activation_completer = QCompleter(self.activation_model, self)
        activation_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.activation_input.setCompleter(activation_completer)
        form_layout.addRow("Activation:", self.activation_input)

        # Tone with Autocompletion
        self.tone_input = QLineEdit()
        self.tone_input.setPlaceholderText("Comma-separated tones (e.g., resilient, prophetic)")
        tone_completer = QCompleter(self.tone_model, self)
        tone_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.tone_input.setCompleter(tone_completer)
        form_layout.addRow("Tone:", self.tone_input)

        # Narrative Role with Autocompletion
        self.narrative_role_input = QLineEdit()
        self.narrative_role_input.setPlaceholderText("e.g., Proxy Origin, System Core Belief")
        role_completer = QCompleter(self.narrative_role_model, self)
        role_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.narrative_role_input.setCompleter(role_completer)
        form_layout.addRow("Narrative Role:", self.narrative_role_input)
        
        metadata_group.setLayout(form_layout)
        left_layout.addWidget(metadata_group)
        
        # Action Buttons
        action_layout = QHBoxLayout()
        self.attach_voice_button = QPushButton("Attach Voice")
        self.attach_bgm_button = QPushButton("Attach BGM")
        self.save_button = QPushButton("Save Fragment")
        self.save_button.setStyleSheet("background-color: #4CAF50; color: white;") # Style save button
        action_layout.addWidget(self.attach_voice_button)
        action_layout.addWidget(self.attach_bgm_button)
        action_layout.addStretch()
        action_layout.addWidget(self.save_button)
        left_layout.addLayout(action_layout)

        left_layout.addStretch() # Push content upwards

        # --- Right Side: Live Preview ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        preview_group = QGroupBox("Live Preview (Rendered)")
        preview_layout = QVBoxLayout()
        self.preview_output = QTextEdit()
        self.preview_output.setReadOnly(True)
        self.preview_output.setFont(QFont("Courier New", 10)) # Use monospace font for preview
        self.preview_output.setPlaceholderText("Preview of the rendered fragment will appear here...")
        preview_layout.addWidget(self.preview_output)
        preview_group.setLayout(preview_layout)
        right_layout.addWidget(preview_group)

        # Set size policies
        left_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        right_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        main_layout.addWidget(left_panel, 1) # Give left panel 1/3 space
        main_layout.addWidget(right_panel, 2) # Give right panel 2/3 space

    def _connect_signals(self):
        """Connect widget signals to handler methods."""
        # Connect input fields to trigger preview update
        self.quote_input.textChanged.connect(self._update_preview)
        self.name_input.textChanged.connect(self._update_preview)
        self.author_input.textChanged.connect(self._update_preview)
        self.tags_input.textChanged.connect(self._update_preview)
        self.rank_combo.currentTextChanged.connect(self._update_preview)
        self.resonance_spinbox.valueChanged.connect(self._update_preview)
        self.activation_input.textChanged.connect(self._update_preview)
        self.tone_input.textChanged.connect(self._update_preview)
        self.narrative_role_input.textChanged.connect(self._update_preview)

        # Connect buttons
        self.save_button.clicked.connect(self._save_fragment)
        self.attach_voice_button.clicked.connect(self._attach_file_voice)
        self.attach_bgm_button.clicked.connect(self._attach_file_bgm)

    def _update_preview(self):
        """Gather data from input fields and update the preview pane using TemplateEngine."""
        fragment_data = self._gather_fragment_data()
        
        # Define a default Jinja2 template for the preview
        # This could be loaded from a file or configuration later
        preview_template = """
        <style>
            .label { font-weight: bold; }
            .core-text { 
                white-space: pre-wrap; /* Preserve whitespace */ 
                font-family: monospace; 
                background-color: #f8f8f8;
                border: 1px solid #eee;
                padding: 10px;
                margin-top: 10px;
            }
        </style>
        <p><span class="label">Fragment:</span> {{ fragment.name | default('Untitled') }}</p>
        <p><span class="label">Author:</span> {{ fragment.author | default('N/A') }}</p>
        <p>
            <span class="label">Rank:</span> {{ fragment.rank | default('N/A') }} &nbsp;&nbsp;
            <span class="label">Resonance:</span> {{ fragment.resonance | default(0) }}%
        </p>
        <p><span class="label">Tags:</span> {{ fragment.tags | join(', ') | default('None') }}</p>
        <p><span class="label">Tone:</span> {{ fragment.tone | join(', ') | default('None') }}</p>
        <p><span class="label">Activation:</span> {{ fragment.activation | join(', ') | default('None') }}</p>
        <p><span class="label">Narrative Role:</span> {{ fragment.narrative_role | default('N/A') }}</p>
        
        {% if fragment.voice_file %}
        <p><span class="label">Voice:</span> {{ fragment.voice_file | basename }}</p>
        {% endif %}
        {% if fragment.bgm_file %}
        <p><span class="label">BGM:</span> {{ fragment.bgm_file | basename }}</p>
        {% endif %}

        <div class="core-text">{{ fragment.core_text | default('(No core text entered)') }}</div>
        """

        try:
            # Pass fragment data under a 'fragment' key for the template context
            # Add os.path.basename as a filter for convenience
            self.template_engine.env.filters['basename'] = os.path.basename 
            rendered_html = self.template_engine.render(preview_template, context={"fragment": fragment_data})
            self.preview_output.setHtml(rendered_html) # Use setHtml for styled preview
        except Exception as e:
            logger.error(f"Failed to render fragment preview: {e}", exc_info=True)
            self.preview_output.setText(f"Error rendering preview:\n{e}")

    def _gather_fragment_data(self) -> dict:
        """Collects data from all input fields into a dictionary."""
        return {
            "core_text": self.quote_input.toPlainText().strip(),
            "name": self.name_input.text().strip(),
            "author": self.author_input.text().strip(),
            "tags": [tag.strip() for tag in self.tags_input.text().split(',') if tag.strip()],
            "rank": self.rank_combo.currentText(),
            "resonance": self.resonance_spinbox.value(),
            "activation": [act.strip() for act in self.activation_input.text().split(',') if act.strip()],
            "tone": [t.strip() for t in self.tone_input.text().split(',') if t.strip()],
            "narrative_role": self.narrative_role_input.text().strip(),
            # Placeholders for file paths
            "voice_file": getattr(self, '_voice_file_path', None), 
            "bgm_file": getattr(self, '_bgm_file_path', None)
        }

    def _save_fragment(self):
        """Handles saving the current fragment data using MemoryManager."""
        fragment_data = self._gather_fragment_data()
        name = fragment_data.get("name")
        core_text = fragment_data.get("core_text")

        if not core_text and not name:
            logger.warning("Cannot save fragment: Core text or name is missing.")
            # TODO: Show a QMessageBox.warning to the user
            return
            
        # Use name for ID generation, fallback to timestamp if no name
        base_id = name.lower().replace(' ', '_').replace('\'', '') if name else "fragment"
        fragment_id = f"{base_id}_{int(datetime.now().timestamp())}" 
        
        logger.info(f"Attempting to save fragment: ID='{fragment_id}', Name='{name}'")
        
        try:
            success = self.memory_manager.save_fragment(fragment_id, fragment_data)
            if success:
                logger.info(f"Fragment '{fragment_id}' saved successfully.")
                # TODO: Show a status message or clear the form
                # self.clear_form() # Optional: Add a method to clear fields
            else:
                logger.error(f"Failed to save fragment '{fragment_id}' using MemoryManager.")
                # TODO: Show a QMessageBox.critical
        except Exception as e:
            logger.error(f"Exception occurred during fragment save: {e}", exc_info=True)
            # TODO: Show a QMessageBox.critical

    def _attach_file_dialog(self, title: str, file_filter: str) -> Optional[str]:
        """Opens a file dialog and returns the selected file path."""
        options = QFileDialog.Options()
        # options |= QFileDialog.DontUseNativeDialog # Uncomment for consistent dialog on all OS
        file_path, _ = QFileDialog.getOpenFileName(
            self, title, "", file_filter, options=options
        )
        if file_path:
            logger.info(f"File selected: {file_path}")
            return file_path
        return None

    def _attach_file_voice(self):
        """Handles attaching a voice narration file."""
        file_path = self._attach_file_dialog("Attach Voice Narration", "Audio Files (*.mp3 *.wav *.ogg)")
        if file_path:
            self._voice_file_path = file_path
            # Update UI or preview if needed to show attached file
            logger.info(f"Voice file attached: {file_path}")
            self.attach_voice_button.setText(f"Voice: {os.path.basename(file_path)}") # Update button text

    def _attach_file_bgm(self):
        """Handles attaching a background music file."""
        file_path = self._attach_file_dialog("Attach Background Music", "Audio Files (*.mp3 *.wav *.ogg)")
        if file_path:
            self._bgm_file_path = file_path
            # Update UI or preview if needed
            logger.info(f"BGM file attached: {file_path}")
            self.attach_bgm_button.setText(f"BGM: {os.path.basename(file_path)}") # Update button text

    def load_fragment(self, fragment_data: dict):
         """Loads data from a dictionary into the form fields."""
         self.quote_input.setPlainText(fragment_data.get("core_text", ""))
         self.name_input.setText(fragment_data.get("name", ""))
         self.author_input.setText(fragment_data.get("author", ""))
         self.tags_input.setText(", ".join(fragment_data.get("tags", [])))
         
         rank_index = self.rank_combo.findText(fragment_data.get("rank", ""), Qt.MatchFixedString)
         if rank_index >= 0: self.rank_combo.setCurrentIndex(rank_index)
         
         self.resonance_spinbox.setValue(fragment_data.get("resonance", 0))
         self.activation_input.setText(", ".join(fragment_data.get("activation", [])))
         self.tone_input.setText(", ".join(fragment_data.get("tone", [])))
         self.narrative_role_input.setText(fragment_data.get("narrative_role", ""))
         
         self._voice_file_path = fragment_data.get("voice_file")
         self._bgm_file_path = fragment_data.get("bgm_file")
         
         # Update button text if files are loaded
         if self._voice_file_path: self.attach_voice_button.setText(f"Voice: {os.path.basename(self._voice_file_path)}")
         else: self.attach_voice_button.setText("Attach Voice")
             
         if self._bgm_file_path: self.attach_bgm_button.setText(f"BGM: {os.path.basename(self._bgm_file_path)}")
         else: self.attach_bgm_button.setText("Attach BGM")
         
         self._update_preview() # Update preview after loading
         logger.info(f"Loaded fragment '{fragment_data.get('name', 'N/A')}' into Forge.")

# Example Usage (for standalone testing)
if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication, QMainWindow
    
    # Basic logging for example
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    app = QApplication(sys.argv)
    main_window = QMainWindow()
    forge_tab = FragmentForgeTab()
    main_window.setCentralWidget(forge_tab)
    main_window.setWindowTitle("Dream Fragment Forge - Standalone Test")
    main_window.setGeometry(100, 100, 1000, 700) # Set initial size
    
    # Example of loading data
    test_data = {
        "core_text": "We, the unwilling, led by the unknowing, are doing the impossible for the ungrateful.",
        "name": "Proxy's Burden",
        "author": "Konstantin Josef Jireček (adapted)",
        "tags": ["proxy", "dream.lore", "core", "resilience"],
        "rank": "S",
        "resonance": 97,
        "activation": ["Boot", "Full Sync", "Recovery"],
        "tone": ["resilient", "prophetic", "weary"],
        "narrative_role": "Proxy Origin",
    }
    # Use QTimer to load data after the event loop starts
    from PyQt5.QtCore import QTimer
    QTimer.singleShot(100, lambda: forge_tab.load_fragment(test_data))

    main_window.show()
    sys.exit(app.exec_()) 