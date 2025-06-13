# Deduplication Task List

This list outlines the main areas of the codebase where duplicate or near-duplicate files/directories were detected by `deduplication_scanner.py` (scan date: 2025-06-13). Use it as a high-level guide for manual cleanup.

## Exact duplicate files

- 4 empty `__init__.py` files share the same hash (`d41d8cd98f00b204e9800998ecf8427e`):
  - `tests/__init__.py`
  - `tests/integration/__init__.py`
  - `src/bridge/__init__.py`
  - `src/bridge/modules/__init__.py`
  - *Action*: keep them since they ensure packages are recognized. No action required unless restructuring removes these packages.

## Directories with many near-duplicate filenames

Below are the top directories ranked by the number of near-duplicate filename matches found. Investigate these directories for redundant or outdated files.

| Count | Directory |
|-------|-----------|
|    20 | /workspace/Victor.os/docs/vision |
|    14 | /workspace/Victor.os/src/dreamos/tools |
|    12 | /workspace/Victor.os/runtime/operational_logs/lore |
|    11 | /workspace/Victor.os |
|    11 | /workspace/Victor.os/sandbox/bridge |
|    10 | /workspace/Victor.os/prompts/agents |
|     8 | /workspace/Victor.os/docs/agents/protocols |
|     7 | /workspace/Victor.os/runtime/agent_comms/governance/onboarding |
|     7 | /workspace/Victor.os/runtime/agent_comms/governance/election_cycle/candidates |
|     7 | /workspace/Victor.os/src/dreamos/testing/module_validation |
|     7 | /workspace/Victor.os/src/dreamos/core |
|     7 | /workspace/Victor.os/episodes |
|     6 | /workspace/Victor.os/src/dreamos/tools/scanner |
|     6 | /workspace/Victor.os/tests |
|     5 | /workspace/Victor.os/docs/onboarding |
|     5 | /workspace/Victor.os/src/dreamos/bridge |
|     5 | /workspace/Victor.os/basicbot |
|     5 | /workspace/Victor.os/src/dreamos/core/agents/scraper |
|     5 | /workspace/Victor.os/src/dreamos/tools/agent_bootstrap_runner |
|     5 | /workspace/Victor.os/src/dreamos/agents/agent3 |

## Recommended next steps

1. Prioritize cleanup in directories with the highest counts (top of the table).
2. For each directory:
   - Review files with similar names or timestamps to consolidate redundant versions.
   - Remove obsolete or temporary files that are no longer referenced.
   - Consolidate documentation or logs where possible.
3. After manual cleanup, re-run `python deduplication_scanner.py` to verify that duplicates were removed.

## Progress (2025-06-13)

- Removed redundant lore logs under `runtime/operational_logs/lore` ([9f2607f](https://github.com/Dadudekc/Victor.os/commit/9f2607f)).
- Regenerated deduplication reports with `deduplication_scanner.py` which produced `runtime/reports/duplicate_report.json` and `duplicate_summary.txt`.
- Next focus areas:
  - `docs/vision`
  - `src/dreamos/tools`
