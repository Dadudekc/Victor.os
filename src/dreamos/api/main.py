from fastapi import FastAPI, HTTPException, Request
from .security import setup_security, validate_input

app = FastAPI()

# Setup security middleware
setup_security(app)

# Input validation schemas
COMMAND_SCHEMA = {
    'command': r'^[a-zA-Z0-9_]+$',
    'args': r'^[a-zA-Z0-9_\s]+$'
}

@app.post("/api/v1/commands")
async def execute_command(request: Request):
    data = await request.json()
    
    # Validate input
    if not validate_input(data, COMMAND_SCHEMA):
        raise HTTPException(status_code=400, detail="Invalid command format")
        
    # Process command
    return {"status": "success", "message": "Command executed"} 