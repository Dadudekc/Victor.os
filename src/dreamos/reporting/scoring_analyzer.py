# src/dreamos/reporting/scoring_analyzer.py
import json
import logging
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- Configuration ---
# Assuming completed tasks are stored here after processing
# TODO: Update this path based on Agent 02's implementation
DEFAULT_TASK_DATA_PATH = (
    Path(__file__).resolve().parents[3] / "runtime" / "tasks" / "completed_tasks.json"
)

# --- Data Loading ---


def load_task_data(data_path: Path = DEFAULT_TASK_DATA_PATH) -> List[Dict[str, Any]]:
    """Loads completed task data from the specified JSON file."""
    if not data_path.exists():
        logger.warning(f"Task data file not found: {data_path}. No data to analyze.")
        return []

    try:
        with open(data_path, "r", encoding="utf-8") as f:
            content = f.read()
            if not content.strip():
                logger.info(f"Task data file is empty: {data_path}")
                return []
            tasks = json.loads(content)
            if not isinstance(tasks, list):
                logger.error(f"Task data file does not contain a list: {data_path}")
                return []
            logger.info(f"Loaded {len(tasks)} task records from {data_path}")
            return tasks
    except json.JSONDecodeError:
        logger.error(
            f"Failed to decode JSON from task data file: {data_path}", exc_info=True
        )
        return []
    except Exception as e:
        logger.error(f"Failed to load task data from {data_path}: {e}", exc_info=True)
        return []


# --- Metric Calculation ---


def calculate_metrics(tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculates scoring and performance metrics from task data."""
    logger.info(f"Calculating metrics for {len(tasks)} tasks...")
    if not tasks:
        return {}

    total_tasks = len(tasks)
    completed_tasks = [t for t in tasks if t.get("status") == "completed"]
    failed_tasks = [t for t in tasks if t.get("status") == "failed"]
    perm_failed_tasks = [t for t in tasks if t.get("status") == "permanently_failed"]

    # Overall metrics
    success_rate = (len(completed_tasks) / total_tasks * 100) if total_tasks else 0
    total_retries = sum(t.get("retry_count", 0) for t in tasks)
    avg_retries_all = (total_retries / total_tasks) if total_tasks else 0

    # Scoring metrics (only for tasks with scores)
    scored_tasks = [
        t for t in tasks if t.get("scoring") and "total_score" in t["scoring"]
    ]
    scores = [t["scoring"]["total_score"] for t in scored_tasks]
    avg_score = statistics.mean(scores) if scores else 0
    median_score = statistics.median(scores) if scores else 0

    # Per-agent metrics
    agent_metrics = defaultdict(
        lambda: {
            "total": 0,
            "completed": 0,
            "failed": 0,
            "perm_failed": 0,
            "retries": 0,
            "scores": [],
        }
    )

    for task in tasks:
        agent_id = task.get("agent_id", "UnknownAgent")
        agent_metrics[agent_id]["total"] += 1
        agent_metrics[agent_id]["retries"] += task.get("retry_count", 0)
        status = task.get("status")
        if status == "completed":
            agent_metrics[agent_id]["completed"] += 1
        elif status == "failed":
            agent_metrics[agent_id]["failed"] += 1
        elif status == "permanently_failed":
            agent_metrics[agent_id]["perm_failed"] += 1

        if task.get("scoring") and "total_score" in task["scoring"]:
            agent_metrics[agent_id]["scores"].append(task["scoring"]["total_score"])

    # Calculate derived agent metrics
    final_agent_metrics = {}
    for agent_id, data in agent_metrics.items():
        total = data["total"]
        scores = data["scores"]
        final_agent_metrics[agent_id] = {
            "total_tasks": total,
            "completed": data["completed"],
            "failed": data["failed"],
            "permanently_failed": data["perm_failed"],
            "success_rate": (data["completed"] / total * 100) if total else 0,
            "avg_retries": (data["retries"] / total) if total else 0,
            "avg_score": statistics.mean(scores) if scores else 0,
            "median_score": statistics.median(scores) if scores else 0,
            "scored_task_count": len(scores),
        }

    metrics = {
        "overall": {
            "total_tasks": total_tasks,
            "completed_count": len(completed_tasks),
            "failed_count": len(failed_tasks),
            "perm_failed_count": len(perm_failed_tasks),
            "success_rate_pct": success_rate,
            "avg_retries": avg_retries_all,
            "total_scored_tasks": len(scored_tasks),
            "avg_score": avg_score,
            "median_score": median_score,
        },
        "per_agent": final_agent_metrics,
    }
    logger.info("Metrics calculation complete.")
    return metrics


# --- Report Generation ---


def generate_console_report(metrics: Dict[str, Any]):
    """Prints a summary report to the console."""
    logger.info("Generating console report...")
    print("\n" + "=" * 60)
    print("          DREAM.OS SCORING ANALYTICS REPORT (Prototype)")
    print("=" * 60)

    if not metrics:
        print("\nNo metrics calculated.")
        print("=" * 60)
        return

    # --- Overall Summary ---
    overall = metrics.get("overall", {})
    print("\n--- Overall Performance ---")
    print(f"Total Tasks Analyzed: {overall.get('total_tasks', 0)}")
    print(f"  - Completed:        {overall.get('completed_count', 0)}")
    print(f"  - Failed (Retryable): {overall.get('failed_count', 0)}")
    print(f"  - Failed (Permanent): {overall.get('perm_failed_count', 0)}")
    print(f"Overall Success Rate: {overall.get('success_rate_pct', 0):.2f}%")
    print(f"Average Retries/Task: {overall.get('avg_retries', 0):.2f}")
    print("\n--- Overall Scoring --- (Based on tasks with scores)")
    print(f"Total Tasks Scored:   {overall.get('total_scored_tasks', 0)}")
    print(f"Average Score:        {overall.get('avg_score', 0):.2f}")
    print(f"Median Score:         {overall.get('median_score', 0):.2f}")

    # --- Per-Agent Summary ---
    per_agent = metrics.get("per_agent", {})
    print("\n--- Performance By Agent ---")
    if not per_agent:
        print("No per-agent data available.")
    else:
        for agent_id, data in sorted(per_agent.items()):
            print(f"\n  Agent: {agent_id}")
            print(f"    Tasks Processed:    {data.get('total_tasks', 0)}")
            print(f"    Success Rate:       {data.get('success_rate', 0):.2f}%")
            print(f"    Avg Retries:        {data.get('avg_retries', 0):.2f}")
            print(
                f"    Avg Score (Scored): {data.get('avg_score', 0):.2f} (from {data.get('scored_task_count', 0)} tasks)"
            )
            print(f"    Failures (Perm):    {data.get('permanently_failed', 0)}")

    print("\n" + "=" * 60)
    logger.info("Console report generated.")


# --- Main Execution ---


def main():
    """Main function to load data, calculate metrics, and generate report."""
    tasks = load_task_data()
    if not tasks:
        return  # Exit if no data

    metrics = calculate_metrics(tasks)
    generate_console_report(metrics)


if __name__ == "__main__":
    # Ensure runtime/tasks directory exists for the dummy file creation
    DEFAULT_TASK_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Create a dummy data file if it doesn't exist for testing
    if not DEFAULT_TASK_DATA_PATH.exists():
        dummy_tasks = [
            {
                "task_id": "task_001",
                "agent_id": "agent_02",
                "status": "completed",
                "completed_at": datetime(2024, 1, 1, 10, 0, 0).isoformat(),
                "retry_count": 0,
                "scoring": {"total_score": 90},
            },
            {
                "task_id": "task_002",
                "agent_id": "agent_01",
                "status": "failed",
                "completed_at": datetime(2024, 1, 1, 10, 5, 0).isoformat(),
                "retry_count": 2,
                "scoring": {"total_score": 45},
            },
            {
                "task_id": "task_003",
                "agent_id": "agent_02",
                "status": "completed",
                "completed_at": datetime(2024, 1, 1, 10, 10, 0).isoformat(),
                "retry_count": 1,
                "scoring": {"total_score": 75},
            },
            {
                "task_id": "task_004",
                "agent_id": "agent_01",
                "status": "permanently_failed",
                "completed_at": datetime(2024, 1, 1, 10, 15, 0).isoformat(),
                "retry_count": 3,  # Max retries hit
                # No score for permanently failed
            },
        ]
        try:
            with open(DEFAULT_TASK_DATA_PATH, "w", encoding="utf-8") as f:
                json.dump(dummy_tasks, f, indent=2)
            logger.info(f"Created dummy task data file at {DEFAULT_TASK_DATA_PATH}")
        except Exception as e:
            logger.error(f"Failed to create dummy task data file: {e}")

    main()
