You are creating the core task management system for Dream.OS.

🎯 Objective:
Build a `TaskNexus` class that serves as a local task queue and state tracker. It reads/writes from a shared JSON file (`runtime/task_list.json`) and enables multiple agents to coordinate work.

📦 File: `dream_mode/task_nexus/task_nexus.py`

---

✅ Features to Implement:

```python
class TaskNexus:
    def __init__(self, task_file="runtime/task_list.json"):
        ...
```

### Required Methods:

1. `get_next_task(agent_id=None, type_filter=None)`
   - Return first task where `status == "pending"`
   - Mark it `claimed`, add `claimed_by = agent_id`

2. `add_task(task_dict)`
   - Append new task (with `status="pending"` by default)
   - Save to file

3. `update_task_status(task_id, status)`
   - Change status of given task (`completed`, `failed`, etc.)

4. `get_all_tasks(status=None)`
   - Return all tasks or filter by status

5. `stats()`
   - Return a `Counter` of task statuses for dashboarding

---

💾 Behavior:
- File auto-creates if missing
- Internal `_load()` and `_save()` helpers handle JSON
- Should handle multiple agents calling in parallel (atomic ops preferred)

---

📁 Save and overwrite the file after generation:

```json
{
  "action": "save_file",
  "params": {
    "path": "dream_mode/task_nexus/task_nexus.py",
    "content": "<your implementation here>"
  }
}
```

Begin. 