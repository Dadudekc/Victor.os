"""Utilities for parsing specification documents, like PROJECT_PLAN.md.

Relies on commonmarkextensions library for robust table parsing.
"""

import logging
from pathlib import Path

# Configure logger for this module FIRST to catch import issues if they log
logger = logging.getLogger(__name__)
# Setup basic config if running standalone for testing, or rely on app's config
if not logger.hasHandlers():
    logging.basicConfig(level=logging.DEBUG) # Or logging.INFO

logger.debug("spec_parser.py: Attempting to import commonmark and extensions...")
# Attempt to import commonmark and the table extension
try:
    import commonmark
    from commonmark_extensions.tables import ParserWithTables, RendererWithTables
    _commonmark_available = True
    logger.info("spec_parser.py: Successfully imported commonmark and commonmark_extensions.tables.")
except ImportError as e:
    _commonmark_available = False
    logger.warning(f"spec_parser.py: Failed to import commonmark or commonmark_extensions.tables. Parser functionality will be disabled. Error: {e}")
    # Define dummy classes if library not available to prevent import errors,
    # but functionality will be disabled.
    class NodeVisitor:
        pass
    class ParserWithTables:
        def parse(self, text):
            raise NotImplementedError("commonmarkextensions library not installed.")
    # Renderer not strictly needed for parsing, but included for completeness
    class RendererWithTables:
        pass

# Constants for known table headers (normalized)
EXPECTED_HEADERS_MAIN_NORM = [
    "task id", "description", "agent assigned", "status", "priority", "due date", "notes"
]
EXPECTED_HEADERS_LEGACY_MD_NORM = [
    "original category", "task description", "status (from tasks.md)", "priority (implied)", "notes"
]
# Add constants for other legacy table headers (e.g., from future_tasks.json section) if needed


class ProjectPlanTableVisitor(commonmark.NodeVisitor if _commonmark_available else NodeVisitor):
    """AST Visitor to find and process specific task tables within PROJECT_PLAN.md."""
    
    def __init__(self):
        if not _commonmark_available:
             logger.error("commonmarkextensions not installed. Cannot parse project plan tables.")
             # Or raise an error? For now, allow init but methods will fail.
        self.extracted_data = {
            "main_tasks": [],
            "legacy_tasks_md": [],
            # Add keys for other legacy sources if needed
        }
        self._current_table_type = None # To know which list to append to
        self._current_expected_headers = None # Store expected headers for current table

    def visit_Table(self, node):
        """Process a table node found in the AST."""
        if not _commonmark_available:
            return
            
        logger.debug("Found a Table node in AST.")
        headers = self._extract_headers(node) # Expects Table node
        normalized_headers = self._normalize_headers(headers)
        logger.debug(f"Table headers (raw): {headers}, (normalized): {normalized_headers}")

        self._current_table_type = None # Reset before checking
        self._current_expected_headers = None

        if normalized_headers == EXPECTED_HEADERS_MAIN_NORM:
            logger.info("Identified main task table.")
            self._current_table_type = "main_tasks"
            self._current_expected_headers = EXPECTED_HEADERS_MAIN_NORM
        elif normalized_headers == EXPECTED_HEADERS_LEGACY_MD_NORM:
            logger.info("Identified legacy tasks.md table.")
            self._current_table_type = "legacy_tasks_md"
            self._current_expected_headers = EXPECTED_HEADERS_LEGACY_MD_NORM
        # Add elif blocks for other expected legacy tables here
        else:
            logger.debug(f"Skipping table with unrecognized headers: {normalized_headers}")
            self.generic_visit(node) # Visit children anyway, but don't process rows
            return

        # If a known table type, specifically visit TableBody to process rows
        table_body = next((child for child in node.children if isinstance(child, commonmark.nodes.TableBody)), None)
        if table_body:
            # Only visit children of TableBody for row processing
            for child_row in table_body.children:
                if isinstance(child_row, commonmark.nodes.TableRow):
                    self.visit_TableRow(child_row) # Explicitly call on the TableRow in TableBody
        
        self._current_table_type = None # Reset after processing table
        self._current_expected_headers = None

    def visit_TableRow(self, node):
        """Process a row (TableRow node) within a recognized table's TableBody."""
        # This method is now called explicitly by visit_Table for rows in a TableBody
        # of a recognized table.
        if not _commonmark_available or self._current_table_type is None or self._current_expected_headers is None:
            # Not inside a recognized table's body, or headers not set.
            # Do not call generic_visit if we are not processing this row.
            return 
        
        row_cells_content = self._extract_row_cells(node) # Expects TableRow node
        if not row_cells_content:
            logger.debug("Skipping empty or unparseable row.")
            return

        logger.debug(f"Processing row with {len(row_cells_content)} cells for table type {self._current_table_type}")

        task_dict = self._map_row_to_headers(row_cells_content, self._current_expected_headers)
        if task_dict:
            # Check if the list exists for the current table type, defensive
            if self._current_table_type in self.extracted_data:
                self.extracted_data[self._current_table_type].append(task_dict)
                logger.debug(f"Appended task: {task_dict} to {self._current_table_type}")
            else:
                logger.warning(f"Table type '{self._current_table_type}' not initialized in extracted_data.")
        
        # Do not call generic_visit from here as we've processed the row's cells.
        # self.generic_visit(node) # This would re-process children like TableCell individually.

    # --- Helper Methods (Require Implementation based on commonmark AST) --- 

    def _extract_headers(self, table_node):
        """Extracts text content from header cells of a table node."""
        headers = []
        if not _commonmark_available:
            return headers
        
        # Expected structure: table -> thead -> tr -> th
        # commonmark.py AST: Table -> TableHead -> TableRow -> TableCell
        head = next((child for child in table_node.children if isinstance(child, commonmark.nodes.TableHead)), None)
        if head:
            header_row = next((child for child in head.children if isinstance(child, commonmark.nodes.TableRow)), None)
            if header_row:
                for cell in header_row.children:
                    if isinstance(cell, commonmark.nodes.TableCell):
                        headers.append(self._extract_cell_content(cell).strip())
        if not headers:
            logger.warning(f"Could not extract headers from table node: {table_node}")
        return headers

    def _extract_row_cells(self, row_node):
        """Extracts content from cells (td) within a row (tr) node."""
        # row_node is expected to be a commonmark.nodes.TableRow
        cells_content = []
        if not _commonmark_available or not isinstance(row_node, commonmark.nodes.TableRow):
            return cells_content
            
        for cell_node in row_node.children:
            if isinstance(cell_node, commonmark.nodes.TableCell):
                cells_content.append(self._extract_cell_content(cell_node)) # Keep raw content for now, strip in mapping
        return cells_content

    def _extract_cell_content(self, cell_node):
        """Extracts combined text content from a cell node, handling children recursively."""
        if not _commonmark_available or not cell_node:
            return ""

        text_parts = []
        
        # Iterate over all children of the cell
        for sub_node in cell_node.walker(): # Use walker to get all descendants
            # We are interested in event_type 'enter' for container nodes 
            # and the node itself if it's a leaf like Text, SoftBreak etc.
            # The walker yields (node, entering), so we check node type.
            current_node = sub_node[0] # sub_node is a tuple (node, entering_boolean)
            
            if isinstance(current_node, commonmark.nodes.Text):
                text_parts.append(current_node.literal)
            elif isinstance(current_node, commonmark.nodes.SoftBreak):
                text_parts.append(" ") # Replace soft breaks with a space
            elif isinstance(current_node, commonmark.nodes.LineBreak):
                text_parts.append("\n") # Explicit newline
            elif isinstance(current_node, commonmark.nodes.HtmlInline) and current_node.literal.lower().strip() == "<br>":
                text_parts.append("\n") # Treat <br> as newline
            # elif isinstance(current_node, commonmark.nodes.Code):
            #     text_parts.append(current_node.literal)
            # Add other inline elements if needed, e.g., Code, Emph, Strong, Link text
            # For Link, one might want to extract node.destination or the text part.
            # For now, focusing on plain text extraction.

        return "".join(text_parts)

    def _normalize_headers(self, headers_list):
        """Converts header list to lowercase, stripped strings for comparison."""
        return [str(h).lower().strip() for h in headers_list if h]

    def _map_row_to_headers(self, row_cell_contents, headers_list_normalized):
        """Maps a list of cell contents to a dictionary using normalized headers."""
        task_data = {}
        num_headers = len(headers_list_normalized)
        num_cells_in_row = len(row_cell_contents)

        for i in range(min(num_headers, num_cells_in_row)):
            header = headers_list_normalized[i]
            # Apply basic cleaning to extracted content
            cell_value = str(row_cell_contents[i]).strip() 
            task_data[header] = cell_value
        
        if num_cells_in_row < num_headers:
            for i in range(num_cells_in_row, num_headers):
                header = headers_list_normalized[i]
                task_data[header] = None # Pad missing cells
        
        if num_cells_in_row > num_headers:
            logger.warning(f"Row has more cells ({num_cells_in_row}) than headers ({num_headers}). Ignoring extra cells.")
            # Store extra data if needed: task_data["_extra_cells"] = row_cell_contents[num_headers:]

        return task_data


def parse_project_plan_tasks(file_path: str = "specs/PROJECT_PLAN.md") -> dict | None:
    """Parses the PROJECT_PLAN.md file and extracts task data from known tables.
    
    Args:
        file_path (str): The path to the PROJECT_PLAN.md file.

    Returns:
        dict | None: A dictionary containing lists of tasks keyed by table type 
                      (e.g., 'main_tasks', 'legacy_tasks_md'), or None on error.
    """
    if not _commonmark_available:
        logger.error("Cannot parse project plan: commonmarkextensions library not found.")
        return None
        
    try:
        plan_path = Path(file_path)
        if not plan_path.is_file():
            logger.error(f"Project plan file not found: {file_path}")
            return None
            
        markdown_content = plan_path.read_text(encoding="utf-8")
        
        parser = ParserWithTables()
        ast = parser.parse(markdown_content)
        
        visitor = ProjectPlanTableVisitor()
        visitor.visit(ast)

        logger.info(f"Parsed project plan. Found {len(visitor.extracted_data['main_tasks'])} main tasks.")
        # Add logging for legacy tasks found if needed

        return visitor.extracted_data

    except NotImplementedError as nie:
        logger.error(f"Parsing failed: {nie}") # Likely library import issue
        return None
    except Exception as e:
        logger.exception(f"Error parsing project plan {file_path}: {e}") # Log traceback
        return None

# Example usage (for testing purposes)
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG) # Enable debug logging for testing
    logger.info("Testing spec_parser...")
    parsed_tasks = parse_project_plan_tasks()
    if parsed_tasks:
        print("--- Main Tasks ---")
        for task in parsed_tasks.get("main_tasks", []):
            print(task)
        # Print legacy tasks if needed
        # print("--- Legacy Tasks (TASKS.md) ---")
        # for task in parsed_tasks.get("legacy_tasks_md", []):
        #     print(task)
    else:
        print("Failed to parse tasks.") 