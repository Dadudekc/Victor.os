# Task System Migration Guide

## Overview

This guide provides step-by-step instructions for migrating between different versions of the Dream.OS task system. It covers version migrations, data format changes, and storage migrations.

## Pre-Migration Checklist

Before starting any migration:

1. **Backup Current State**
   - Create a backup of `runtime/task_board.json`
   - Create a backup of `runtime/working_tasks.json`
   - Create a backup of `runtime/future_tasks.json`
   - Create a backup of `runtime/task_ready_queue.json`

2. **Verify System State**
   - Ensure no tasks are currently in progress
   - Check for any pending task dependencies
   - Verify all agents are in a stable state

3. **Prepare Migration Environment**
   - Create a new `runtime/task_migration_backups/` directory
   - Ensure sufficient disk space for backups
   - Verify write permissions in runtime directory

## Version Migrations

### v1.0 to v2.0

1. **Task Board Format Update**
   ```json
   {
     "cursor_agents": {
       "agent_id": {
         "assigned_task_description": "string",
         "current_task_id": "string",
         "last_status_update_utc": "ISO8601",
         "status": "string",
         "status_details": "string",
         "tasks": {
           "task_id": {
             "description": "string",
             "status": "string",
             "last_updated": "ISO8601",
             "dependencies": ["task_id"],
             "blocker_reason": "string"
           }
         }
       }
     },
     "last_updated_utc": "ISO8601",
     "supervisor_notes": "string"
   }
   ```

2. **Working Tasks Format Update**
   ```json
   [
     {
       "task_id": "string",
       "description": "string",
       "assigned_agent": "string",
       "status": "string",
       "priority": "string",
       "depends_on": ["task_id"],
       "deliverables": ["string"],
       "collaborators": ["agent_id"],
       "collaboration_notes": "string",
       "completion_date": "ISO8601"
     }
   ]
   ```

3. **Migration Steps**
   - Convert all timestamps to ISO8601 format
   - Add missing fields with default values
   - Update status values to match new enum
   - Validate JSON schema compliance

### v2.0 to v2.1

1. **New Features**
   - Task priority levels
   - Collaboration tracking
   - Deliverable tracking
   - Completion timestamps

2. **Migration Steps**
   - Add priority field (default: "Medium")
   - Add collaborators array (default: [])
   - Add deliverables array (default: [])
   - Add completion_date field (default: null)

## Data Format Migrations

### Task Status Migration

1. **Old Status Values**
   - "assigned"
   - "in_progress"
   - "completed"
   - "failed"

2. **New Status Values**
   - "ASSIGNED"
   - "EXECUTING"
   - "COMPLETE"
   - "FAILED"
   - "BLOCKED"
   - "PAUSED_BY_DIRECTIVE"
   - "PAUSED_BY_OVERRIDE"
   - "IDLE"

3. **Migration Script**
   ```python
   def migrate_task_status(old_status):
       status_map = {
           "assigned": "ASSIGNED",
           "in_progress": "EXECUTING",
           "completed": "COMPLETE",
           "failed": "FAILED"
       }
       return status_map.get(old_status, "IDLE")
   ```

### Timestamp Format Migration

1. **Old Format**
   - Unix timestamps
   - Custom datetime strings

2. **New Format**
   - ISO8601 with timezone
   - Example: "2025-05-18T17:29:49.721154+00:00"

3. **Migration Script**
   ```python
   from datetime import datetime
   import pytz

   def migrate_timestamp(old_timestamp):
       if isinstance(old_timestamp, (int, float)):
           dt = datetime.fromtimestamp(old_timestamp)
       else:
           dt = datetime.strptime(old_timestamp, "%Y-%m-%d %H:%M:%S")
       return dt.astimezone(pytz.UTC).isoformat()
   ```

## Storage Migrations

### Task Board Migration

1. **Directory Structure**
   ```
   runtime/
   ├── task_board.json
   ├── working_tasks.json
   ├── future_tasks.json
   ├── task_ready_queue.json
   └── task_migration_backups/
       ├── task_board_v1.json
       ├── working_tasks_v1.json
       └── migration_log.txt
   ```

2. **Migration Steps**
   - Create backup directory
   - Copy current files to backup
   - Apply format updates
   - Validate new files
   - Update file permissions

### Task Queue Migration

1. **Old Queue Format**
   ```json
   {
     "queue": [
       {
         "task_id": "string",
         "priority": "integer"
       }
     ]
   }
   ```

2. **New Queue Format**
   ```json
   {
     "queue": [
       {
         "task_id": "string",
         "priority": "string",
         "assigned_agent": "string",
         "status": "string",
         "added_at": "ISO8601"
       }
     ],
     "last_updated": "ISO8601"
   }
   ```

## Rollback Procedures

### Task Board Rollback

1. **Quick Rollback**
   ```bash
   cp runtime/task_migration_backups/task_board_v1.json runtime/task_board.json
   ```

2. **Full Rollback**
   ```bash
   cp runtime/task_migration_backups/*.json runtime/
   ```

### Status Rollback

1. **Individual Task**
   ```python
   def rollback_task_status(task_id):
       with open("runtime/task_migration_backups/task_board_v1.json") as f:
           old_data = json.load(f)
       # Restore old status
       return old_data["tasks"][task_id]["status"]
   ```

2. **Bulk Rollback**
   ```python
   def rollback_all_statuses():
       with open("runtime/task_migration_backups/task_board_v1.json") as f:
           old_data = json.load(f)
       # Restore all statuses
       return old_data["tasks"]
   ```

## Post-Migration Validation

1. **Schema Validation**
   - Verify JSON schema compliance
   - Check required fields
   - Validate data types

2. **Data Integrity**
   - Verify task dependencies
   - Check agent assignments
   - Validate timestamps

3. **System Health**
   - Monitor task processing
   - Check agent status updates
   - Verify queue operations

## Troubleshooting

### Common Issues

1. **Timestamp Errors**
   - Check timezone settings
   - Verify ISO8601 format
   - Update invalid timestamps

2. **Status Mismatches**
   - Review status mapping
   - Check for invalid states
   - Update incorrect statuses

3. **Missing Fields**
   - Add default values
   - Update schema
   - Validate data

### Recovery Steps

1. **Partial Migration**
   - Identify failed steps
   - Restore from backup
   - Retry migration

2. **Complete Failure**
   - Restore all backups
   - Verify system state
   - Start migration again

## Support

For migration assistance:
1. Check `runtime/task_migration_backups/migration_log.txt`
2. Review agent devlogs for errors
3. Contact system administrator

## Version History

- v1.0: Initial task system
- v2.0: Enhanced task tracking
- v2.1: Added collaboration and deliverables 