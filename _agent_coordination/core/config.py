from dataclasses import dataclass

@dataclass
class CursorCoordinatorConfig:
    """
    Configuration settings for CursorChatCoordinator.
    """
    ocr_timeout: float = 60.0  # seconds to wait for OCR response
    ocr_retry_interval: float = 3.0  # seconds between OCR capture attempts
    max_interpret_loops: int = 10  # max cycles of interpret/dispatch
    sub_task_timeout: float = 120.0  # seconds to wait for sub-task feedback 
