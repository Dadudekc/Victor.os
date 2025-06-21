"""
Victor.os Enterprise Audit Log System
Phase 4: Enterprise Deployment - Append-only, encrypted, exportable audit logs
"""

import time
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from cryptography.fernet import Fernet
import structlog

logger = structlog.get_logger("audit_log")

class AuditLog:
    """Append-only, encrypted audit log system"""
    def __init__(self, log_dir: str = "audit_logs", encryption_key: Optional[bytes] = None):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.key = encryption_key or Fernet.generate_key()
        self.fernet = Fernet(self.key)
        self.log_file = self.log_dir / f"audit_{int(time.time())}.log"

    def append_event(self, event: Dict[str, Any]):
        event["timestamp"] = time.time()
        data = json.dumps(event).encode()
        encrypted = self.fernet.encrypt(data)
        with open(self.log_file, "ab") as f:
            f.write(encrypted + b"\n")
        logger.info("Audit event appended", event_type=event.get("event_type"))

    def export_log(self, export_path: str):
        with open(self.log_file, "rb") as f:
            encrypted_lines = f.readlines()
        decrypted = [self.fernet.decrypt(line.strip()).decode() for line in encrypted_lines if line.strip()]
        with open(export_path, "w") as out:
            for entry in decrypted:
                out.write(entry + "\n")
        logger.info("Audit log exported", export_path=export_path)

    def export_for_compliance(self, export_path: str, filter_func=None):
        with open(self.log_file, "rb") as f:
            encrypted_lines = f.readlines()
        decrypted = [json.loads(self.fernet.decrypt(line.strip()).decode()) for line in encrypted_lines if line.strip()]
        if filter_func:
            filtered = [entry for entry in decrypted if filter_func(entry)]
        else:
            filtered = decrypted
        with open(export_path, "w") as out:
            for entry in filtered:
                out.write(json.dumps(entry) + "\n")
        logger.info("Audit log compliance export", export_path=export_path, count=len(filtered)) 