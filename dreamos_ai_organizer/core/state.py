import sqlite3, pathlib, json, time

class StateDB:
    def __init__(self, path):
        first = not pathlib.Path(path).exists()
        # Allow connections from multiple threads/processes (use with care)
        self.conn = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL;") # Improve concurrency
        self.conn.row_factory = sqlite3.Row # Access columns by name
        if first: self._init_schema()

    def _init_schema(self):
        cur = self.conn.cursor()
        # EDIT START: Add devlog table definition and indexes
        cur.executescript("""
        CREATE TABLE IF NOT EXISTS agents (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            task TEXT,
            points INTEGER DEFAULT 0,
            queue_depth INTEGER DEFAULT 0,
            last_command_ts REAL DEFAULT 0.0
        );
        CREATE TABLE IF NOT EXISTS tasks  (
            id TEXT PRIMARY KEY,
            title TEXT,
            lane TEXT
        );
        CREATE TABLE IF NOT EXISTS devlog (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            agent_name TEXT NOT NULL,
            event_type TEXT NOT NULL,
            status TEXT DEFAULT 'info', -- e.g., info, success, failure, warning
            details_json TEXT NOT NULL -- Store event specifics as JSON
        );
        CREATE INDEX IF NOT EXISTS idx_devlog_ts ON devlog (timestamp);
        CREATE INDEX IF NOT EXISTS idx_devlog_agent ON devlog (agent_name);
        -- Optionally, seed initial agents if needed
        INSERT OR IGNORE INTO agents (name) VALUES ('Agent-1'), ('Agent-2'), ('Agent-3'), ('Agent-4');
        """)
        # EDIT END
        self.conn.commit()

    # --- Agent Methods ---
    def fetch_agents(self):
        # Use row_factory for dict-like access
        cur = self.conn.execute("SELECT id, name, task, points, queue_depth, last_command_ts FROM agents ORDER BY name")
        return [dict(row) for row in cur] # Convert rows to dicts

    def update_agent_queue_status(self, agent_id: int, queue_depth: int):
        """Updates queue depth and last command timestamp for an agent."""
        agent_name = f"Agent-{agent_id}"
        ts = time.time()
        try:
            with self.conn: # Use connection as context manager for implicit commit/rollback
                cur = self.conn.execute(
                    "UPDATE agents SET queue_depth = ?, last_command_ts = ? WHERE name = ?",
                    (queue_depth, ts, agent_name)
                )
                if cur.rowcount == 0: # Agent didn't exist, insert
                     # Ensure agent exists if update affects 0 rows (optional)
                     self.conn.execute(
                         "INSERT OR IGNORE INTO agents (name, queue_depth, last_command_ts) VALUES (?, ?, ?)",
                         (agent_name, queue_depth, ts)
                     )
        except sqlite3.Error as e:
            # Consider logging the error instead of printing directly
            print(f"DB Error updating status for {agent_name}: {e}")

    # --- Task Methods ---
    def fetch_tasks(self, lane):
        cur = self.conn.execute("SELECT * FROM tasks WHERE lane=? ORDER BY id", (lane,))
        return [dict(row) for row in cur] # Convert rows to dicts

    def update_task_lane(self, task_id: str, new_lane: str):
         """Updates the lane for a given task."""
         try:
            with self.conn:
                self.conn.execute(
                    "UPDATE tasks SET lane = ? WHERE id = ?",
                    (new_lane, task_id)
                )
         except sqlite3.Error as e:
             print(f"DB Error updating lane for task {task_id}: {e}")

    # --- EDIT START: Add Command Log Methods ---
    def add_devlog_entry(self, agent_name: str, event_type: str, status: str, details: dict):
        """Adds an event to the devlog table."""
        ts = time.time()
        # Ensure details is always a dict before dumping
        if not isinstance(details, dict):
            details = {"message": str(details)}
        details_json = json.dumps(details)
        try:
            with self.conn:
                self.conn.execute(
                    "INSERT INTO devlog (timestamp, agent_name, event_type, status, details_json) VALUES (?, ?, ?, ?, ?)",
                    (ts, agent_name, event_type, status, details_json)
                )
        except sqlite3.Error as e:
            # Log this error properly in a real application
            print(f"DB Error adding devlog entry for {agent_name}: {e}")

    def fetch_devlog_entries(self, limit: int = 100):
        """Fetches the most recent devlog entries."""
        try:
            # Fetch rows directly as they are dict-like due to row_factory
            cur = self.conn.execute(
                "SELECT * FROM devlog ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
            return list(cur) # Return list of Row objects (dict-like)
        except sqlite3.Error as e:
            print(f"DB Error fetching devlog entries: {e}")
            return []
    # --- EDIT END --- 