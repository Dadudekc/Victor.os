import os
from pathlib import Path

from initialize_agent_manifests import initialize_agent_manifests
from services.service_manager import DreamOSServiceManager
from update_scoreboard import update_scoreboard
from update_system_memory import record_activity


def setup_directories():
    """Create necessary directories for Dream.OS."""
    directories = [
        "runtime/agent_comms/agent_mailboxes",
        "runtime/governance",
        "runtime/dashboard",
        "runtime/scripts",
        "runtime/services",
        "runtime/logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {directory}")

def initialize_system():
    """Initialize the Dream.OS system."""
    print("Setting up Dream.OS...")
    
    # Create directories
    setup_directories()
    
    # Initialize agent manifests
    print("\nInitializing agent manifests...")
    initialize_agent_manifests()
    
    # Record initial system memory
    print("\nRecording initial system memory...")
    record_activity(
        "architecture_decision",
        "system",
        component="Dream.OS Core",
        decision_type="initialization",
        rationale="Initial system setup and architecture decisions"
    )
    
    # Update scoreboard
    print("\nUpdating scoreboard...")
    data = update_scoreboard()
    print(f"Scoreboard updated at {data['last_updated']}")
    
    # Start service manager
    print("\nStarting Dream.OS services...")
    manager = DreamOSServiceManager()
    manager.start()
    
    print("\nDream.OS setup complete!")

def verify_setup():
    """Verify the Dream.OS setup."""
    required_files = [
        "runtime/agent_comms/agent_mailboxes/agent_manifest.json",
        "runtime/governance/system_memory_ledger.jsonl",
        "runtime/dashboard/scoreboard_data.json",
        "runtime/services/sync_service.py",
        "runtime/services/service_manager.py"
    ]
    
    print("\nVerifying setup...")
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✓ {file_path} exists")
        else:
            print(f"✗ {file_path} missing")
    
    # Check service status
    manager = DreamOSServiceManager()
    status = manager.get_service_status()
    print("\nService Status:")
    for service, info in status.items():
        print(f"{service}: {'Running' if info['running'] else 'Stopped'}")

if __name__ == "__main__":
    initialize_system()
    verify_setup() 