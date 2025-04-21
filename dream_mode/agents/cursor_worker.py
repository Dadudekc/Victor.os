import time
from dream_mode.utils.channel_loader import get_blob_channel


def run(worker_id="worker-001"):
    """Simulated Cursor worker that pulls tasks and pushes results."""
    channel = get_blob_channel()
    print(f"⚙️ CursorWorker {worker_id} online.")

    while True:
        tasks = channel.pull_tasks()
        for task in tasks:
            task_id = task.get("id") or task.get("task_id")
            print(f"[{worker_id}] pulled: {task_id}")
            result = {
                "id": task_id,
                "content": f"Processed by {worker_id} at {time.time()}"
            }
            channel.push_result(result)
            print(f"[{worker_id}] pushed: {result['id']}")
        time.sleep(1) 