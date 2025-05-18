# Project Reorganization Plan

## Episode YAML Files
- All episode YAML files should be consolidated in `episodes/` directory
- Older versions should be archived in `archive/episodes/`
- The main episode index should remain at `episodes/EPISODE_INDEX.yaml`

## Task JSON Files
- All task list JSONs should be consolidated in `runtime/tasks/`
- Root task files (`working_tasks.json`, `future_tasks.json`, etc.) should be moved to `runtime/tasks/`
- Episode-specific task JSONs should be moved to `runtime/tasks/episodes/`
- Completed tasks should be in `runtime/tasks/completed/completed_tasks.json`
- Task archives should be stored in `runtime/tasks/archives/`

## Implementation Steps

1. Create any missing directories
2. Move all straggler episode YAML files to `episodes/`
3. Move all straggler task JSON files to appropriate directories in `runtime/tasks/`
4. Update any references to these files in code or documentation

## Files to Move

### Episode YAML Files
- Root: `dummy_episode.yaml` → `episodes/dummy_episode.yaml`
- Root: `episode_5.yaml` → `episodes/episode_5.yaml`

### Task JSON Files
- Root: `future_tasks.json` → `runtime/tasks/future_tasks.json`
- Root: `working_tasks.json` → `runtime/tasks/working_tasks.json`
- Root: `working_tasks_agent-5_claimed.json` → `runtime/tasks/working/working_tasks_agent-5_claimed.json`
- Root: `sample_tasks.json` → `runtime/tasks/sample_tasks.json`
- Episodes: `episodes/parsed_episode_tasks.json` → `runtime/tasks/episodes/parsed_episode_tasks.json`
- Episodes: `episodes/parsed_episode_5_tasks.json` → `runtime/tasks/episodes/parsed_episode_5_tasks.json` 