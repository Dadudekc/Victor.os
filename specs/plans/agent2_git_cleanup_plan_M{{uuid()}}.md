# Git Working Tree Cleanup Plan (Task: AGENT2-GIT-CLEANUP-PLAN-{{uuid()}})

**Agent:** agent-2
**Date:** {{iso_timestamp_utc()}}
**Related Co-Captain Message:** `MSG_COCAPTAIN_TO_AGENT2_001`
**Based on `git status --porcelain=v1` output analyzed on {{iso_timestamp_utc()}}** (during task AGENT2-GIT-INVESTIGATE-MISSING-DOCS-ARCH)

## 1. Overview
The working tree is in a messy state following the execution of `scripts/migration_helpers/robust_move_and_git_track.py` (and potentially other operations). This plan proposes steps to clean it up. The `git status` revealed numerous Renamed (R), Added (A), Deleted (D), Modified (M), and Untracked (??) files.

## 2. General Approach
1.  **Prioritize recovery of potentially lost files.**
2.  **Resolve known problematic file states** (duplicates, incorrect deletions, misplacements).
3.  **Review Renamed/Moved (R) files:** Verify these correspond to the `specs/verification/docs_path_mapping.json` and are correctly staged.
4.  **Review Added (A) files:** Stage if they are intended new locations of moved files or genuinely new tracked files. Address duplicates. Consider if some should be in `.gitignore`.
5.  **Review Deleted (D) files:** Ensure these are sources of successful moves or intentional deletions. Investigate unexpected deletions.
6.  **Review Modified (M) files:** Assess changes and stage if correct. Revert if incorrect.
7.  **Address Untracked (??) files/directories:** Decide whether to track, ignore (update `.gitignore`), or delete.
8.  Create a consolidated commit (or series of logical commits) once the working tree is clean.

## 3. Specific Issues & Proposed Actions (Derived from AGENT2-GIT-INVESTIGATE-MISSING-DOCS-ARCH)

### 3.1. Potentially Lost File: `digital_dreamscape.md`
*   **Issue:** Original `docs/architecture/digital_dreamscape.md` is marked `D` (deleted and staged for deletion by `git rm`). It was mapped to be moved to `ai_docs/architecture_design_docs/digital_dreamscape.md`, but this target does not appear as Added or Renamed in `git status`.
*   **Proposed Action:**
    1.  **CRITICAL: Attempt recovery.** Use `git log -- docs/architecture/digital_dreamscape.md` to find its last commit and content.
    2.  Restore the file content to its *intended new location*: `ai_docs/architecture_design_docs/digital_dreamscape.md`.
    3.  Execute `git add ai_docs/architecture_design_docs/digital_dreamscape.md`.
    4.  The existing staged deletion `D docs/architecture/digital_dreamscape.md` should remain, as the old path is correctly removed.

### 3.2. Duplicated/Unremoved Original: `social_media_manager.md`
*   **Issue:**
    *   Original `docs/architecture/social_media_manager.md` is still in the working tree (directory `docs/architecture/` is untracked `??`).
    *   New `A ai_docs/architecture_design_docs/social_media_manager.md` exists (Added, staged).
    *   New `A ai_docs/architecture_design_docs/from_old_docs/architecture/social_media_manager.md` also exists (Added, staged).
*   **Proposed Action:**
    1.  Verify content of the two added files. Assume `ai_docs/architecture_design_docs/social_media_manager.md` is the canonical one based on its direct mapping.
    2.  Remove the duplicate: `git rm --cached ai_docs/architecture_design_docs/from_old_docs/architecture/social_media_manager.md` (to unstage) and then delete the actual file from the filesystem.
    3.  Manually delete the original, now untracked file: `docs/architecture/social_media_manager.md` from the working tree.
    4.  Ensure the canonical `ai_docs/architecture_design_docs/social_media_manager.md` remains staged.

### 3.3. Misplaced Moved File: `agent_capability_registry.md`
*   **Issue:** Mapped from `docs/architecture/agent_capability_registry.md` to `ai_docs/architecture_design_docs/agent_capability_registry.md`. Git status shows it as `R` (renamed/moved) to `ai_docs/architecture_design_docs/from_old_docs/architecture/agent_capability_registry.md`.
*   **Proposed Action:**
    1.  If the intended location is directly under `ai_docs/architecture_design_docs/`, then execute:
        `git mv ai_docs/architecture_design_docs/from_old_docs/architecture/agent_capability_registry.md ai_docs/architecture_design_docs/agent_capability_registry.md`

## 4. Categorical Actions (Based on Full `git status --porcelain=v1` Output)

### 4.1. Renamed (R) Files
*   **Observation:** Numerous files show as Renamed, primarily from `docs/` subdirectories to `ai_docs/` subdirectories, and from `_archive/` to `archive/`.
*   **Proposed Action:** For each `R old_path -> new_path` entry:
    *   Cross-reference with `specs/verification/docs_path_mapping.json` (for `docs/` moves) or other relevant reorganization plans.
    *   If the rename reflects the intended move and the target is correct, these are correctly staged. No action needed beyond verification.
    *   Investigate and correct any discrepancies (e.g., using `git mv` if a rename was incomplete or incorrect, or to adjust paths like with `agent_capability_registry.md`).

### 4.2. Added (A) Files
*   **Observation:** Many files marked `A`, mostly within `ai_docs/` structure.
*   **Proposed Action:** For each `A new_path` entry:
    *   Verify if it's the correct target of an intended move. If so, it's correctly staged.
    *   Identify and handle duplicates (as with `social_media_manager.md`).
    *   For any other unexpected Added files, determine if they should be committed, deleted, or added to `.gitignore`.

### 4.3. Deleted (D) Files
*   **Observation:** Numerous files marked `D`, from `docs/` subdirectories, `_archive/`, `runtime/agent_comms/agent_mailboxes/.../inbox/`, and various `proposals/`.
*   **Proposed Action:** For each `D old_path` entry:
    *   If it's the source of a verified Renamed (`R`) file, this is correct.
    *   If not part of a rename (like `digital_dreamscape.md`), confirm if the deletion was intentional or if recovery is needed.
    *   Deletions within `runtime/agent_comms/agent_mailboxes/.../inbox/` are likely processed messages and probably correct.
    *   Deletions from `proposals/` (e.g., `master_proposal_list.md`) need verification if these are still relevant or superseded.

### 4.4. Modified (M) Files
*   **Observation:** Several important files are Modified: `.gitignore`, `future_tasks.json`, `pyproject.toml`, `working_tasks.json`, `runtime/config/config.yaml`, various devlogs, and multiple source files in `src/dreamos/` and `src/dreamscape/`.
*   **Proposed Action:** For each modified file:
    *   Use `git diff <file>` to review changes.
    *   `git add <file>` to stage changes if they are correct and intentional (e.g., updates to task files by agents, config changes reflecting reorganization).
    *   `git checkout -- <file>` to revert unintentional or incorrect changes.
    *   Pay special attention to `.gitignore`: ensure it correctly handles new paths and artifact directories resulting from reorganization.

### 4.5. Untracked (??) Files and Directories
*   **Observation:** A large number of directories and some files are untracked. Examples: `ai_docs/api_docs/`, `archive/from_underscore_archive/`, `devtools/`, `sandbox/`, `src/dreamos/bridge/`, `templates/`, many specific `.md` or `.json` files within otherwise tracked structures.
*   **Proposed Action:** For each untracked path:
    *   **Track:** If it's a new, intentional part of the project, `git add <path>`.
    *   **Ignore:** If it's a generated artifact, cache, local config, etc., add an appropriate pattern to `.gitignore`. Verify the path is then no longer listed as untracked.
    *   **Delete:** If it's junk or unwanted, remove from the filesystem.
    *   Directories like `docs/architecture/` became untracked because all previously tracked content was removed. Once its contents (like the original `social_media_manager.md`) are handled, the empty directory might be removed by git or can be cleaned if desired.

## 5. General Recommendations for Execution
*   **Backup:** Before starting, ensure no unrecoverable local changes exist, or consider `git stash save "pre-cleanup-state"`.
*   **Incremental Commits:** Address issues in logical chunks (e.g., fix `digital_dreamscape.md` and commit, fix `social_media_manager.md` and commit, process all renames and commit, etc.) rather than one massive commit. This makes review easier and rollback safer.
*   **Verify Script Logic:** For future moves, the `robust_move_and_git_track.py` script should be reviewed to better handle file vs. directory mappings and prevent duplicate copies or ensure `git rm` operations are robustly confirmed.

## 6. Request for Review
Please review this cleanup plan. Upon approval, Agent-2 can begin executing these steps. 