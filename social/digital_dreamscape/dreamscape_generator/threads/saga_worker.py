from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import QListWidgetItem
from dreamscape_generator.src.generation_engine import generate_episode as chat_completion
from jinja2 import Template
import uuid
from dreamscape_generator.src.core.monitoring.prompt_execution_monitor import PromptExecutionMonitor

# Simple template engine using jinja2
class TemplateEngine:
    @staticmethod
    def render_string(template_str, context):
        return Template(template_str).render(context)

class SagaGenerationWorker(QThread):
    """
    Background thread to generate a full saga by iterating over chat items,
    rendering prompts via Jinja2, calling chat_completion, and emitting
    progress, results, and errors back to the GUI.
    """
    # Signals
    saga_output_ready = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    error_signal = pyqtSignal(str)
    finished = pyqtSignal()
    log_signal = pyqtSignal(str)          # Thread-safe log messages to GUI

    def __init__(self, memory_manager, chat_items, selected_model, prompt_template_str):
        super().__init__()
        self.memory_manager = memory_manager
        self.chat_items = chat_items
        self.selected_model = selected_model
        self.prompt_template_str = prompt_template_str
        self.is_running = True
        # Initialize the prompt execution monitor
        self.monitor = PromptExecutionMonitor(memory=self.memory_manager,
                                             dispatcher=self)

    def stop(self):
        """Allows external callers to stop saga generation gracefully."""
        self.is_running = False

    def run(self):
        total = len(self.chat_items)
        for idx, chat_context in enumerate(self.chat_items, start=1):
            if not self.is_running:
                break
            # If passed a QListWidgetItem, extract its stored context dict
            if isinstance(chat_context, QListWidgetItem):
                try:
                    chat_context = chat_context.data(Qt.ItemDataRole.UserRole)
                except Exception:
                    # Leave chat_context as-is if unwrapping fails
                    self.log_signal.emit(f"[SagaWorker] WARNING prompt {idx}: could not unwrap QListWidgetItem")

            # 1) Render the prompt
            try:
                self.log_signal.emit(f"[SagaWorker] Rendering prompt {idx}/{total}")
                rendered_prompt = TemplateEngine.render_string(
                    self.prompt_template_str, chat_context
                )
            except Exception as e:
                msg = f"[SagaWorker] ERROR rendering prompt {idx}: {e}"
                self.log_signal.emit(msg)
                self.error_signal.emit(msg)
                continue

            # 2) Call the LLM with execution monitoring
            prompt_id = str(uuid.uuid4())
            self.monitor.start_monitoring(prompt_id)
            try:
                self.log_signal.emit(f"[SagaWorker] Calling chat_completion for {idx}/{total} (prompt_id={prompt_id})")
                result = chat_completion(rendered_prompt, self.selected_model)
                if result is None:
                    raise ValueError("Empty response from chat_completion")
                # Report success to monitor
                self.monitor.report_success(prompt_id, result)
            except Exception as e:
                # Report failure to monitor
                self.monitor.report_failure(prompt_id, reason=str(e))
                msg = f"[SagaWorker] ERROR in chat_completion {idx}: {e}"
                self.log_signal.emit(msg)
                self.error_signal.emit(msg)
                continue

            # 3) Emit result and progress
            self.saga_output_ready.emit(result)
            self.progress_signal.emit(idx)

        # 4) All done or stopped
        self.finished.emit() 
