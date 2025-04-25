from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import uvicorn

# Import your ChatGPTResponder (ensure this exists in core.hooks)
try:
    from core.hooks.chatgpt_responder import ChatGPTResponder
except ImportError:
    ChatGPTResponder = None

# Instantiate the responder (dev_mode on by default)
responder = ChatGPTResponder(dev_mode=True) if ChatGPTResponder else None

# Pydantic models for request and response
class PatchRequest(BaseModel):
    file_path: str
    error_msg: str
    source_code: str

class PatchResponse(BaseModel):
    file_path: str
    patch: str

# Create the FastAPI app
app = FastAPI(title="Dream.OS AutoFix Service")

@app.post("/patch", response_model=List[PatchResponse])
def generate_patches(req: PatchRequest) -> List[PatchResponse]:
    """
    Generate code patches for a given file, error message, and source code.
    Returns a list of PatchResponse with unified-diff or edit instructions.
    """
    if not responder:
        raise HTTPException(status_code=501, detail="ChatGPTResponder not available")
    # Build context for the responder
    context: Dict[str, Any] = {
        "file_path": req.file_path,
        "error_msg": req.error_msg,
        "source_code": req.source_code,
    }
    # Call the responder to get patches (stubbed; implement in ChatGPTResponder)
    try:
        raw_patches = responder.respond_to_patch_request(context)  # type: ignore[attr-defined]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Transform raw patches into response models
    responses: List[PatchResponse] = []
    for p in raw_patches:
        responses.append(
            PatchResponse(file_path=p.get("file_path", req.file_path), patch=p.get("patch", ""))
        )
    return responses

if __name__ == "__main__":
    # Run with: python autofix_service.py
    uvicorn.run("autofix_service:app", host="127.0.0.1", port=8000, reload=True) 