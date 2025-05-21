# Task System Migration Guide

## Overview

This guide provides step-by-step instructions for migrating between different versions of the task system, handling data format changes, and ensuring system stability during the migration process.

## Migration Types

### 1. Version Migration

#### Version 1.x to 2.x
```python
def migrate_v1_to_v2(task_dir: str):
    """Migrate task system from v1.x to v2.x."""
    # Create backup
    backup_dir = f"{task_dir}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copytree(task_dir, backup_dir)
    
    # Migrate task boards
    for board_file in Path(task_dir).glob("*.json"):
        # Read v1 format
        with open(board_file, "r") as f:
            tasks = json.load(f)
        
        # Convert to v2 format
        migrated_tasks = []
        for task in tasks:
            migrated_task = {
                "task_id": task["id"],  # Renamed from id to task_id
                "description": task["description"],
                "status": task["state"],  # Renamed from state to status
                "created_at": task["created_at"],
                "updated_at": task.get("updated_at", task["created_at"]),
                "metadata": task.get("metadata", {})
            }
            migrated_tasks.append(migrated_task)
        
        # Write v2 format
        with open(board_file, "w") as f:
            json.dump(migrated_tasks, f, indent=2)
    
    return backup_dir
```

#### Version 2.x to 3.x
```python
def migrate_v2_to_v3(task_dir: str):
    """Migrate task system from v2.x to v3.x."""
    # Create backup
    backup_dir = f"{task_dir}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copytree(task_dir, backup_dir)
    
    # Migrate task boards
    for board_file in Path(task_dir).glob("*.json"):
        # Read v2 format
        with open(board_file, "r") as f:
            tasks = json.load(f)
        
        # Convert to v3 format
        migrated_tasks = []
        for task in tasks:
            migrated_task = {
                "task_id": task["task_id"],
                "description": task["description"],
                "status": task["status"],
                "created_at": task["created_at"],
                "updated_at": task["updated_at"],
                "metadata": task["metadata"],
                "version": "3.0",  # Added version field
                "tags": task["metadata"].get("tags", []),  # Moved tags to top level
                "priority": task["metadata"].get("priority", "normal")  # Added priority
            }
            migrated_tasks.append(migrated_task)
        
        # Write v3 format
        with open(board_file, "w") as f:
            json.dump(migrated_tasks, f, indent=2)
    
    return backup_dir
```

### 2. Data Format Migration

#### JSON Schema Updates
```python
def update_schema(schema_path: str, new_schema: dict):
    """Update JSON schema for task validation."""
    # Backup existing schema
    backup_path = f"{schema_path}.bak"
    shutil.copy2(schema_path, backup_path)
    
    # Write new schema
    with open(schema_path, "w") as f:
        json.dump(new_schema, f, indent=2)
    
    return backup_path
```

#### Task Format Migration
```python
def migrate_task_format(tasks: List[dict], format_version: str) -> List[dict]:
    """Migrate tasks to new format version."""
    if format_version == "2.0":
        return [
            {
                "task_id": task["id"],
                "description": task["description"],
                "status": task["state"],
                "created_at": task["created_at"],
                "updated_at": task.get("updated_at", task["created_at"]),
                "metadata": task.get("metadata", {})
            }
            for task in tasks
        ]
    elif format_version == "3.0":
        return [
            {
                "task_id": task["task_id"],
                "description": task["description"],
                "status": task["status"],
                "created_at": task["created_at"],
                "updated_at": task["updated_at"],
                "metadata": task["metadata"],
                "version": "3.0",
                "tags": task["metadata"].get("tags", []),
                "priority": task["metadata"].get("priority", "normal")
            }
            for task in tasks
        ]
    else:
        raise ValueError(f"Unsupported format version: {format_version}")
```

### 3. Storage Migration

#### File System to Database
```python
def migrate_to_database(task_dir: str, db_url: str):
    """Migrate tasks from file system to database."""
    import sqlalchemy as sa
    from sqlalchemy.orm import sessionmaker
    
    # Create database engine
    engine = sa.create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Create tables
    Base.metadata.create_all(engine)
    
    # Migrate task boards
    for board_file in Path(task_dir).glob("*.json"):
        board_name = board_file.stem
        
        # Read tasks
        with open(board_file, "r") as f:
            tasks = json.load(f)
        
        # Create board
        board = TaskBoard(name=board_name)
        session.add(board)
        
        # Add tasks
        for task_data in tasks:
            task = Task(
                task_id=task_data["task_id"],
                description=task_data["description"],
                status=task_data["status"],
                created_at=datetime.fromisoformat(task_data["created_at"]),
                updated_at=datetime.fromisoformat(task_data["updated_at"]),
                metadata=task_data["metadata"],
                board=board
            )
            session.add(task)
    
    # Commit changes
    session.commit()
    session.close()
```

#### Database to File System
```python
def migrate_to_filesystem(db_url: str, task_dir: str):
    """Migrate tasks from database to file system."""
    import sqlalchemy as sa
    from sqlalchemy.orm import sessionmaker
    
    # Create database engine
    engine = sa.create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Get all boards
    boards = session.query(TaskBoard).all()
    
    # Migrate each board
    for board in boards:
        board_file = Path(task_dir) / f"{board.name}.json"
        
        # Get tasks
        tasks = session.query(Task).filter_by(board_id=board.id).all()
        
        # Convert to JSON
        task_data = [
            {
                "task_id": task.task_id,
                "description": task.description,
                "status": task.status,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat(),
                "metadata": task.metadata
            }
            for task in tasks
        ]
        
        # Write to file
        with open(board_file, "w") as f:
            json.dump(task_data, f, indent=2)
    
    session.close()
```

## Migration Process

### 1. Pre-Migration Steps

```python
def pre_migration_check(task_dir: str) -> bool:
    """Perform pre-migration checks."""
    # Check directory exists
    if not Path(task_dir).exists():
        print(f"Task directory not found: {task_dir}")
        return False
    
    # Check file permissions
    if not os.access(task_dir, os.W_OK):
        print(f"No write permission for directory: {task_dir}")
        return False
    
    # Check for active locks
    lock_files = list(Path(task_dir).glob("*.lock"))
    if lock_files:
        print(f"Active locks found: {[f.name for f in lock_files]}")
        return False
    
    # Check task board integrity
    for board_file in Path(task_dir).glob("*.json"):
        try:
            with open(board_file, "r") as f:
                json.load(f)
        except json.JSONDecodeError:
            print(f"Invalid JSON in board file: {board_file}")
            return False
    
    return True
```

### 2. Backup Creation

```python
def create_backup(task_dir: str) -> str:
    """Create backup of task directory."""
    backup_dir = f"{task_dir}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Create backup directory
    os.makedirs(backup_dir)
    
    # Copy files
    for file in Path(task_dir).glob("*"):
        if file.is_file():
            shutil.copy2(file, backup_dir)
    
    return backup_dir
```

### 3. Migration Execution

```python
def execute_migration(task_dir: str, migration_type: str):
    """Execute migration process."""
    # Pre-migration checks
    if not pre_migration_check(task_dir):
        raise MigrationError("Pre-migration checks failed")
    
    # Create backup
    backup_dir = create_backup(task_dir)
    print(f"Backup created at: {backup_dir}")
    
    try:
        # Execute migration
        if migration_type == "v1_to_v2":
            migrate_v1_to_v2(task_dir)
        elif migration_type == "v2_to_v3":
            migrate_v2_to_v3(task_dir)
        elif migration_type == "fs_to_db":
            migrate_to_database(task_dir, "sqlite:///tasks.db")
        elif migration_type == "db_to_fs":
            migrate_to_filesystem("sqlite:///tasks.db", task_dir)
        else:
            raise ValueError(f"Unsupported migration type: {migration_type}")
        
        print("Migration completed successfully")
        
    except Exception as e:
        # Restore from backup
        shutil.rmtree(task_dir)
        shutil.copytree(backup_dir, task_dir)
        raise MigrationError(f"Migration failed: {str(e)}")
```

### 4. Post-Migration Verification

```python
def verify_migration(task_dir: str, migration_type: str) -> bool:
    """Verify migration results."""
    if migration_type in ["v1_to_v2", "v2_to_v3"]:
        # Verify task board format
        for board_file in Path(task_dir).glob("*.json"):
            with open(board_file, "r") as f:
                tasks = json.load(f)
            
            # Check required fields
            for task in tasks:
                if migration_type == "v1_to_v2":
                    required_fields = ["task_id", "description", "status", "created_at"]
                else:  # v2_to_v3
                    required_fields = ["task_id", "description", "status", "created_at", "version"]
                
                if not all(field in task for field in required_fields):
                    print(f"Missing required fields in task: {task}")
                    return False
    
    elif migration_type == "fs_to_db":
        # Verify database
        engine = sa.create_engine("sqlite:///tasks.db")
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Check tables
        if not sa.inspect(engine).has_table("task_boards"):
            print("Missing task_boards table")
            return False
        
        if not sa.inspect(engine).has_table("tasks"):
            print("Missing tasks table")
            return False
        
        # Check data
        boards = session.query(TaskBoard).all()
        if not boards:
            print("No boards found in database")
            return False
        
        session.close()
    
    return True
```

## Rollback Procedures

### 1. Version Rollback

```python
def rollback_version(task_dir: str, backup_dir: str):
    """Rollback to previous version."""
    # Remove current version
    shutil.rmtree(task_dir)
    
    # Restore from backup
    shutil.copytree(backup_dir, task_dir)
    
    print(f"Rolled back to version from: {backup_dir}")
```

### 2. Format Rollback

```python
def rollback_format(schema_path: str, backup_path: str):
    """Rollback schema format."""
    # Remove current schema
    os.remove(schema_path)
    
    # Restore from backup
    shutil.copy2(backup_path, schema_path)
    
    print(f"Rolled back schema to version from: {backup_path}")
```

### 3. Storage Rollback

```python
def rollback_storage(task_dir: str, backup_dir: str):
    """Rollback storage migration."""
    # Remove current storage
    if Path(task_dir).exists():
        shutil.rmtree(task_dir)
    
    # Restore from backup
    shutil.copytree(backup_dir, task_dir)
    
    print(f"Rolled back storage to version from: {backup_dir}")
```

## Migration Best Practices

### 1. Planning

- Review release notes and breaking changes
- Test migration in staging environment
- Create detailed migration plan
- Schedule maintenance window
- Prepare rollback plan

### 2. Execution

- Take system backup before starting
- Follow migration steps in order
- Monitor progress and logs
- Verify each step
- Keep backup until verification

### 3. Verification

- Check data integrity
- Verify system functionality
- Test critical operations
- Monitor system performance
- Document any issues

### 4. Maintenance

- Clean up old backups
- Update documentation
- Train users on new features
- Monitor for issues
- Plan next migration

## Troubleshooting

### 1. Common Issues

- **Lock Files**: Remove stale lock files
- **Permission Errors**: Check file permissions
- **Data Corruption**: Restore from backup
- **Migration Failures**: Check logs and rollback
- **Performance Issues**: Monitor and optimize

### 2. Recovery Steps

1. Stop all operations
2. Restore from backup
3. Verify system state
4. Check error logs
5. Retry migration

### 3. Support Resources

- Migration documentation
- Release notes
- Support tickets
- Community forums
- Developer chat 