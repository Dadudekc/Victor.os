import re
from typing import Any, Dict, Optional

from bs4 import BeautifulSoup


def extract_task_metadata(html_content: str) -> Optional[Dict[str, Any]]:
    """
    Extract task metadata from a ChatGPT HTML message.
    Args:
        html_content: The HTML content from ChatGPT's response
    Returns:
        A dictionary with extracted metadata, or None if not found
    """
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        # Example: look for a div with class 'task-metadata'
        meta_div = soup.find("div", {"class": "task-metadata"})
        if not meta_div:
            return None
        # Extract key-value pairs from the metadata div
        metadata = {}
        for row in meta_div.find_all("div", {"class": "meta-row"}):
            key_elem = row.find("span", {"class": "meta-key"})
            value_elem = row.find("span", {"class": "meta-value"})
            if key_elem and value_elem:
                key = key_elem.get_text(strip=True)
                value = value_elem.get_text(strip=True)
                metadata[key] = value
        return metadata if metadata else None
    except Exception as e:
        print(f"Error extracting task metadata: {e}")
        return None


def extract_task_id(text: str) -> Optional[str]:
    """
    Extract a task ID from a string using regex.
    Args:
        text: The text to search for a task ID
    Returns:
        The extracted task ID, or None if not found
    """
    match = re.search(r"Task ID: (\w+)", text)
    if match:
        return match.group(1)
    return None
