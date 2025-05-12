# Runtime Directory Cleanup Plan

## 1. Directory Consolidation

### Temp Directories
- [ ] Consolidate all temp directories into `runtime/temp/`:
  - `temp/`
  - `temp_task_definitions/`
  - `temp_tasks/`
  - `temp_io_test/`

### Task Management
- [ ] Consolidate task-related directories:
  - `task_board/`
  - `tasks/`
  - `temp_tasks/`
  - `temp_task_definitions/`
  - Move all to `runtime/tasks/` with subdirectories:
    - `board/` - For task board related files
    - `definitions/` - For task definitions
    - `temp/` - For temporary task files

### Logging
- [ ] Consolidate all log directories into `runtime/logs/`:
  - `logs/`
  - `testlogs/`
  - `agent_logs/`
  - `operational_logs/`
  - Create subdirectories:
    - `agents/` - For agent-specific logs
    - `tests/` - For test logs
    - `operations/` - For operational logs

### Bridge
- [ ] Consolidate bridge-related directories:
  - `bridge/`
  - `bridge_outbox/`
  - `bridge_analysis/`
  - Move all to `runtime/bridge/` with subdirectories:
    - `outbox/` - For outgoing messages
    - `analysis/` - For bridge analysis
    - `inbox/` - For incoming messages

## 2. File Organization

### JSON Files
- [ ] Consolidate JSON files into appropriate directories:
  - Move task-related JSON files to `runtime/tasks/board/`
  - Move state-related JSON files to `runtime/state/`
  - Move configuration JSON files to `runtime/config/`

### Documentation
- [ ] Consolidate documentation:
  - Move all README files to `runtime/docs/`
  - Move all markdown files to appropriate documentation directories

## 3. Cleanup Actions

### Phase 1: Directory Structure
1. Create new consolidated directories
2. Move files to new locations
3. Update any references to old paths
4. Remove empty directories

### Phase 2: File Organization
1. Consolidate similar files
2. Remove duplicates
3. Update file references
4. Clean up empty files

### Phase 3: Documentation
1. Update documentation to reflect new structure
2. Create new README files for consolidated directories
3. Update any scripts that reference old paths

## 4. Safety Measures

- [ ] Create backup of current structure before making changes
- [ ] Test all functionality after each major change
- [ ] Keep track of moved files in a log
- [ ] Verify no broken references after moves

## 5. Progress Tracking

- [ ] Phase 1: Directory Structure
  - [ ] Temp directories
  - [ ] Task management
  - [ ] Logging
  - [ ] Bridge

- [ ] Phase 2: File Organization
  - [ ] JSON files
  - [ ] Documentation
  - [ ] Duplicate removal

- [ ] Phase 3: Documentation
  - [ ] README updates
  - [ ] Path reference updates
  - [ ] Script updates

## 6. Verification Steps

After each phase:
1. Run project scan to verify changes
2. Check for any broken references
3. Test core functionality
4. Update documentation

## Next Steps

1. Create backup of current structure
2. Begin with Phase 1: Directory Structure
3. Move one category at a time
4. Verify after each move
5. Update documentation as we go 