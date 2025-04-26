# social/core/coordination/cursor/editor_service.py

import logging
from typing import Optional

# Assuming CursorEditorController is defined elsewhere and imported
from .cursor_editor_controller import CursorEditorController # Corrected import

logger = logging.getLogger("CursorEditorService")

class CursorEditorService:
    def __init__(self, editor_controller: CursorEditorController):
        """Initializes the service with an editor controller instance."""
        # TODO: Add type hint for editor_controller when its definition is known
        if not isinstance(editor_controller, CursorEditorController):
             raise TypeError("controller must be an instance of CursorEditorController")
        self.editor_controller = editor_controller
        logger.info(f"CursorEditorService initialized with controller: {type(editor_controller).__name__}")

    async def open_file(self, file_path: str) -> bool:
        """
        Opens the specified file in the editor.
        """
        try:
            logger.info(f"Service request: Opening file in editor: {file_path}")
            # Assuming editor_controller.open_file is an async method or we adapt
            # If synchronous, might need asyncio.to_thread
            return await self.editor_controller.open_file(file_path)
        except Exception as e:
            logger.error(f"Failed to open file '{file_path}': {e}", exc_info=True)
            return False

    async def insert_text(self, text: str, at_line: Optional[int] = None) -> bool:
        """
        Inserts text into the editor. If `at_line` is specified, insert at that line.
        Otherwise, insert at cursor position.
        """
        try:
            logger.info(f"Service request: Inserting text (len={len(text)}), at_line={at_line}")
            # Assuming editor_controller.insert_text is async
            return await self.editor_controller.insert_text(text, at_line=at_line)
        except Exception as e:
            logger.error(f"Failed to insert text: {e}", exc_info=True)
            return False

    async def get_text(self) -> Optional[str]:
        """
        Gets the full text content from the editor.
        """
        try:
            logger.debug("Service request: Get editor text")
            # Assuming editor_controller.get_text is async
            return await self.editor_controller.get_text()
        except Exception as e:
            logger.error(f"Failed to get editor text: {e}", exc_info=True)
            return None

    async def set_text(self, text: str) -> bool:
        """
        Overwrites the entire text in the editor with the provided string.
        """
        try:
            logger.info(f"Service request: Setting full text (len={len(text)})")
            # Assuming editor_controller.set_text is async
            return await self.editor_controller.set_text(text)
        except Exception as e:
            logger.error(f"Failed to set editor text: {e}", exc_info=True)
            return False 
