"""
Interface to ChatGPTResponder via HTTP auto-fix endpoint.
"""
from typing import Dict, Any
import requests
from config import Config


def refine(context: Dict[str, Any]) -> str:
    """
    Send draft text to the AutoFix service for refinement.
    Expects Config.CHATGPT_URL to be the '/patch' endpoint.
    Returns the refined text (joined patches or direct response).
    """
    # Prepare payload: using 'source' and 'purpose'
    payload = {
        "source": context.get("reply", context.get("prompt", "")),
        "purpose": "refine"
    }
    try:
        resp = requests.post(Config.CHATGPT_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()
        # If the service returns a list of patch objects
        if isinstance(data, list):
            return "\n".join([p.get("patch", "") for p in data])
        # If service wraps text in a dict
        if isinstance(data, dict) and "refined" in data:
            return data.get("refined", "")
        # Otherwise assume plain string
        return str(data)
    except Exception as e:
        print(f"❌ ChatGPT refinement failed: {e}")
        # Fallback: return original draft
        return context.get("reply", context.get("prompt", "")) 
