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
from utils import GuiLogHandler, post_to_discord # Keep utils import separate

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
            rendered = self.prompt or ctx["rendered_prompt"]
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

        # ================= left column =================
        left = QVBoxLayout()
        self.model_select = QComboBox()
        self.model_select.addItems(["gpt-4o", "gpt-4.5", "o4-mini", "o4-mini-high"])
        self.headless = QCheckBox("Headless Mode")
        self.discord = QCheckBox("Post to Discord", checked=True)
        self.reverse = QCheckBox("Reverse Order")

        self.prompt_box = QTextEdit()
        self.gen_btn   = QPushButton("Generate Episodes")
        self.cancel_btn = QPushButton("Cancel Generation")
        self.cancel_btn.setEnabled(False)

        self.gen_btn.clicked.connect(self.start_generation)
        self.cancel_btn.clicked.connect(self.cancel_generation)

        for w in [self.model_select, self.headless, self.discord,
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

    # --- Add handler for tab double-click ---
    def handle_tab_double_click(self, index):
        if index == self.log_tab_index:
            self.log_tab.clear()
            self.append_log("--- Log cleared ---")
    # ----------------------------------------

    # ------------------------------------------------------------------ #
    def start_generation(self):
        logging.info("[DEBUG] start_generation called.")
        if self.worker:
            logging.warning("Generation already in progress. Ignoring call.")
            return  # already running
        
        logging.info("[DEBUG] self.worker is None, proceeding to start generation.")
        
        model = self.model_select.currentText()
        prompt = self.prompt_box.toPlainText().strip()
        headless = self.headless.isChecked()
        reverse = self.reverse.isChecked() # Get reverse flag from checkbox

        # Pass reverse flag to worker
        self.worker = GenerationWorker(model, prompt, headless, reverse)
        self.worker.finished.connect(self.on_done)
        self.worker.context_ready.connect(self.context_tab.setPlainText)
        self.worker.log_ready.connect(self.append_log)
        self.worker.start()

        self.gen_btn.setEnabled(False); self.cancel_btn.setEnabled(True)
        self.append_log(f"--- Generation started with {model} ---")

    def cancel_generation(self):
        if self.worker:
            self.worker.stop()
            self.worker.wait(1000)
            self.worker = None
            self.gen_btn.setEnabled(True); self.cancel_btn.setEnabled(False)
            self.append_log("--- Generation cancelled ---")

    def on_done(self, content: str):
        self.content_tab.setPlainText(content)

        if self.discord.isChecked():
            success = post_to_discord(content)
            note = "✅ Discord post successful" if success else "⚠️ Discord post failed"
            self.append_log(note)

        self.gen_btn.setEnabled(True); self.cancel_btn.setEnabled(False)
        self.append_log("--- Generation finished ---")
        self.worker = None

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