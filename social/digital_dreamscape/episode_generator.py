"""
Dreamscape Episode Generator – Cycle‑aware GUI
=============================================

* PyQt6 front‑end that can batch‑generate multiple prompts (“cycles”)
* Uses multiprocessing to keep LLM calls off the UI thread
* Thread‑safe logging pipe → live log tab
* Clean interrupt / cancel path
* All hard‑coded knobs pulled into a Config dataclass

Author : The Architect's Edge (ChatGPT o3) – Full Sync Mode
"""

from __future__ import annotations

# ───────────────────────── stdlib / typing ──────────────────────────
import json
import logging
import multiprocessing as mp
import os
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from queue import Empty
from typing import Any, Dict, List, Optional

# ────────────────────────── 3rd‑party ──────────────────────────────
from PyQt6.QtCore import QObject, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QAbstractItemView,
    QMainWindow,
)

# ──────────────────────── dreamscape libs ──────────────────────────
from dreamscape_generator.src import build_context, generate_episode
from utils import (
    GuiLogHandler,
    load_models_yaml,
    load_prompt_templates,
    post_to_discord,
)
from dreamscape_generator.threads.saga_worker import SagaGenerationWorker

# ────────────────────────── configuration ──────────────────────────
@dataclass(slots=True)
class Config:
    RATE_LIMIT_DELAY_SEC: int = 5
    PROMPT_SEPARATOR: str = "===PROMPT_SEPARATOR==="
    LOG_DIR: Path = Path("logs/gui")
    DISCORD_ENABLED: bool = True
    DEFAULT_HEADLESS: bool = True
    LOG_LEVEL: int = logging.INFO
    LOG_FORMAT: str = "%(asctime)s | %(levelname)-7s | %(message)s"
    DOTENV_PATH: Path = Path("config/.env")
    HISTORY_CACHE_FILE: Path = Path(".history_cache.json")


CFG = Config()  # module‑level singleton

# ────────────────────────── multiproc shim ─────────────────────────
if sys.platform == "win32":
    mp.set_start_method("spawn", force=True)  # PyQt6 + mp safety on Windows


def _generation_worker(
    log_q: mp.Queue,
    ctx_q: mp.Queue,
    res_q: mp.Queue,
    model: str,
    prompt: str,
    headless: bool,
    reverse: bool,
) -> None:
    """Child process: build context → generate episode → hand data back."""
    # --- Import and Setup Memory Manager for this process ---
    from memory_manager import UnifiedMemoryManager
    # Use defaults for paths (relative to project root)
    # Ensure template dir exists if needed for narrative (though not used here directly)
    mem_manager = UnifiedMemoryManager(template_dir="templates")
    # --------------------------------------------------------
    try:
        log_q.put(("INFO", f"Building context… (model={model})"))
        # Pass manager instance to build_context
        ctx = build_context(prompt, reverse, mem_manager) 
        rendered = ctx.get("rendered_prompt", "")
        ctx_q.put(rendered)

        log_q.put(("INFO", "Calling LLM…"))
        episode = generate_episode(rendered, model, headless, reverse)
        res_q.put(episode)

        # --- Save result back to memory --- 
        # Simple example: store latest episode in 'context' segment
        # Uses prompt as key, could be timestamp, or other ID
        # Consider if overwriting or appending is desired
        mem_manager.set(key="last_episode", data=episode, segment="context")
        log_q.put(("INFO", "Saved episode to memory manager."))
        # ---------------------------------

        log_q.put(("INFO", f"Episode length = {len(episode):,} chars"))
    except Exception as exc:  # noqa: BLE001
        err = f"{type(exc).__name__}: {exc}"
        log_q.put(("ERROR", err))
        ctx_q.put(f"[CTX‑ERROR] {err}")
        res_q.put(f"[GEN‑ERROR] {err}")
    finally:
        log_q.put(("INFO", "Worker done."))
        # --- Close memory manager resources --- 
        if 'mem_manager' in locals():
             mem_manager.close() 
        # -------------------------------------


# ────────────────────────── worker thread ──────────────────────────
class CycleThread(QThread):
    finished = pyqtSignal(str)
    context_ready = pyqtSignal(str)
    result_ready = pyqtSignal(str, str)

    def __init__(self, model: str, prompts: list[str], headless: bool, reverse: bool):
        super().__init__()
        self.model, self.prompts = model, prompts
        self.headless, self.reverse = headless, reverse
        self._stop = False
        self._log_q, self._ctx_q, self._res_q = mp.Queue(), mp.Queue(), mp.Queue()
        self._proc: mp.Process | None = None

    # ───────────────────────── public API ──────────────────────────
    def stop(self) -> None:
        self._stop = True

    # ────────────────────────── main loop ──────────────────────────
    def run(self) -> None:
        summary: list[str] = []

        for idx, prompt in enumerate(self.prompts, start=1):
            if self._stop:
                summary.append(f"Prompt {idx}: CANCELLED")
                break

            self._proc = mp.Process(
                target=_generation_worker,
                args=(
                    self._log_q,
                    self._ctx_q,
                    self._res_q,
                    self.model,
                    prompt,
                    self.headless,
                    self.reverse,
                ),
                daemon=True,
            )
            self._proc.start()
            ctx_yielded = False
            result = "[NO‑RESULT]"

            while self._proc.is_alive():
                self._pump_queues(ctx_yielded)
                ctx_yielded = ctx_yielded or not self._ctx_q.empty()
                if self._stop:
                    self._proc.terminate()
                    self._proc.join(timeout=1)
                    break
                self.msleep(100)

            # flush remaining queues after process exit
            self._pump_queues(ctx_yielded)
            if not self._res_q.empty():
                result = self._res_q.get_nowait()

            status = (
                "OK"
                if not result.startswith("[GEN‑ERROR") and result != "[NO‑RESULT]"
                else "FAIL"
            )
            summary.append(f"Prompt {idx}: {status}")
            self.result_ready.emit(prompt, result)

            if self._stop or idx == len(self.prompts):
                break
            self.msleep(CFG.RATE_LIMIT_DELAY_SEC * 1000)

        self.finished.emit("; ".join(summary))

    # ─────────────────────── helper: queue pump ────────────────────
    def _pump_queues(self, ctx_already_emitted: bool) -> None:
        try:
            while True:
                lvl, msg = self._log_q.get_nowait()
                getattr(log, lvl.lower())(msg)
        except Empty:
            pass

        if not ctx_already_emitted:
            try:
                ctx = self._ctx_q.get_nowait()
                self.context_ready.emit(ctx)
            except Empty:
                pass


# --- New HistoryFetchThread ---
class HistoryFetchThread(QThread):
    """Worker thread to fetch chat history non-headlessly."""
    finished = pyqtSignal(bool, str) # Signal finished status (success: bool, message: str)

    def __init__(self):
        super().__init__()
        self._stop_flag = False # Not strictly needed for this simple task, but good practice

    def run(self):
        status = False
        message = "History fetch failed."
        history_data = []
        manager = None
        # --- Need to import necessary classes within the thread run method ---
        # Because this runs potentially before full GUI init? Or just good practice.
        # We assume backend imports might fail if run too early globally
        from dreamscape_generator.src.core.UnifiedDriverManager import UnifiedDriverManager
        from dreamscape_generator.src.chatgpt_scraper import ChatGPTScraper
        # --------------------------------------------------------------------
        try:
            self._log_status("Initializing non-headless browser for history fetch...")
            # Explicitly set headless=False
            # TODO: Make profile/cookie paths configurable via CFG if needed
            manager = UnifiedDriverManager(headless=False) # Using default profile/cookie paths for now
            scraper = ChatGPTScraper(manager=manager)

            # --- Explicitly get the driver first! ---
            driver = manager.get_driver()
            if not driver:
                # Log status already handled the error message from get_driver
                raise Exception("Failed to initialize WebDriver for history fetch.")
            # ----------------------------------------

            # Check login - this might block or require user interaction if cookies invalid
            self._log_status("Checking login status (browser window may require attention)...")
            if not manager.is_logged_in():
                 # Try loading cookies again explicitly after driver init?
                 if not manager.load_cookies() or not manager.is_logged_in():
                      message = "Login required in browser. Please log in and click Refresh again."
                      self._log_status(f"ERROR: {message}")
                      # No automatic prompt for login here, user must click refresh again
                      raise Exception(message) # Stop the thread

            self._log_status("Login verified. Fetching chat titles...")
            history_data = scraper.get_all_chat_titles()

            if history_data:
                self._log_status(f"Successfully fetched {len(history_data)} chat titles. Saving...")
                # Save to JSON
                history_file = Path(CFG.HISTORY_CACHE_FILE)
                try:
                    with open(history_file, 'w', encoding='utf-8') as f:
                        json.dump(history_data, f, indent=2)
                    message = f"History updated ({len(history_data)} titles saved)."
                    status = True
                    self._log_status("Save complete.")
                except Exception as save_err:
                    message = f"Fetched titles but failed to save to {history_file.name}: {save_err}"
                    self._log_status(f"ERROR: {message}")
            else:
                message = "Fetched 0 chat titles (or failed during fetch)."
                self._log_status(f"WARNING: {message}")
                # Keep status=False if fetch didn't return data

        except ImportError as imp_err:
             message = f"ERROR: Failed to import backend components for history fetch: {imp_err}"
             self._log_status(message)
        except Exception as e:
            message = f"Error during history fetch: {e}"
            self._log_status(f"ERROR: {message}")
        finally:
            if manager:
                self._log_status("Closing history fetch browser...")
                manager.quit_driver()
            self.finished.emit(status, message)

    def _log_status(self, msg: str):
        # Use root logger so it appears in GUI via handler
        # Need to import logging here as well? Or assume it's globally available?
        # Let's assume global logging is okay here for simplicity, but might need explicit getLogger
        logging.info(f"[HistoryFetch] {msg}")

    def stop(self): # Basic stop method
        self._stop_flag = True
# ---------------------------

# ───────────────────────────── GUI ─────────────────────────────────
class DreamscapeGenerator(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Dreamscape Episode Generator")
        self.resize(1080, 720)

        # ---------- central widget and layout ----------
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        # Create main horizontal layout on the central widget
        h_main = QHBoxLayout(central_widget)
        v_left = QVBoxLayout()
        v_right = QVBoxLayout()
        # Add side-by-side panels with stretch factors
        h_main.addLayout(v_left, 3)
        h_main.addLayout(v_right, 7)

        # ---------- left panel ----------
        self.model_cmb = QComboBox()
        self.model_cmb.addItems(load_models_yaml())
        v_left.addWidget(self.model_cmb)

        self.template_cmb = QComboBox()
        self.template_cmb.addItem("(Custom Prompt)")
        self.templates = load_prompt_templates()
        self.template_cmb.addItems(sorted(self.templates))
        self.template_cmb.currentIndexChanged.connect(self._template_selected)
        v_left.addWidget(self.template_cmb)

        self.headless_chk = QCheckBox("Headless Mode")
        self.headless_chk.setChecked(CFG.DEFAULT_HEADLESS)
        self.discord_chk = QCheckBox("Post to Discord")
        self.discord_chk.setChecked(CFG.DISCORD_ENABLED)
        self.reverse_chk = QCheckBox("Reverse Order")

        for w in (self.headless_chk, self.discord_chk, self.reverse_chk):
            v_left.addWidget(w)

        self.prompt_te = QTextEdit()
        self.prompt_te.setPlaceholderText(
            f"Enter prompt(s) separated by:\n{CFG.PROMPT_SEPARATOR}"
        )
        v_left.addWidget(self.prompt_te)

        self.start_btn = QPushButton("▶️ Generate")
        self.start_btn.clicked.connect(self._start)
        self.cancel_btn = QPushButton("⏹️ Cancel")
        self.cancel_btn.clicked.connect(self._cancel)
        self.cancel_btn.setEnabled(False)

        h_btns = QHBoxLayout()
        h_btns.addWidget(self.start_btn)
        h_btns.addWidget(self.cancel_btn)
        v_left.addLayout(h_btns)

        # ---------- right panel ----------
        self.tabs = QTabWidget()
        self.content_tab = QTextEdit(readOnly=True)
        self.ctx_tab = QTextEdit(readOnly=True)
        self.history_list_widget = QListWidget()
        # --- Enable Multi-Selection ---
        self.history_list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        # ------------------------------
        self.log_tab = QTextEdit(readOnly=True)
        self.saga_chronicle_tab = QTextEdit(readOnly=True)
        self.history_tab_index = -1
        self.log_tab_index = -1

        tab_widgets = [
            self.content_tab, self.ctx_tab,
            self.history_list_widget, self.log_tab,
            self.saga_chronicle_tab
        ]
        tab_names = ["Content", "Context", "History", "Log", "Dreamscape Chronicle"]
        for i, (widget, name) in enumerate(zip(tab_widgets, tab_names)):
            self.tabs.addTab(widget, name)
            if widget == self.log_tab:
                self.log_tab_index = i
            if widget == self.history_list_widget:
                self.history_tab_index = i
        v_right.addWidget(self.tabs)

        # Double-clicking the log tab clears its contents
        # Connect the QTabBar's double-click signal
        self.tabs.tabBar().tabBarDoubleClicked.connect(self._on_tab_double_click)

        # --- Add Control Buttons Below Tabs ---
        h_bottom_btns = QHBoxLayout()
        self.refresh_history_btn = QPushButton("🔄 Refresh Chat History")
        self.refresh_history_btn.clicked.connect(self._start_history_fetch)
        h_bottom_btns.addWidget(self.refresh_history_btn)

        # Add Select All button
        self.select_all_history_btn = QPushButton("Select All History")
        self.select_all_history_btn.clicked.connect(self._select_all_history)
        h_bottom_btns.addWidget(self.select_all_history_btn)
        
        # Existing Generate Full Saga button
        self.generate_saga_btn = QPushButton("🌀 Generate Full Saga")
        self.generate_saga_btn.clicked.connect(self.on_generate_saga_clicked)
        h_bottom_btns.addWidget(self.generate_saga_btn)
        h_bottom_btns.addStretch()
        v_right.addLayout(h_bottom_btns)
        # -------------------------------------

        # ---------- runtime ----------
        self.worker: CycleThread | None = None
        self.saga_worker: SagaGenerationWorker | None = None
        self.current_context: str | None = None
        self.prompt_counter = 0
        self.history_fetch_worker: HistoryFetchThread | None = None

        # --- Load Ignored Chats --- 
        self.ignored_chat_titles = self._load_ignored_chat_titles()
        self._log(f"Loaded {len(self.ignored_chat_titles)} ignored chat titles from file.")
        # --------------------------

        # Initialize Memory Manager
        try:
            from memory_manager import UnifiedMemoryManager
            self.memory_manager = UnifiedMemoryManager(template_dir="templates")
        except ImportError:
            self._log("ERROR: Failed to import UnifiedMemoryManager. Saga features disabled.")
            self.memory_manager = None
            self.generate_saga_btn.setEnabled(False)

        # Load initial history (will now use self.ignored_chat_titles)
        self._load_history_from_file()

    # ────────────────────── template selector ──────────────────────
    def _template_selected(self, idx: int) -> None:
        name = self.template_cmb.itemText(idx)
        if name != "(Custom Prompt)":
            self.prompt_te.setPlainText(self.templates[name])

    # ───────────────────────── start / cancel ──────────────────────
    def _start(self) -> None:
        # --- Updated Logic: Use Saga Worker for Selected Chats with GUI Prompt --- 
        if self.saga_worker and self.saga_worker.isRunning():
            self._log("[SagaMode] Saga generation is already running.")
            return
        if self.worker and self.worker.isRunning():
             self._log("⚠️ A different generation cycle might be running. Cancel first?")
             return
             
        if not self.memory_manager:
            self._log("ERROR: Memory Manager not available. Cannot generate.")
            return

        # 1. Get Selected History Items
        selected_items = self.history_list_widget.selectedItems()
        if not selected_items:
            self._log("ERROR: No chat history item selected. Please select one or more chats from the 'History' tab, or use 'Generate Full Saga'.")
            return
            
        # 2. Get Prompt Template String from GUI
        prompt_template_str = self.prompt_te.toPlainText().strip()
        if not prompt_template_str:
             self._log("ERROR: Prompt text area is empty. Load or paste a saga prompt.")
             return

        # 2b. Get selected model and log it
        selected_model = self.model_cmb.currentText()
        self._log(f"[SagaMode] Using model: {selected_model}")
        # 3. Check Reverse Order
        should_reverse = self.reverse_chk.isChecked()
        order_desc = "newest-to-oldest (reversed selection)" if should_reverse else "oldest-to-newest (selected order)"
        self._log(f"[SagaMode] Processing selected chats. Order: {order_desc}")
        # Extract chat contexts from selected QListWidgetItems
        chat_contexts = [item.data(Qt.ItemDataRole.UserRole) for item in selected_items]
        # Optionally reverse contexts if needed
        if should_reverse:
            chat_contexts.reverse()

        self._log(f"[SagaMode] ▶️ Initializing Dreamscape chronicle for {len(chat_contexts)} selected chat(s) using current prompt...")
        self.saga_chronicle_tab.clear()

        # 4. Instantiate and run the SagaGenerationWorker using the GUI prompt
        self.saga_worker = SagaGenerationWorker(
            memory_manager=self.memory_manager,
            chat_items=chat_contexts,
            selected_model=selected_model,
            prompt_template_str=prompt_template_str
        )
        # Thread-safe logging from worker
        self.saga_worker.log_signal.connect(self._log)
        # Connect signals
        self.saga_worker.saga_output_ready.connect(self.on_saga_output_ready)
        self.saga_worker.progress_signal.connect(self._log)
        self.saga_worker.error_signal.connect(self._log)
        self.saga_worker.finished.connect(self._saga_generation_finished)
        # Start worker
        self.saga_worker.start()

        # Update UI state
        self.start_btn.setEnabled(False)
        self.generate_saga_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        # --- End of Updated Logic ---

    def _cancel(self) -> None:
        # Cancel SagaGenerationWorker specifically
        if self.saga_worker and self.saga_worker.isRunning():
            self.saga_worker.stop()
            self._log("⚠️ Cancel requested for Saga Generation...")
        elif self.worker and self.worker.isRunning():
            self.worker.stop()
            self._log("⚠️ Cancel requested for legacy cycle...")
        else:
            self._log("No generation process seems to be running.")

    # ──────────────────────── slot handlers ────────────────────────
    # _ctx_update, _result_update, _cycle_done are now less relevant if CycleThread isn't used by _start
    # Keep them for now, but they might be removable later.
    def _ctx_update(self, context: str) -> None:
        self.ctx_tab.setPlainText(context)

    def _result_update(self, prompt: str, result: str) -> None:
        self.prompt_counter += 1
        if self.prompt_counter > 1:
            separator = (
                f"\n\n{'='*20} Result for Prompt {self.prompt_counter} {'='*20}\n"
                f"'{prompt[:60]}...'\n"
                f"{'='*50}\n\n"
            )
            self.content_tab.append(separator)

        self.content_tab.append(result)
        self.content_tab.moveCursor(QTextCursor.MoveOperation.End)
        self._log(f"Prompt {self.prompt_counter} complete.")

    def _cycle_done(self, summary: str) -> None:
        self._log(f"✅ Cycle finished: {summary}")
        if self.discord_chk.isChecked():
            # Use template for final summary?
            post_to_discord(content=f"Dreamscape cycle done.\n{summary}")

        self.worker = None
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

    # ───────────────────────── log helper ──────────────────────────
    def _log(self, msg: str) -> None:
        # Convert message to string (handles ints from progress_signal)
        self.log_tab.append(str(msg))
        # auto-scroll
        self.log_tab.verticalScrollBar().setValue(
            self.log_tab.verticalScrollBar().maximum()
        )

    # --- Add Method: _load_history_from_file --- 
    def _load_history_from_file(self):
        """Load history from the JSON cache file, filtering by ignored_chats.txt."""
        history_file = Path(CFG.HISTORY_CACHE_FILE)
        if not history_file.exists():
            self._log("History cache file not found.")
            self.history_list_widget.addItem("No history found. Click Refresh.")
            return

        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
        except Exception as e:
            self._log(f"Error loading history cache: {e}")
            self.history_list_widget.addItem("Error loading history cache.")
            return

        if not history_data:
            self.history_list_widget.addItem("No history found. Click Refresh.")
            return

        self.history_list_widget.clear()
        count = 0
        loaded_count = 0 # Track count *before* filtering
        for item in history_data:
            loaded_count += 1
            title = item.get('title', 'Untitled Chat')
            # Filter based on loaded ignored list
            if title in self.ignored_chat_titles:
                continue

            list_item = QListWidgetItem(title)
            list_item.setData(Qt.ItemDataRole.UserRole, item)
            self.history_list_widget.addItem(list_item)
            count += 1

        self._log(f"Loaded {count} history items from cache (out of {loaded_count} total, {loaded_count-count} ignored).")
        if count == 0:
             self.history_list_widget.addItem("No relevant history found after filtering. Click Refresh?")
    # ------------------------------------------

    # --- Add Method Stub: _start_history_fetch --- 
    def _start_history_fetch(self):
        """Starts the background thread to fetch chat history."""
        if self.history_fetch_worker and self.history_fetch_worker.isRunning():
            self._log("History fetch already in progress.")
            return

        self._log("🔄 Starting history fetch... (Non-headless browser will open)")
        self.refresh_history_btn.setEnabled(False) # Disable button during fetch

        self.history_fetch_worker = HistoryFetchThread()
        # Connect finished signal to handle result and re-enable button
        self.history_fetch_worker.finished.connect(self._on_history_fetch_done)
        self.history_fetch_worker.start()
    # --------------------------------------------

    # --- Add Slot: _on_history_fetch_done --- 
    def _on_history_fetch_done(self, success: bool, message: str):
        """Handles completion of the history fetch thread."""
        self._log(f"History Fetch Result: {message}")
        if success:
            # Reload the list widget from the updated file
            self._load_history_from_file()
        self.refresh_history_btn.setEnabled(True) # Re-enable button
        self.history_fetch_worker = None # Clear worker reference
    # -----------------------------------------

    # --- Add Saga Output Slot ---
    def on_saga_output_ready(self, text: str):
        self.saga_chronicle_tab.setPlainText(text)
        self._log("[SagaMode] ✅ Full Dreamscape Saga generated and displayed.")
        # Optionally save to file here
        # self.save_saga_to_file(text)

    # --- Add Handler for Worker Finishing ---
    def _saga_generation_finished(self):
        self._log("[SagaMode] Saga generation process completed.")
        # Clear orchestrator reference
        if hasattr(self, 'saga_runner'):
            self.saga_runner = None
        # Restore UI state
        self.generate_saga_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

    # --- Add Slot for Select All --- 
    def _select_all_history(self):
        item_count = self.history_list_widget.count()
        if item_count == 0:
            self._log("No history items to select.")
            return
            
        # Check if ALL items are already selected, if so, deselect all
        all_selected = True
        for i in range(item_count):
             item = self.history_list_widget.item(i)
             if item and not item.isSelected(): # Check if item exists before checking selection
                 all_selected = False
                 break
                 
        if all_selected:
             self._log("All items already selected, deselecting all.")
             self.history_list_widget.clearSelection()
        else:
             self._log(f"Selecting all {item_count} history items.")
             for i in range(item_count):
                 item = self.history_list_widget.item(i)
                 if item: # Ensure item exists
                     item.setSelected(True)
    # ------------------------------

    def _load_ignored_chat_titles(self) -> list[str]:
        """Loads ignored chat titles from ignored_chats.txt."""
        ignored_list = []
        ignore_file_path = "ignored_chats.txt"
        try:
            with open(ignore_file_path, "r", encoding="utf-8") as f:
                ignored_list = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            self._log(f"Successfully read ignore list: {ignore_file_path}")
        except FileNotFoundError:
            self._log(f"Ignore file not found: {ignore_file_path}. Creating default empty file.")
            try:
                 with open(ignore_file_path, "w", encoding="utf-8") as f:
                     f.write("# Add chat titles to ignore, one per line.\n")
                 self._log(f"Created default {ignore_file_path}")
            except Exception as e:
                 self._log(f"ERROR: Could not create default ignore file: {e}")
            return []
        except Exception as e:
            self._log(f"ERROR reading ignore file {ignore_file_path}: {e}")
            return []
        return ignored_list

    # --- Generate Full Saga Slot ---
    def on_generate_saga_clicked(self) -> None:
        """Handler for the 'Generate Full Saga' button click."""
        # 1. Prevent concurrent saga runs
        if self.saga_worker and self.saga_worker.isRunning():
            self._log("[SagaMode] Saga generation is already running.")
            return
        # 2. Ensure memory manager is available
        if not self.memory_manager:
            self._log("ERROR: Memory Manager not available. Cannot generate saga.")
            return

        # 3. Model selection
        selected_model = self.model_cmb.currentText()
        self._log(f"[SagaMode] Using model: {selected_model}")

        # 4. Check reverse order flag and gather chats
        should_reverse = self.reverse_chk.isChecked()
        order_desc = "newest-to-oldest (reversed)" if should_reverse else "oldest-to-newest (chronological)"
        self._log(f"[SagaMode] Processing order: {order_desc}")
        # Gather selected chat items and extract their stored contexts
        selected_items = self.get_ordered_filtered_chats(reverse=should_reverse)
        # Extract chat context dictionaries from QListWidgetItems
        chat_items = [item.data(Qt.ItemDataRole.UserRole) for item in selected_items]
        if not chat_items:
            self._log("[SagaMode] No chat history items found to generate saga from.")
            return

        # 5. Prepare the prompt template string
        prompt_template_str = self.prompt_te.toPlainText().strip()
        if not prompt_template_str:
            self._log("ERROR: Saga prompt text area is empty.")
            return

        # 6. Clear previous saga output
        self.saga_chronicle_tab.clear()

        # 7. Instantiate and connect the worker
        self.saga_worker = SagaGenerationWorker(
            memory_manager=self.memory_manager,
            chat_items=chat_items,
            selected_model=selected_model,
            prompt_template_str=prompt_template_str
        )
        self.saga_worker.log_signal.connect(self._log)
        self.saga_worker.saga_output_ready.connect(self.on_saga_output_ready)
        self.saga_worker.progress_signal.connect(self._log)
        self.saga_worker.error_signal.connect(self._log)
        self.saga_worker.finished.connect(self._saga_generation_finished)

        # 8. Start the worker thread
        self.saga_worker.start()

        # 9. Lock the UI
        self.generate_saga_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)

    def get_ordered_filtered_chats(self, reverse: bool = False) -> list[QListWidgetItem]:
        """Helper to get all current items from the history list widget.
        Optionally reverses the list before returning.
        """
        items = []
        for i in range(self.history_list_widget.count()):
            item = self.history_list_widget.item(i)
            # Basic check to exclude placeholders like "No history found..."
            if item and item.data(Qt.ItemDataRole.UserRole) is not None:
                items.append(item)
        
        # Reverse the list if requested
        if reverse:
            items.reverse()
            
        return items

    def _on_tab_double_click(self, index: int):
        if index == self.log_tab_index:
            self.log_tab.clear()

# ────────────────────────── bootstrap ──────────────────────────────
if __name__ == "__main__":
    mp.freeze_support()
    # Use CFG for logging level
    logging.basicConfig(level=CFG.LOG_LEVEL, format=CFG.LOG_FORMAT)

    # Initialize app first
    app = QApplication(sys.argv)

    # Create the main window instance BEFORE setting up the handler that needs it
    window = DreamscapeGenerator()

    # Pipe root logger into GUI log tab
    gui_handler = GuiLogHandler()
    # Connect the GUI handler to the window's log method
    gui_handler._emitter.log_signal.connect(lambda m: window._log(m))
    logging.getLogger().addHandler(gui_handler)

    # Load .env AFTER basic logging and GUI setup, before showing window?
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=CFG.DOTENV_PATH, override=True)
    logging.info(f"Env loaded: {CFG.DOTENV_PATH}")

    # Ensure logs dir exists
    os.makedirs("logs", exist_ok=True)

    # Show window and start event loop
    window.show()
    sys.exit(app.exec())

# --- Generation Worker Thread (for single cycles) ---
class GenerationWorker(QThread):
    # ... (Keep existing GenerationWorker code, assuming it's needed for single prompts) ...
    pass


# --- Saga Generation Worker Thread (Refined as per User Spec) ---
# Override inline SagaGenerationWorker with external implementation
from dreamscape_generator.threads.saga_worker import SagaGenerationWorker

# --- Final Imports Check ---
# Ensure these are present at the top of the file:
# import json, time
# from PyQt6.QtCore import QThread, pyqtSignal, Qt
# Need to add/verify:
# from memory_manager import UnifiedMemoryManager (Ensure this path is correct)
# from jinja2 import Environment, FileSystemLoader, select_autoescape (If using Jinja2 directly)
