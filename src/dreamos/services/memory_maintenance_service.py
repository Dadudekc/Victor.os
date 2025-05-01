# src/dreamos/services/memory_maintenance_service.py
import asyncio
import fnmatch
import functools
import json
import logging
import os
import shutil
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Literal, Optional

from apscheduler.jobstores.memory import MemoryJobStore

# EDIT START: Add APScheduler import
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from dreamos.core.config import (  # Updated import
    AppConfig,
    CompactionPolicyConfig,
    MemoryMaintenanceConfig,
    SummarizationPolicyConfig,
)
from dreamos.core.coordination.agent_bus import AgentBus  # Assuming AgentBus is needed
from dreamos.core.utils.file_locking import (  # For locking memory segments
    FileLock,
    LockAcquisitionError,
)
from dreamos.core.utils.summarizer import (
    BaseSummarizer,  # Import BaseSummarizer for type hint
)
from dreamos.memory.compaction_utils import CompactionError, compact_segment_file
from dreamos.memory.summarization_utils import (
    SummarizationError,
    summarize_segment_file,
)

# EDIT END


# Placeholder for policies - these would define compaction/summarization rules
# CompactionPolicy = dict
# SummarizationPolicy = dict

logger = logging.getLogger(__name__)

class MemoryMaintenanceService:
    """
    Manages background memory maintenance tasks like compaction and summarization.
    Uses APScheduler for scheduling.
    """
    def __init__(
        self,
        # Remove direct path/interval args, get them from config
        # memory_base_path: Path,
        # snapshot_base_path: Path,
        # scan_interval_seconds: int = 300,
        config: AppConfig, # Accept the main AppConfig
        summarizer: Optional[BaseSummarizer] = None # Pass in the summarizer instance
    ):
        """
        Initializes the Memory Maintenance Service using application configuration.

        Args:
            config: The loaded application configuration (AppConfig).
            summarizer: An optional summarizer instance for the summarization task.
        """
        self.config = config
        self.maintenance_config: MemoryMaintenanceConfig = config.memory_maintenance
        self.summarizer = summarizer

        # Get paths and intervals from config
        self.memory_base_path = config.paths.memory
        self.snapshot_base_path = config.paths.temp / "memory_snapshots"
        self.scan_interval_seconds = self.maintenance_config.scan_interval_seconds
        self.lock_timeout_seconds = self.maintenance_config.lock_timeout_seconds

        # EDIT START: Remove storing single global policy
        # self.compaction_policy = self.maintenance_config.compaction_policy
        # self.summarization_policy = self.maintenance_config.summarization_policy
        # Policies will be determined per-agent/segment later
        # EDIT END

        self.scheduler = AsyncIOScheduler()
        self._job_id = "memory_maintenance_job"
        self._running = False

        self.snapshot_base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Memory Maintenance Service initialized...") # Simplified log
        # EDIT START: Log default policies from config
        # logger.info(f"Default Compaction Policy: {self.maintenance_config.default_compaction_policy.dict()}")
        # logger.info(f"Default Summarization Policy: {self.maintenance_config.default_summarization_policy.dict()}")
        # NOTE: Assuming config structure change {default_compaction_policy, default_summarization_policy}
        logger.info(f"Default Compaction Policy: {getattr(self.maintenance_config, 'default_compaction_policy', self.maintenance_config.compaction_policy).dict()}")
        logger.info(f"Default Summarization Policy: {getattr(self.maintenance_config, 'default_summarization_policy', self.maintenance_config.summarization_policy).dict()}")
        # EDIT END
        if not self.summarizer:
            logger.warning("No summarizer provided; summarization tasks will be skipped.")

    async def start(self):
        """Adds the maintenance job and starts the scheduler."""
        if self.scheduler.running:
            logger.warning("Maintenance scheduler already running.")
            return

        logger.info("Starting Memory Maintenance Service scheduler...")
        try:
            # Add the job
            self.scheduler.add_job(
                self._perform_maintenance,
                'interval',
                seconds=self.maintenance_config.scan_interval_seconds,
                id=self._job_id,
                replace_existing=True,
                misfire_grace_time=self.maintenance_config.misfire_grace_time
            )
            logger.info(f"Scheduled maintenance job '{self._job_id}' with interval {self.maintenance_config.scan_interval_seconds}s.")

            # Start the scheduler
            self.scheduler.start()
            self._running = True
            logger.info("Memory Maintenance Service scheduler started.")
        except ImportError as e: # Example: If APScheduler not installed
            logger.critical(f"Failed to start Memory Maintenance: APScheduler not installed or import failed: {e}")
            self._running = False
            raise # Re-raise critical dependency error
        except Exception as e: # Catch other potential scheduler errors
            logger.exception(f"Failed to start Memory Maintenance Service scheduler: {e}")
            self._running = False
            raise
        # Removed old task creation logic:
        # self._running = True
        # self._task = asyncio.create_task(self._run())
        # logger.info("Memory Maintenance Service started.")

    async def stop(self):
        """Stops the maintenance service scheduler."""
        if not self.scheduler.running:
            logger.warning("Maintenance scheduler not running.")
            return

        logger.info("Stopping Memory Maintenance Service scheduler...")
        try:
            # Pass wait=False to avoid blocking if called from within event loop
            # Error handling within shutdown might be needed depending on APScheduler version
            self.scheduler.shutdown(wait=False)
            self._running = False
            logger.info("Memory Maintenance Service scheduler stopped.")
        except Exception as e:
             logger.exception(f"Error stopping maintenance scheduler: {e}")
        # Removed old task cancellation logic:
        # if not self._running or not self._task:
        #     logger.warning("Maintenance service not running.")
        #     return
        # self._running = False
        # self._task.cancel()
        # try:
        #     await self._task
        # except asyncio.CancelledError:
        #     logger.info("Maintenance task cancelled.")
        # except Exception as e:
        #     logger.exception(f"Error during maintenance service shutdown: {e}")
        # finally:
        #     self._task = None
        #     logger.info("Memory Maintenance Service stopped.")

    async def _perform_maintenance(self):
        """Scans memory directories and triggers processing for each. (Applies agent filtering)"""
        logger.info(f"Running memory maintenance cycle for {self.memory_base_path}...")
        try:
            if not self.memory_base_path.is_dir():
                logger.error(f"Memory base path {self.memory_base_path} does not exist or is not a directory.")
                return

            # EDIT START: Implement Agent Filtering based on proposed config
            # process_agents = self.maintenance_config.process_agents
            # skip_agents = self.maintenance_config.skip_agents
            # NOTE: Using getattr to handle case where config edit failed
            process_agents = getattr(self.maintenance_config, 'process_agents', None)
            skip_agents = getattr(self.maintenance_config, 'skip_agents', None)
            # EDIT END

            agent_tasks = []
            # Add try/except around directory iteration in case of permission errors
            try:
                 agent_dirs = list(self.memory_base_path.iterdir())
            except OSError as e:
                 logger.error(f"Failed to list agent directories in {self.memory_base_path}: {e}", exc_info=True)
                 return # Cannot proceed if we can't list dirs

            for agent_dir in agent_dirs:
                if agent_dir.is_dir():
                    agent_id = agent_dir.name
                    # EDIT START: Apply Filtering
                    if process_agents is not None and agent_id not in process_agents:
                        logger.debug(f"Skipping agent {agent_id} (not in process_agents list).")
                        continue
                    if skip_agents is not None and agent_id in skip_agents:
                        logger.debug(f"Skipping agent {agent_id} (in skip_agents list).")
                        continue
                    # EDIT END

                    logger.debug(f"Scheduling memory processing for agent: {agent_id}")
                    agent_tasks.append(asyncio.create_task(self._process_agent_memory(agent_dir)))

            if agent_tasks:
                # Gather results, log errors within the gather call
                results = await asyncio.gather(*agent_tasks, return_exceptions=True)
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        # Log error from the specific _process_agent_memory task
                        agent_id_failed = agent_tasks[i].get_coro().__self__.agent_id # Attempt to get agent ID if possible
                        logger.error(f"Error processing memory for agent '{agent_id_failed}': {result}", exc_info=result)
                logger.info("Finished processing agent memory directories for this cycle.")
            else:
                 logger.info("No agent memory directories found/selected to process in this cycle.")
        except Exception as e:
            # Catch any unexpected error during the maintenance cycle itself
            logger.critical(f"Unexpected critical error during memory maintenance cycle: {e}", exc_info=True)

    def _get_policy_for_file(
        self,
        file_path: Path,
        agent_id: str,
        policy_type: Literal["compaction", "summarization"]
    ) -> Optional[BasePolicyConfig]:
        """Finds the most specific policy matching the file and agent.

        Checks agent overrides first, then defaults.
        Matches based on file_pattern using fnmatch.
        Returns the specific CompactionPolicyConfig or SummarizationPolicyConfig, or None.
        """
        policies_to_check: List[BasePolicyConfig] = []
        override_config = self.maintenance_config.agent_policy_overrides.get(agent_id)

        # 1. Get candidate policies (agent overrides + defaults)
        if policy_type == "compaction":
            if override_config and override_config.compaction_policies:
                policies_to_check.extend(override_config.compaction_policies)
            policies_to_check.extend(self.maintenance_config.default_compaction_policies)
        elif policy_type == "summarization":
            if override_config and override_config.summarization_policies:
                policies_to_check.extend(override_config.summarization_policies)
            policies_to_check.extend(self.maintenance_config.default_summarization_policies)

        # 2. Find the best match based on file_pattern
        best_match: Optional[BasePolicyConfig] = None
        best_match_specificity = -1 # Track how specific the pattern is

        relative_path_str = str(file_path.relative_to(self.snapshot_base_path / agent_id)) # Path relative to agent snapshot root

        for policy in policies_to_check:
            if not policy.enabled:
                continue # Skip disabled policies

            pattern = policy.file_pattern
            if pattern is None:
                # Policy with no pattern is considered least specific default
                specificity = 0
                if fnmatch.fnmatch(relative_path_str, "*"): # Matches any file if no pattern
                    if specificity > best_match_specificity:
                        best_match = policy
                        best_match_specificity = specificity
            elif fnmatch.fnmatch(relative_path_str, pattern):
                # Calculate specificity (e.g., count path separators and non-wildcard chars)
                # Simple specificity: length of the pattern string
                specificity = len(pattern)
                if specificity > best_match_specificity:
                    best_match = policy
                    best_match_specificity = specificity

        if best_match:
            logger.debug(f"Selected {policy_type} policy for '{relative_path_str}': pattern='{best_match.file_pattern}', enabled={best_match.enabled}")
        # else: logger.debug(f"No matching {policy_type} policy found for '{relative_path_str}'") # Too noisy

        return best_match

    async def _process_agent_memory(self, agent_memory_path: Path):
        """Processes a single agent's memory directory (snapshot, compaction, summarization)."""
        agent_id = agent_memory_path.name
        snapshot_dir = self.snapshot_base_path / agent_id
        # Define agent-specific lock path within the base memory directory's parent
        agent_lock_file = agent_memory_path.with_suffix(".lock")
        backup_dir = agent_memory_path.with_suffix(".bak")
        replacement_successful = False

        # --- Snapshotting ---
        try:
            if snapshot_dir.exists():
                logger.warning(f"Previous snapshot dir {snapshot_dir} exists, removing.")
                shutil.rmtree(snapshot_dir) # Clean up potentially stale snapshot

            logger.info(f"Creating snapshot of {agent_memory_path} at {snapshot_dir}")
            # Copy directory contents recursively
            shutil.copytree(agent_memory_path, snapshot_dir, symlinks=False, ignore_dangling_symlinks=True)
            logger.info(f"Snapshot created successfully for {agent_id}.")

        except (shutil.Error, OSError, PermissionError) as e:
            logger.exception(f"Failed to create/cleanup snapshot for {agent_id} from {agent_memory_path} to {snapshot_dir}: {e}")
            # Ensure cleanup attempt even on creation failure
            if snapshot_dir.exists():
                try: shutil.rmtree(snapshot_dir)
                except Exception as rm_e: logger.error(f"Secondary error cleaning up failed snapshot {snapshot_dir}: {rm_e}")
            return # Cannot proceed without a snapshot
        except Exception as e:
            logger.exception(f"Unexpected error during snapshot creation for {agent_id}: {e}")
            if snapshot_dir.exists():
                 try: shutil.rmtree(snapshot_dir)
                 except Exception as rm_e: logger.error(f"Secondary error cleaning up failed snapshot {snapshot_dir}: {rm_e}")
            return # Stop processing this agent if snapshot failed

        # --- 3. Process Files in Snapshot ---
        logger.info(f"Processing snapshot for agent {agent_id} at {snapshot_dir}")
        processed_count = 0
        skipped_count = 0
        error_count = 0
        try:
            # Use rglob to recursively find all files
            for segment_file in snapshot_dir.rglob('*'):
                if segment_file.is_file():
                    # EDIT START: Determine policies and skip if no match
                    compaction_policy = self._get_policy_for_file(segment_file, agent_id, "compaction")
                    summarization_policy = self._get_policy_for_file(segment_file, agent_id, "summarization")

                    if not compaction_policy and not summarization_policy:
                        # logger.debug(f"Skipping file {segment_file.name}: No matching policies found.") # Too noisy
                        skipped_count += 1
                        continue # Skip file if no applicable policy found

                    # Ensure policies are the correct type for the helper function
                    comp_policy_config: Optional[CompactionPolicyConfig] = compaction_policy if isinstance(compaction_policy, CompactionPolicyConfig) else None
                    summ_policy_config: Optional[SummarizationPolicyConfig] = summarization_policy if isinstance(summarization_policy, SummarizationPolicyConfig) else None

                    # Only proceed if at least one applicable policy exists and is enabled
                    if (comp_policy_config and comp_policy_config.enabled) or \
                       (summ_policy_config and summ_policy_config.enabled and self.summarizer): # Also check if summarizer exists

                        logger.debug(f"Processing segment: {segment_file.relative_to(snapshot_dir)}")
                        # Pass potentially None policies; _process_segment_file handles None
                        success = await self._process_segment_file(
                            segment_file,
                            compaction_policy=comp_policy_config,
                            summarization_policy=summ_policy_config
                        )
                        if success:
                            processed_count += 1
                        else:
                            error_count += 1
                    else:
                        # logger.debug(f"Skipping file {segment_file.name}: Applicable policies are disabled or summarizer missing.") # Too noisy
                        skipped_count += 1
                    # EDIT END
        except Exception as e:
            logger.exception(f"Error during snapshot file iteration for agent {agent_id}: {e}")
            error_count += 1 # Count this as an error

        logger.info(f"Agent {agent_id}: Processed={processed_count}, Skipped={skipped_count}, Errors={error_count}")
        if error_count > 0:
             logger.warning(f"Agent {agent_id}: Encountered {error_count} errors during file processing. Replacement might be incomplete.")
             # Decide whether to proceed with replacement if errors occurred?
             # For now, proceed cautiously.

        # --- 4. Atomic Replacement ---
        if error_count == 0 and processed_count > 0: # Only replace if processing happened without errors
            logger.info(f"Attempting atomic replacement for agent {agent_id}")
            agent_lock = FileLock(str(agent_lock_file), timeout=self.lock_timeout_seconds)
            try:
                logger.debug(f"Acquiring agent lock: {agent_lock_file}")
                with agent_lock:
                    logger.info(f"Agent lock acquired for {agent_id}. Performing replacement.")

                    # 1. Backup Original Directory
                    if agent_memory_path.exists():
                        logger.debug(f"Renaming original {agent_memory_path} to {backup_dir}")
                        # Use os.replace for better atomicity if possible on the OS
                        os.replace(agent_memory_path, backup_dir)
                    else:
                        logger.warning(f"Original agent memory path {agent_memory_path} not found during replacement. Proceeding with snapshot rename.")
                        backup_dir = None # Indicate no backup exists

                    # 2. Rename Snapshot to Original
                    logger.debug(f"Renaming snapshot {snapshot_dir} to {agent_memory_path}")
                    os.replace(snapshot_dir, agent_memory_path)

                    replacement_successful = True
                    logger.info(f"Atomic replacement successful for agent {agent_id}.")
                    # Lock released automatically by 'with' statement
                    logger.debug(f"Agent lock released for {agent_id}.")

            except LockAcquisitionError as lae:
                logger.error(f"Failed to acquire agent lock {agent_lock_file} for replacement: {lae}")
            except OSError as ose:
                logger.error(f"OS error during atomic replacement for {agent_id}: {ose}", exc_info=True)
                # Attempt rollback if backup exists
                if backup_dir and backup_dir.exists() and not agent_memory_path.exists():
                    logger.warning(f"Attempting rollback: renaming {backup_dir} back to {agent_memory_path}")
                    try:
                        os.replace(backup_dir, agent_memory_path)
                        logger.info(f"Rollback successful for {agent_id}.")
                    except OSError as rbe:
                        logger.critical(f"CRITICAL: Rollback FAILED for {agent_id}! Manual intervention needed. Error: {rbe}")
                elif not backup_dir:
                     logger.error("Replacement failed, and no backup existed. Original may be lost if it existed.")
                else:
                     logger.error("Replacement failed, could not automatically rollback.")
            except Exception as e:
                logger.critical(f"Unexpected critical error during atomic replacement for {agent_id}: {e}", exc_info=True)
                # Add similar rollback logic here if appropriate?

        # --- Cleanup (associated with the replacement attempt) ---
        finally:
             # Always clean up snapshot if it wasn't successfully moved
             if snapshot_dir.exists():
                 logger.info(f"Cleaning up snapshot directory: {snapshot_dir}")
                 try:
                     shutil.rmtree(snapshot_dir)
                 except OSError as e:
                     logger.error(f"Error removing snapshot directory {snapshot_dir}: {e}")
             # Clean up backup only if replacement was successful
             if replacement_successful and backup_dir and backup_dir.exists():
                  logger.info(f"Cleaning up backup directory: {backup_dir}")
                  try:
                      shutil.rmtree(backup_dir)
                  except OSError as e:
                      logger.error(f"Error removing backup directory {backup_dir}: {e}")
             elif not replacement_successful and backup_dir and backup_dir.exists():
                  logger.warning(f"Replacement failed or was skipped. Backup directory retained: {backup_dir}")

        # --- Handle cases where replacement wasn't attempted ---
        elif error_count > 0:
            logger.warning(f"Skipping replacement for agent {agent_id} due to {error_count} processing errors.")
            # Clean up snapshot if it exists even if replacement wasn't attempted due to errors
            if snapshot_dir.exists():
                 logger.info(f"Cleaning up unused snapshot directory (due to processing errors): {snapshot_dir}")
                 try:
                     shutil.rmtree(snapshot_dir)
                 except OSError as e:
                     logger.error(f"Error removing snapshot directory {snapshot_dir} after processing errors: {e}")

        else: # processed_count == 0 or snapshot_dir didn't exist initially or had no segments
            logger.info(f"Skipping replacement for agent {agent_id} as no files needed processing or snapshot was empty/missing.")
            # Clean up the snapshot directory if it exists but wasn't used for replacement
            if snapshot_dir.exists():
                logger.info(f"Cleaning up unused snapshot directory (no files processed/needed): {snapshot_dir}")
                try:
                    shutil.rmtree(snapshot_dir)
                except OSError as e:
                     logger.error(f"Error removing unused snapshot directory {snapshot_dir}: {e}")

    async def _process_segment_file(self, segment_file_path: Path,
                                    compaction_policy: Optional[CompactionPolicyConfig],
                                    summarization_policy: Optional[SummarizationPolicyConfig]) -> bool:
        """Applies compaction and summarization to a single segment file using specific policies."""
        logger.debug(f"Processing segment file in snapshot: {segment_file_path}")
        success = True # Assume success initially

        # --- Compaction ---
        if compaction_policy and compaction_policy.enabled:
            logger.debug(f"Applying compaction to {segment_file_path.name} using policy: {compaction_policy.dict()}")
            try:
                # Assuming compact_segment_file handles policy dict correctly
                # And returns boolean success or raises specific exceptions
                compact_result = compact_segment_file(
                    segment_file_path,
                    compaction_policy.dict(),
                    compress_after=compaction_policy.compress_after_processing
                )
                if not compact_result:
                    logger.warning(f"Compaction failed for {segment_file_path.name} (returned False)")
                    success = False
            except CompactionError as ce:
                logger.error(f"CompactionError for {segment_file_path.name}: {ce}", exc_info=True)
                success = False
            except Exception as e:
                logger.error(f"Unexpected error during compaction for {segment_file_path.name}: {e}", exc_info=True)
                success = False
        elif compaction_policy: # Policy exists but is disabled
             logger.debug(f"Compaction policy disabled for {segment_file_path.name}")
        # Else: No compaction policy found

        # --- Summarization ---
        if summarization_policy and summarization_policy.enabled and self.summarizer:
            logger.debug(f"Applying summarization to {segment_file_path.name} using policy: {summarization_policy.dict()}")
            try:
                # Assuming summarize_segment_file handles policy dict correctly
                # And returns boolean success or raises specific exceptions
                summarize_result = summarize_segment_file(
                    segment_file_path,
                    self.summarizer,
                    summarization_policy.dict(),
                    compress_after=summarization_policy.compress_after_processing
                )
                if not summarize_result:
                     logger.warning(f"Summarization failed for {segment_file_path.name} (returned False)")
                     success = False
            except SummarizationError as se:
                logger.error(f"SummarizationError for {segment_file_path.name}: {se}", exc_info=True)
                success = False
            except Exception as e:
                logger.error(f"Unexpected error during summarization for {segment_file_path.name}: {e}", exc_info=True)
                success = False
        elif summarization_policy and summarization_policy.enabled and not self.summarizer:
             logger.warning(f"Summarization policy enabled for {segment_file_path.name}, but no summarizer instance provided.")
        elif summarization_policy: # Policy exists but is disabled
             logger.debug(f"Summarization policy disabled for {segment_file_path.name}")
        # Else: No summarization policy found or no summarizer

        # Return overall success for this segment
        if not success:
            logger.warning(f"Segment processing FAILED for: {segment_file_path}")
        # else:
            # logger.debug(f"Segment processing finished for: {segment_file_path}") # A bit noisy
        return success


# Example usage (for testing purposes)
async def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Create dummy memory structure
    base_dir = Path("./temp_memory_test")
    agent1_mem = base_dir / "agent_001" / "memory"
    agent2_mem = base_dir / "agent_002" / "memory"
    snapshot_dir = base_dir / "snapshots"

    if base_dir.exists():
        shutil.rmtree(base_dir) # Clean start

    agent1_mem.mkdir(parents=True, exist_ok=True)
    agent2_mem.mkdir(parents=True, exist_ok=True)
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    # Create dummy segment files
    with open(agent1_mem / "segment_1.json", "w") as f:
        f.write('{"entries": [1, 2, 3]}') # Dummy content
    with open(agent1_mem / "segment_2.json", "w") as f:
        f.write('{"entries": [4, 5, 6]}')
    with open(agent2_mem / "segment_A.json", "w") as f:
        f.write('{"entries": ["a", "b", "c"]}')

    config = AppConfig.load()
    configure_logging(config, verbose=True) # Assuming configure_logging function
    # summarizer = SomeSummarizerImplementation() # Instantiate a summarizer
    service = MemoryMaintenanceService(config=config, summarizer=None) # Pass config
    await service.start()

    # Let it run for a couple of cycles
    await asyncio.sleep(12)

    await service.stop()

    # Clean up
    # shutil.rmtree(base_dir)
    logger.info("Test finished. Check logs and temp_memory_test directory.")


if __name__ == "__main__":
    # Note: Running compaction/summarization utils might require actual implementations
    # and potentially external resources (like an LLM for summarization).
    # This example mainly tests the service structure, snapshotting, and locking flow.
    asyncio.run(main())
