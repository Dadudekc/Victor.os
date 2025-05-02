# Dream.OS - Autonomous Overnight Runner (PowerShell)
# Launches AgentBus, CursorOrchestrator, Supervisor, and core agents.

param(
    [switch]$DebugAgents # Add --debug flag to agent launches if specified
)

Write-Host "🚀 Launching Dream.OS Agent Swarm for Overnight Run..."

# --- Configuration ---
$PythonExecutable = "python" # Or specify absolute path e.g., "C:/Python39/python.exe"
$ProjectRoot = $PSScriptRoot # Assumes script is in the project root
$VenvPath = Join-Path $ProjectRoot ".venv"
$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
$RequirementsFile = Join-Path $ProjectRoot "requirements.txt"

# --- Prerequisites ---
Write-Host "🔧 Setting up Python Virtual Environment (venv)..."

# 1. Check if requirements.txt exists
if (-not (Test-Path $RequirementsFile)) {
    Write-Error "requirements.txt not found at $RequirementsFile. Cannot proceed."
    exit 1
}

# 2. Check/Create Virtual Environment
if (-not (Test-Path $VenvPath)) {
    Write-Host "   Virtual environment not found. Creating at $VenvPath..."
    try {
        & $PythonExecutable -m venv $VenvPath -ErrorAction Stop
        Write-Host "   Venv created successfully."
    } catch {
        Write-Error "Failed to create virtual environment at $VenvPath. Ensure Python is installed and accessible via '$PythonExecutable'. Error: $_"
        exit 1
    }
} else {
    Write-Host "   Existing virtual environment found at $VenvPath."
}

# 3. Check Python executable within Venv
if (-not (Test-Path $VenvPython)) {
    Write-Error "Python executable not found within the virtual environment at $VenvPython. Venv creation might have failed or is corrupt."
    exit 1
}
Write-Host "   Python executable found in venv: $VenvPython"

# 4. Install/Update Dependencies
Write-Host "   Installing/updating dependencies from $RequirementsFile..."
try {
    & $VenvPython -m pip install -r $RequirementsFile -ErrorAction Stop
    Write-Host "   Dependencies installed successfully."
} catch {
    Write-Error "Failed to install dependencies using pip from $RequirementsFile. Check the file and network connection. Error: $_"
    exit 1
}

# 5. Ensure core directories exist (agents create their own, but state/logs needed)
$StateDir = Join-Path $ProjectRoot "state"
$LogDir = Join-Path $ProjectRoot "logs"
if (-not (Test-Path $StateDir)) { New-Item -ItemType Directory -Path $StateDir | Out-Null }
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

# --- Launch Components ---

# Function to launch a component
function Start-DreamOSComponent {
    param(
        [string]$ComponentName,
        [string]$ScriptPath,
        [switch]$Debug = $false
    )

    # Use the venv python executable path defined earlier
    $venvPythonExec = $using:VenvPython

    # Construct the base python command arguments within the job's scriptblock
    if ($Debug) {
        Write-Host "   Launching $ComponentName (Debug Mode)..."
    } else {
        Write-Host "   Launching $ComponentName..."
    }

    try {
        # Pass the boolean state of the switch parameter
        $debugSwitchState = $Debug.IsPresent

        Start-Job -ScriptBlock {
            param($pythonExec, $scriptToRun, [bool]$enableDebug)

            # Assign the component name to a local variable within the job scope
            $localComponentName = $using:ComponentName

            # Set thread/process title for better identification (optional)
            # $Host.UI.RawUI.WindowTitle = "DreamOS Agent: $localComponentName"

            # Use the venv Python executable
            $cmdArgs = @($scriptToRun)
            if ($enableDebug) {
                # Check if the target script *accepts* a --debug flag
                # Placeholder: Assume most agent workers might?
                # A more robust solution might check script arguments or have config
                $cmdArgs += "--debug"
            }
            Write-Output "Executing: $pythonExec $cmdArgs"
            # Execute using the venv Python
            & $pythonExec $cmdArgs
            # Add error handling or logging from job if needed
            if ($LASTEXITCODE -ne 0) {
                # Use the local variable in the warning message
                Write-Warning "Component $localComponentName exited with code $LASTEXITCODE"
            }
        } -ArgumentList $venvPythonExec, $ScriptPath, $debugSwitchState | Out-Null
        Write-Host "   -> $ComponentName started in background job (via venv python)."
    } catch {
        # Use string formatting or concatenation to avoid parsing issue with $_ inside ""
        Write-Error ("Failed to start {0} from {1}: {2}" -f $ComponentName, $ScriptPath, $_)
    }
    Start-Sleep -Seconds 1 # Stagger launches slightly
}

# 1. Launch AgentBus
Start-DreamOSComponent -ComponentName "AgentBus" -ScriptPath "src/dreamos/core/agent_bus.py" -Debug

# 2. Launch CursorOrchestrator
Start-DreamOSComponent -ComponentName "CursorOrchestrator" -ScriptPath "src/dreamos/automation/run_orchestrator.py" -Debug:$DebugAgents

# 3. Launch SupervisorAgent (Reads human_directive.json)
Start-DreamOSComponent -ComponentName "SupervisorAgent" -ScriptPath "src/dreamos/agents/supervisor_agent.py" -Debug:$DebugAgents

# 4. Launch Agent 2 (Executor - Infra Surgeon / Cursor Worker)
# Assuming agent2_infra_surgeon.py is the correct entry point based on recent code.
Start-DreamOSComponent -ComponentName "Agent 2 (Executor)" -ScriptPath "src/dreamos/agents/agent2_infra_surgeon.py" -Debug:$DebugAgents

# 5. Launch Other Required Agents (e.g., Agent 5 - assuming it has a worker script if needed)
# Start-DreamOSComponent -ComponentName "Agent 5 (Captain)" -ScriptPath "src/dreamos/agents/agent5/worker.py" -Debug:$DebugAgents
# --> NOTE: Agent 5 (Captain, likely this assistant) runs within the primary interaction process, not launched separately here.

# --- Remove launches for non-existent Agent 1, 3, 4 workers ---
# Start-DreamOSComponent -ComponentName "Agent 1 (Planner)" -ScriptPath "src/dreamos/agents/agent_1/worker.py" -Debug:$DebugAgents
# Start-DreamOSComponent -ComponentName "Agent 3 (Verifier)" -ScriptPath "src/dreamos/agents/agent_3/worker.py" -Debug:$DebugAgents
# Start-DreamOSComponent -ComponentName "Agent 4 (Orchestrator)" -ScriptPath "src/dreamos/agents/agent_4/worker.py" -Debug:$DebugAgents

Write-Host "✅ All core Dream.OS components launched in background jobs."
Write-Host "   Launched: AgentBus, CursorOrchestrator, SupervisorAgent, Agent 2 (Executor)"
Write-Host "   Use 'Get-Job' to see running agent processes."
Write-Host "   Use 'Receive-Job -Job <JobObject>' to view output (or check logs/agent_X.log)."
Write-Host "   Use 'Stop-Job -Job <JobObject>' to terminate a specific agent."
Write-Host "   Use 'Get-Job | Stop-Job' to terminate all agents."
Write-Host "🌙 System running in Autonomous Overnight Mode."
