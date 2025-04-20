import sys, logging, time, os
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QComboBox, QCheckBox,
    QTextEdit, QPushButton, QTabWidget
)

# --- Use package imports --- 
from dreamscape_generator.src import (
    build_context,
    generate_episode, 
    # send_prompt_to_chatgpt # This is not used directly here yet
)
from utils import GuiLogHandler, post_to_discord, load_models_yaml, load_prompt_templates # Keep utils import separate, add template loader

# --------------------------------------------------------------------------- #
#                              Worker Thread                                  #
# --------------------------------------------------------------------------- #
class GenerationWorker(QThread):
    finished = pyqtSignal(str)          # final content
    context_ready = pyqtSignal(str)     # rendered prompt / context
    log_ready = pyqtSignal(str)         # forwarded log line

    # Add reverse_flag parameter
    def __init__(self, model: str, prompt: str, headless: bool, reverse_flag: bool):
        super().__init__()
        self.model = model
        self.prompt = prompt
        self.headless = headless
        self.reverse_flag = reverse_flag # Store reverse flag
        self._stop = False

        # Pipe logging to this worker's signal
        handler = GuiLogHandler()
        handler._emitter.log_signal.connect(self.log_ready.emit)
        # Avoid adding handler multiple times if worker is recreated
        root_logger = logging.getLogger()
        if not any(isinstance(h, GuiLogHandler) for h in root_logger.handlers):
             root_logger.addHandler(handler)
        # Ensure root logger level is appropriate
        if root_logger.level > logging.INFO:
            root_logger.setLevel(logging.INFO)


    def run(self):
        # Build context (may be long; do it in thread)
        logging.info("Worker thread started. Building context...")
        try:
            ctx = build_context() # Uses imported function
            # --- Log prompt values for debugging ---
            logger.info(f"[DEBUG] Worker received prompt from GUI: '{self.prompt}'")
            # ---------------------------------------
            rendered = self.prompt or ctx["rendered_prompt"]
            # --- Log final rendered prompt ---
            logger.info(f"[DEBUG] Using final rendered prompt: '{rendered[:100]}...'") # Log start of prompt
            # --------------------------------
            self.context_ready.emit(rendered)
            logging.info("Context built successfully.")
        except Exception as e:
            logging.error(f"Error building context: {e}", exc_info=True)
            self.finished.emit(f"[ERROR] Context building failed: {e}")
            return

        if self._stop:
            logging.info("Worker stopping before generation.")
            return
        try:
            logging.info("Starting episode generation...")
            # Call the imported generate_episode function
            content = generate_episode(rendered, self.model, self.headless, self.reverse_flag)
            logging.info("Episode generation finished.")
            self.finished.emit(content)
        except Exception as e:
            logging.error(f"Error during generation: {e}", exc_info=True)
            self.finished.emit(f"[ERROR] Generation failed: {e}")

    def stop(self):
        logging.info("Stop signal received by worker.")
        self._stop = True

# --------------------------------------------------------------------------- #
#                              GUI Widget                                     #
# --------------------------------------------------------------------------- #
class DreamscapeGenerator(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dreamscape Episode Generator")
        self.resize(1000, 700)

        # --- Load templates first ---
        self.loaded_templates = load_prompt_templates()
        # ---------------------------

        # ================= left column =================
        left = QVBoxLayout()
        
        # --- Model Selector --- 
        self.model_select = QComboBox()
        available_models = load_models_yaml() 
        if available_models:
            self.model_select.addItems(available_models)
        else:
            logging.error("No models loaded from models.yaml or defaults. Check file and logs.")
            self.model_select.addItem("ERROR: No models loaded")
            self.model_select.setEnabled(False)
        left.addWidget(self.model_select) # Add to layout
        
        # --- Template Selector --- 
        self.template_select = QComboBox()
        self.template_select.addItem("(Custom Prompt)") # Default option
        if self.loaded_templates:
             self.template_select.addItems(sorted(self.loaded_templates.keys()))
        self.template_select.currentIndexChanged.connect(self.on_template_selected)
        left.addWidget(self.template_select) # Add to layout
        # -------------------------
        
        self.headless = QCheckBox("Headless Mode")
        self.discord = QCheckBox("Post to Discord", checked=True)
        self.reverse = QCheckBox("Reverse Order")

        self.prompt_box = QTextEdit() # Main prompt entry
        self.gen_btn   = QPushButton("Generate Episodes")
        self.cancel_btn = QPushButton("Cancel Generation")
        self.cancel_btn.setEnabled(False)

        self.gen_btn.clicked.connect(self.start_generation)
        self.cancel_btn.clicked.connect(self.cancel_generation)

        # Add remaining widgets to left layout
        for w in [self.headless, self.discord,
                  self.reverse, self.prompt_box, self.gen_btn, self.cancel_btn]:
            left.addWidget(w)

        # ================= right column =================
        right = QVBoxLayout()
        self.tabs = QTabWidget()
        self.content_tab = QTextEdit(); self.content_tab.setReadOnly(True)
        self.context_tab = QTextEdit(); self.context_tab.setReadOnly(True)
        self.log_tab = QTextEdit();     self.log_tab.setReadOnly(True)
        self.log_tab_index = -1 # Store index for later check
        tab_widgets = [self.content_tab, self.context_tab, self.log_tab]
        tab_names = ["Content", "Context", "Log"]
        for i, (widget, name) in enumerate(zip(tab_widgets, tab_names)):
            self.tabs.addTab(widget, name)
            if widget == self.log_tab:
                self.log_tab_index = i # Save the index of the log tab
        right.addWidget(self.tabs)

        # --- Connect tab double-click signal ---
        self.tabs.tabBarDoubleClicked.connect(self.handle_tab_double_click)
        # ---------------------------------------

        # ================= master layout ================
        master = QHBoxLayout(self)
        master.addLayout(left, 3); master.addLayout(right, 7)

        self.worker: GenerationWorker | None = None

    # --- Add handler for template selection --- 
    def on_template_selected(self, index):
        template_name = self.template_select.itemText(index)
        logging.debug(f"Template selected: '{template_name}' at index {index}")
        if template_name == "(Custom Prompt)":
            # Optional: Clear the prompt box or do nothing
            # self.prompt_box.clear()
            pass 
        elif template_name in self.loaded_templates:
            self.prompt_box.setPlainText(self.loaded_templates[template_name])
    # ------------------------------------------

    # --- Add handler for tab double-click ---
    def handle_tab_double_click(self, index):
        if index == self.log_tab_index:
            self.log_tab.clear()
            self.append_log("--- Log cleared ---")
    # ----------------------------------------

    # ------------------------------------------------------------------ #
    def start_generation(self):
        logging.info("[DEBUG] start_generation called.") 
        # Use button state as the primary guard against rapid clicks
        if not self.gen_btn.isEnabled():
            logging.warning("Generation button is disabled, likely already running. Ignoring call.")
            return
        
        # Secondary check (optional, but doesn't hurt)
        if self.worker:
            logging.warning("Worker object exists, generation already in progress. Ignoring call.")
            return  
        
        logging.info("[DEBUG] Generation not running, proceeding to start.") 
        
        model = self.model_select.currentText()
        prompt = self.prompt_box.toPlainText().strip()
        headless = self.headless.isChecked()
        reverse = self.reverse.isChecked() # Get reverse flag from checkbox

        # Pass reverse flag to worker
        self.worker = GenerationWorker(model, prompt, headless, reverse)
        self.worker.finished.connect(self.on_done)
        self.worker.context_ready.connect(self.context_tab.setPlainText)
        self.worker.log_ready.connect(self.append_log)
        
        # Disable button immediately BEFORE starting worker
        self.gen_btn.setEnabled(False); self.cancel_btn.setEnabled(True)
        
        self.worker.start()

        self.append_log(f"--- Generation started with {model} ---")

    def cancel_generation(self):
        logging.info("[DEBUG] cancel_generation called.") # Add log
        if self.worker:
            self.worker.stop()
            self.worker.wait(1000)
            self.worker = None
            self.gen_btn.setEnabled(True); self.cancel_btn.setEnabled(False)
            self.append_log("--- Generation cancelled ---")

    def on_done(self, content: str):
        logging.info("[DEBUG] on_done called.") # Add log
        # Ensure content is a string before setting
        if not isinstance(content, str):
             logging.warning(f"on_done received non-string content (type: {type(content)}), converting.")
             content = str(content) # Convert potential non-strings
             
        self.content_tab.setPlainText(content)

        if self.discord.isChecked():
            success = post_to_discord(content)
            note = "✅ Discord post successful" if success else "⚠️ Discord post failed"
            self.append_log(note)

        # Re-enable button AFTER everything else is done
        self.gen_btn.setEnabled(True); self.cancel_btn.setEnabled(False)
        self.append_log("--- Generation finished ---")
        self.worker = None # Set worker to None last

    def append_log(self, msg: str):
        self.log_tab.append(msg)
        # auto‑scroll
        self.log_tab.verticalScrollBar().setValue(self.log_tab.verticalScrollBar().maximum())

# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    # --- Load .env file from project root --- 
    from dotenv import load_dotenv
    import os
    # Calculate the path to the parent directory and join with .env
    script_dir = os.path.dirname(__file__) # Dir containing episode_generator.py
    project_root = os.path.abspath(os.path.join(script_dir, os.pardir, os.pardir)) # Go up two levels (social/digital_dreamscape -> ..)
    # *** Correction based on user path D:\Dream.os\.env ***
    # Assuming script is at D:\Dream.os\social\digital_dreamscape\episode_generator.py
    # We need to go up two levels: digital_dreamscape -> social -> Dream.os
    project_root_actual = os.path.abspath(os.path.join(script_dir, os.pardir, os.pardir)) # Adjust based on actual structure
    # ** Simpler approach: Assume .env is directly one level above the script's parent **
    # D:\Dream.os\social\digital_dreamscape -> parent is D:\Dream.os\social
    # That parent's parent is D:\Dream.os 
    parent_dir = os.path.dirname(script_dir)
    project_root_env = os.path.dirname(parent_dir)
    dotenv_path = os.path.join(project_root_env, '.env')
    
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path, override=True) # override=True ensures .env takes precedence
        print(f"Loaded environment variables from {os.path.abspath(dotenv_path)}")
    else:
        print(f".env file not found at {os.path.abspath(dotenv_path)}, relying on system environment variables.")
    # -----------------------------------------
    
    # --- Ensure logs directory exists ---
    os.makedirs('logs', exist_ok=True) 
    # -------------------------------------

    # basic console logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    app = QApplication(sys.argv)
    win = DreamscapeGenerator()
    win.show()
    sys.exit(app.exec_()) 