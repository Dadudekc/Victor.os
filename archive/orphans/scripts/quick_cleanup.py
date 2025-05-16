import shutil
from pathlib import Path

backup_path = Path('runtime/cleanup_backups/backup_20250515_014945/runtime')
if backup_path.exists():
    shutil.rmtree(backup_path)
    print(f"Removed {backup_path}") 