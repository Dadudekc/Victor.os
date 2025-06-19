import asyncio
import json
from datetime import datetime, timedelta, date
from pathlib import Path
from dreamos.core.alert_manager import AlertManager
import os

async def simulate_agent_activity(alert_manager, day):
    """Simulates agent activity for a given day, introducing variations."""
    print(f"Simulating agent activity for Day {day+1}...")

    # Day-specific variations
    # Agent-1: Consistent performer
    await alert_manager.send_alert(
        alert_type="TASK_COMPLETE",
        message="Task completed successfully by Agent-1",
        severity="info",
        details={"agent_id": "1", "task_id": "task_123"}
    )
    if day % 3 == 0: # Extra task on some days
        await alert_manager.send_alert(
            alert_type="TASK_COMPLETE",
            message="Bonus task completed by Agent-1",
            severity="info",
            details={"agent_id": "1", "task_id": "task_bonus_1"}
        )

    # Agent-2: Experiences drift more often in later days
    if day > 2 and day % 2 == 0 : # Drifts on even days after day 3
        drift_start_time = datetime.now() - timedelta(minutes=10 + day) # Longer drift over time
        await alert_manager.send_alert(
            alert_type="DRIFT",
            message=f"Agent-2 drifted from expected state on Day {day+1}",
            severity="warning",
            details={"agent_id": "2", "drift_type": "timeout", "drift_start_time": drift_start_time.isoformat(), "drift_duration_seconds": (10 + day) * 60 }
        )
        await asyncio.sleep(1) # Simulate time for recovery
        await alert_manager.send_alert(
            alert_type="RECOVERY",
            message=f"Recovery attempt for Agent-2 on Day {day+1}",
            severity="info",
            details={"agent_id": "2", "recovery_type": "reboot", "recovery_successful": True, "recovery_time_seconds": 60 + day*5}
        )
    elif day % 4 == 0: # Occasional minor drift
         drift_start_time_minor = datetime.now() - timedelta(minutes=1) # e.g. 1 minute ago
         await alert_manager.send_alert(
            alert_type="DRIFT",
            message=f"Agent-2 minor drift on Day {day+1}",
            severity="warning",
            details={"agent_id": "2", "drift_type": "timeout", "drift_start_time": drift_start_time_minor.isoformat(), "drift_duration_seconds": 60}
        )
         await asyncio.sleep(0.5)
         await alert_manager.send_alert(
            alert_type="RECOVERY",
            message=f"Recovery for Agent-2 minor drift on Day {day+1}",
            severity="info",
            details={"agent_id": "2", "recovery_type": "reboot", "recovery_successful": True, "recovery_time_seconds": 30}
        )

    # Agent-3: Encounters errors, sometimes clustered
    if day % 2 != 0:  # Errors on odd days
        await alert_manager.send_alert(
            alert_type="ERROR",
            message=f"Agent-3 encountered error on Day {day+1}",
            severity="error",
            details={"agent_id": "3", "error_type": "processing_failed", "task_id": f"task_err_{day}"}
        )
        if day > 3: # Clustered errors in later days
            await asyncio.sleep(0.1)
            await alert_manager.send_alert(
                alert_type="ERROR",
                message=f"Agent-3 second error on Day {day+1}",
                severity="error",
                details={"agent_id": "3", "error_type": "dependency_missing", "task_id": f"task_err_{day}_b"}
            )
    elif day == 6: # Specific critical error on the last day
        await alert_manager.send_alert(
            alert_type="ERROR",
            message=f"Agent-3 critical system error on Day {day+1}",
            severity="critical",
            details={"agent_id": "3", "error_type": "critical_failure", "task_id": "task_critical"}
        )

    # Agent-4: New agent, starts tasks later
    if day >= 2:
        await alert_manager.send_alert(
            alert_type="TASK_COMPLETE",
            message=f"Task completed by Agent-4 on Day {day+1}",
            severity="info",
            details={"agent_id": "4", "task_id": f"task_agent4_{day}"}
        )

    # Agent-5: Sporadic activity, occasional errors
    if day % 3 == 1:
        await alert_manager.send_alert(
            alert_type="TASK_COMPLETE",
            message=f"Task completed by Agent-5 on Day {day+1}",
            severity="info",
            details={"agent_id": "5", "task_id": f"task_agent5_{day}"}
        )
    elif day % 4 == 2:
        await alert_manager.send_alert(
            alert_type="ERROR",
            message=f"Agent-5 minor error on Day {day+1}",
            severity="warning",
            details={"agent_id": "5", "error_type": "timeout", "task_id": f"task_err_agent5_{day}"}
        )

    print(f"Finished simulating agent activity for Day {day+1}.")


async def main():
    # Load configuration
    config_path = "config.json"
    if not os.path.exists(config_path):
        print(f"Configuration file {config_path} not found.")
        return
    with open(config_path, "r", encoding='utf-8') as f:
        config_data = json.load(f)
    
    alert_manager = AlertManager(config=config_data, workspace_root=".")

    for day in range(7): # Simulate 7 days
        current_date = date(2025, 5, 14) + timedelta(days=day)
        print(f"--- Simulating Day {day+1} ({current_date.isoformat()}) ---")
        
        # Simulate agent activity for the current day
        await simulate_agent_activity(alert_manager, day)
        
        # Generate digest for the current day
        # Ensure the generate_digest method can be called with a specific date
        print(f"Generating digest for {current_date.isoformat()}...")
        digest_data = await alert_manager.digest.generate_digest(specific_date=current_date)

        if digest_data and digest_data.get("trend_analysis"):
            print("\nTrend Analysis Results:")
            print(json.dumps(digest_data["trend_analysis"], indent=2))
        else:
            print("\nNo trend analysis data or digest data was not fully generated.")
        
        # Small delay to simulate passage of time between days
        if day < 6: # Don't sleep after the last day
            await asyncio.sleep(1) 
    
    print("\n--- Multi-Day Simulation Complete ---")

if __name__ == "__main__":
    # Ensure datetime is imported if not already at the top of the file
    from datetime import date, timedelta, datetime # Make sure all are available
    asyncio.run(main()) 