# Dream.OS Command Dashboard

A PyQt5-based dashboard for monitoring and managing Dream.OS agents and project analysis.

## Features

### Agent Management Tab
- View all active agents
- Monitor task queue status
- Check last devlog timestamp
- Resume agent execution
- Trigger agent onboarding

### Project Analysis Tab
- Display project metadata from `chatgpt_project_context.json`
- Show file statistics from `project_analysis.json`
- List dependencies from `dependency_cache.json`
- Monitor orphaned files and missing documentation

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the dashboard:
```bash
python agent_dashboard.py
```

## File Structure

- `agent_dashboard.py` - Main dashboard implementation
- `requirements.txt` - Python dependencies
- `README.md` - This documentation

## Data Sources

The dashboard reads from the following JSON files in the project root:
- `chatgpt_project_context.json` - Project metadata and structure
- `project_analysis.json` - File statistics and analysis
- `dependency_cache.json` - Package dependencies

## Development

The dashboard uses PyQt5 for the UI and automatically refreshes the agent status every 5 seconds. The project analysis tab updates when the dashboard is launched. 