# Task and Episode File Organization

This document describes the standard organization of task list JSONs and episode YAML files in the Dream.os project.

## Episode YAML Files

All episode YAML files are stored in the `episodes/` directory:

- `episodes/episode-XX.yaml` - Individual episode definitions
- `episodes/EPISODE_INDEX.yaml` - Main index of all episodes
- Archived episodes should be moved to `archive/episodes/`

## Task JSON Files

Task list JSONs follow this organizational structure:

- **Primary Task Lists**
  - `runtime/tasks/future_tasks.json` - Tasks planned for future work
  - `runtime/tasks/working_tasks.json` - Tasks currently being worked on
  - `runtime/tasks/completed_tasks.json` - Tasks that have been completed

- **Agent-Specific Task Lists**
  - `runtime/tasks/working/working_tasks_agent-X_claimed.json` - Tasks claimed by specific agents

- **Episode-Related Task Lists**
  - `runtime/tasks/episodes/parsed_episode_tasks.json` - Tasks parsed from episodes
  - `runtime/tasks/episodes/parsed_episode_X_tasks.json` - Tasks parsed from specific episodes

- **Other Task Files**
  - `runtime/tasks/sample_tasks.json` - Sample task definitions for reference
  - `runtime/tasks/archives/` - Archived task lists

## Implementation Notes

This organization was implemented per the reorganization plan in `reorganization_plan.md`. The following files were moved:

- `dummy_episode.yaml` → `episodes/dummy_episode.yaml`
- `episode_5.yaml` → `episodes/episode_5.yaml`
- `future_tasks.json` → `runtime/tasks/future_tasks.json`
- `working_tasks.json` → `runtime/tasks/working_tasks.json`
- `working_tasks_agent-5_claimed.json` → `runtime/tasks/working/working_tasks_agent-5_claimed.json`
- `sample_tasks.json` → `runtime/tasks/sample_tasks.json`
- `episodes/parsed_episode_tasks.json` → `runtime/tasks/episodes/parsed_episode_tasks.json`
- `episodes/parsed_episode_5_tasks.json` → `runtime/tasks/episodes/parsed_episode_5_tasks.json`

**Note**: These files are currently duplicated in both places for backward compatibility. Future development should use the new paths exclusively. 