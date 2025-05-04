# src/dreamos/services/memory_maintenance_service.py
import asyncio
import fnmatch
import logging
import os
import shutil
from pathlib import Path
from typing import (  # Assuming Union is needed for BasePolicyConfig resolution below
    List,
    Literal,
    Optional,
    Union,
)

from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Assuming config types are needed
from dreamos.core.config import (  # Placeholder for BasePolicyConfig if it exists in config, otherwise remove/replace; BasePolicyConfig  # noqa: E501
    AppConfig,
    CompactionPolicyConfig,
    MemoryMaintenanceConfig,
    SummarizationPolicyConfig,
)
from dreamos.core.utils.file_locking import FileLock, LockAcquisitionError
from dreamos.core.utils.summarizer import BaseSummarizer
from dreamos.memory.compaction_utils import CompactionError, compact_segment_file
from dreamos.memory.summarization_utils import (
    SummarizationError,
    summarize_segment_file,
)

# Define BasePolicyConfig if not imported - Use Union as placeholder based on flake8 fix attempt  # noqa: E501
BasePolicyConfig = Union[CompactionPolicyConfig, SummarizationPolicyConfig]


logger = logging.getLogger(__name__)


class MemoryMaintenanceService:
    """
    Manages background memory maintenance tasks like compaction and summarization.
    Uses APScheduler for scheduling.
    """

    def __init__(self, config: AppConfig, summarizer: Optional[BaseSummarizer] = None):
        """
        Initializes the Memory Maintenance Service using application configuration.

        Args:
            config: The loaded application configuration (AppConfig).
            summarizer: An optional summarizer instance for the summarization task.
        """
        self.config = config
        self.maintenance_config: MemoryMaintenanceConfig = config.memory_maintenance
        self.summarizer = summarizer

        self.memory_base_path = config.paths.memory
        self.snapshot_base_path = config.paths.temp / "memory_snapshots"
        self.scan_interval_seconds = self.maintenance_config.scan_interval_seconds
        self.lock_timeout_seconds = self.maintenance_config.lock_timeout_seconds

        self.scheduler = AsyncIOScheduler()
        self._job_id = "memory_maintenance_job"
        self._running = False

        self.snapshot_base_path.mkdir(parents=True, exist_ok=True)
        logger.info("Memory Maintenance Service initialized...")

        # Simplified logging from user's manual fix example
        try:
            comp_policy_attr = getattr(
                self.maintenance_config,
                "default_compaction_policy",
                # Fallback to the single policy if default list doesn't exist
                self.maintenance_config.compaction_policy,
            )
            logger.info(f"Default Compaction Policy: {comp_policy_attr.dict()}")
        except AttributeError:
            logger.warning("Could not determine default compaction policy from config.")

        try:
            summ_policy_attr = getattr(
                self.maintenance_config,
                "default_summarization_policy",
                # Fallback to the single policy if default list doesn't exist
                self.maintenance_config.summarization_policy,
            )
            logger.info(f"Default Summarization Policy: {summ_policy_attr.dict()}")
        except AttributeError:
            logger.warning(
                "Could not determine default summarization policy from config."
            )

        if not self.summarizer:
            logger.warning(
                "No summarizer provided; summarization tasks will be skipped."
            )

    async def start(self):
        """Adds the maintenance job and starts the scheduler."""
        if self.scheduler.running:
            logger.warning("Maintenance scheduler already running.")
            return

        logger.info("Starting Memory Maintenance Service scheduler...")
        try:
            self.scheduler.add_job(
                self._perform_maintenance,
                "interval",
                seconds=self.maintenance_config.scan_interval_seconds,
                id=self._job_id,
                replace_existing=True,
                misfire_grace_time=self.maintenance_config.misfire_grace_time,
            )
            logger.info(
                f"Scheduled maintenance job '{self._job_id}' with interval "
                f"{self.maintenance_config.scan_interval_seconds}s."
            )
            self.scheduler.start()
            self._running = True
            logger.info("Memory Maintenance Service scheduler started.")
        except ImportError as e:
            logger.critical(
                f"Failed to start Memory Maintenance: APScheduler not installed or "
                f"import failed: {e}"
            )
            self._running = False
            raise
        except Exception as e:
            logger.exception(
                f"Failed to start Memory Maintenance Service scheduler: {e}"
            )
            self._running = False
            raise

    async def stop(self):
        """Stops the maintenance service scheduler."""
        if not self.scheduler.running:
            logger.warning("Maintenance scheduler not running.")
            return

        logger.info("Stopping Memory Maintenance Service scheduler...")
        try:
            self.scheduler.shutdown(wait=False)
            self._running = False
            logger.info("Memory Maintenance Service scheduler stopped.")
        except Exception as e:
            logger.exception(f"Error stopping maintenance scheduler: {e}")

    async def _perform_maintenance(self):
        """Scans memory directories and triggers processing for each."""
        logger.info(f"Running memory maintenance cycle for {self.memory_base_path}...")
        try:
            if not self.memory_base_path.is_dir():
                logger.error(
                    f"Memory base path {self.memory_base_path} does not exist or "
                    f"is not a directory."
                )
                return

            process_agents = getattr(self.maintenance_config, "process_agents", None)
            skip_agents = getattr(self.maintenance_config, "skip_agents", None)

            agent_tasks = []
            try:
                agent_dirs = list(self.memory_base_path.iterdir())
            except OSError as e:
                logger.error(
                    f"Failed to list agent directories in {self.memory_base_path}: {e}",
                    exc_info=True,
                )
                return

            for agent_dir in agent_dirs:
                if agent_dir.is_dir():
                    agent_id = agent_dir.name
                    if process_agents is not None and agent_id not in process_agents:
                        logger.debug(
                            f"Skipping agent {agent_id} (not in process_list)."
                        )
                        continue
                    if skip_agents is not None and agent_id in skip_agents:
                        logger.debug(f"Skipping agent {agent_id} (in skip_list).")
                        continue

                    logger.debug(f"Scheduling memory processing for agent: {agent_id}")
                    agent_tasks.append(
                        asyncio.create_task(
                            self._process_agent_memory(agent_dir),
                            name=f"process_agent_{agent_id}",
                        )
                    )

            if agent_tasks:
                results = await asyncio.gather(*agent_tasks, return_exceptions=True)
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        task_name = agent_tasks[i].get_name()
                        agent_id_failed = (
                            task_name.split("_")[-1]
                            if task_name.startswith("process_agent_")
                            else "unknown"
                        )
                        logger.error(
                            f"Error processing memory for agent '{agent_id_failed}': {result}",  # noqa: E501
                            exc_info=result,
                        )
                logger.info("Finished processing agent memory directories this cycle.")
            else:
                logger.info("No agent memory directories found/selected to process.")
        except Exception as e:
            logger.critical(
                f"Unexpected critical error during memory maintenance cycle: {e}",
                exc_info=True,
            )

    def _get_policy_for_file(
        self,
        file_path: Path,
        agent_id: str,
        policy_type: Literal["compaction", "summarization"],
    ) -> Optional[BasePolicyConfig]:  # Uses Union defined globally
        """Finds the most specific policy matching the file and agent."""
        # Simplified: Assumes lists default_compaction_policies etc exist now
        policies_to_check: List[BasePolicyConfig] = []
        override_config = self.maintenance_config.agent_policy_overrides.get(agent_id)

        # 1. Get candidate policies (agent overrides + defaults)
        if policy_type == "compaction":
            if override_config and override_config.compaction_policies:
                policies_to_check.extend(override_config.compaction_policies)
            policies_to_check.extend(
                getattr(self.maintenance_config, "default_compaction_policies", [])
            )
        elif policy_type == "summarization":
            if override_config and override_config.summarization_policies:
                policies_to_check.extend(override_config.summarization_policies)
            policies_to_check.extend(
                getattr(self.maintenance_config, "default_summarization_policies", [])
            )

        # 2. Find the best match based on file_pattern
        best_match: Optional[BasePolicyConfig] = None
        best_match_specificity = -1

        relative_path_str = str(
            file_path.relative_to(self.snapshot_base_path / agent_id)
        )

        for policy in policies_to_check:
            if not policy.enabled:
                continue

            pattern = policy.file_pattern
            if pattern is None:  # Default policy for type
                specificity = 0
                if fnmatch.fnmatch(relative_path_str, "*"):
                    if specificity > best_match_specificity:
                        best_match = policy
                        best_match_specificity = specificity
            elif fnmatch.fnmatch(relative_path_str, pattern):
                specificity = len(pattern)
                if specificity > best_match_specificity:
                    best_match = policy
                    best_match_specificity = specificity

        if best_match:
            logger.debug(
                f"Selected {policy_type} policy for '{relative_path_str}': "
                f"pattern='{best_match.file_pattern}', enabled={best_match.enabled}"
            )
        return best_match

    async def _process_agent_memory(self, agent_memory_path: Path):
        """Processes a single agent's memory directory (snapshot, compaction, summarization)."""  # noqa: E501
        agent_id = agent_memory_path.name
        snapshot_dir = self.snapshot_base_path / agent_id
        agent_lock_file = agent_memory_path.with_suffix(".lock")

        # --- Snapshotting ---
        try:
            if snapshot_dir.exists():
                logger.warning(
                    f"Previous snapshot dir {snapshot_dir} exists, removing."
                )
                shutil.rmtree(snapshot_dir)

            logger.info(f"Creating snapshot of {agent_memory_path} at {snapshot_dir}")
            shutil.copytree(
                agent_memory_path,
                snapshot_dir,
                symlinks=False,
                ignore_dangling_symlinks=True,
            )
            logger.info(f"Snapshot created successfully for {agent_id}.")

        except (shutil.Error, OSError) as e:  # Removed redundant PermissionError
            logger.exception(
                f"Failed to create/cleanup snapshot for {agent_id} from "
                f"{agent_memory_path} to {snapshot_dir}: {e}"
            )
            if snapshot_dir.exists():
                try:
                    shutil.rmtree(snapshot_dir)
                except Exception as rm_e:
                    logger.error(
                        f"Secondary error cleaning snapshot {snapshot_dir}: {rm_e}"
                    )
            return
        except Exception as e:
            logger.exception(f"Unexpected error during snapshot for {agent_id}: {e}")
            if snapshot_dir.exists():
                try:
                    shutil.rmtree(snapshot_dir)
                except Exception as rm_e:
                    logger.error(
                        f"Secondary error cleaning snapshot {snapshot_dir}: {rm_e}"
                    )
            return

        # --- Processing / Replacement / Cleanup (User's manually corrected structure) ---  # noqa: E501
        logger.info(f"Processing snapshot for agent {agent_id} at {snapshot_dir}")
        processed_count = skipped_count = error_count = 0

        # ---------------------------------------------------
        # unified try / finally  → cleanup always guaranteed
        # ---------------------------------------------------
        replacement_successful = False
        backup_dir = agent_memory_path.with_suffix(".bak")  # Define backup path early

        try:
            # ---------- 3. PROCESS FILES IN SNAPSHOT ----------
            try:
                # Use rglob to recursively find all files
                for segment_file in snapshot_dir.rglob("*"):
                    if not segment_file.is_file():
                        continue  # Skip directories

                    # Determine policies based on file name or other logic if needed
                    compaction_policy = self._get_policy_for_file(
                        segment_file, agent_id, "compaction"
                    )
                    summarization_policy = self._get_policy_for_file(
                        segment_file, agent_id, "summarization"
                    )

                    if not compaction_policy and not summarization_policy:
                        # logger.debug(f"Skipping file {segment_file.name}: No matching policies found.") # Too noisy  # noqa: E501
                        skipped_count += 1
                        continue  # Skip file if no applicable policy found

                    # Ensure policies are the correct type for the helper function
                    comp_conf: Optional[CompactionPolicyConfig] = (
                        compaction_policy
                        if isinstance(compaction_policy, CompactionPolicyConfig)
                        else None
                    )
                    summ_conf: Optional[SummarizationPolicyConfig] = (
                        summarization_policy
                        if isinstance(summarization_policy, SummarizationPolicyConfig)
                        else None
                    )

                    # Only proceed if at least one applicable policy exists and is enabled  # noqa: E501
                    if (comp_conf and comp_conf.enabled) or (
                        summ_conf and summ_conf.enabled and self.summarizer
                    ):  # Also check if summarizer exists
                        logger.debug(
                            f"Processing segment: {segment_file.relative_to(snapshot_dir)}"  # noqa: E501
                        )
                        # Pass potentially None policies; _process_segment_file handles None  # noqa: E501
                        success = await self._process_segment_file(
                            segment_file,
                            compaction_policy=comp_conf,
                            summarization_policy=summ_conf,
                        )
                        # Use augmented assignment directly
                        (processed_count if success else error_count).__iadd__(1)
                    else:
                        # logger.debug(f"Skipping file {segment_file.name}: Applicable policies are disabled or summarizer missing.") # Too noisy  # noqa: E501
                        skipped_count += 1
            except Exception as e:
                logger.exception(
                    f"Error during snapshot file iteration for agent {agent_id}: {e}"
                )
                error_count += 1  # Count this as an error

            logger.info(
                f"Agent {agent_id}: Processed={processed_count}, Skipped={skipped_count}, Errors={error_count}"  # noqa: E501
            )

            # ---------- 4. ATOMIC REPLACEMENT ----------
            if (
                error_count == 0 and processed_count > 0
            ):  # Only replace if processing happened without errors
                logger.info(f"Attempting atomic replacement for agent {agent_id}")
                agent_lock = FileLock(
                    str(agent_lock_file), timeout=self.lock_timeout_seconds
                )
                try:
                    with agent_lock:
                        logger.info(
                            f"Agent lock acquired for {agent_id}. Performing replacement."  # noqa: E501
                        )

                        # 1. Backup Original Directory (rename)
                        if agent_memory_path.exists():
                            logger.debug(
                                f"Renaming original {agent_memory_path} to {backup_dir}"
                            )
                            # Use os.replace for better atomicity if possible on the OS
                            os.replace(agent_memory_path, backup_dir)
                        else:
                            logger.warning(
                                f"Original agent memory path {agent_memory_path} not found during replacement. Proceeding with snapshot rename."  # noqa: E501
                            )
                            backup_dir = None  # Indicate no backup exists / nothing to roll back to  # noqa: E501

                        # 2. Rename Snapshot to Original
                        logger.debug(
                            f"Renaming snapshot {snapshot_dir} to {agent_memory_path}"
                        )
                        os.replace(snapshot_dir, agent_memory_path)

                        replacement_successful = True
                        logger.info(f"Atomic replacement successful for {agent_id}.")
                        logger.debug(
                            f"Agent lock released for {agent_id}."
                        )  # Lock released by 'with'

                except (
                    LockAcquisitionError,
                    OSError,
                    Exception,
                ) as e:  # Catch relevant errors
                    logger.exception(f"Atomic replacement failed for {agent_id}: {e}")
                    # Attempt rollback if backup exists and original doesn't (or failed replace didn't create it)  # noqa: E501
                    if (
                        backup_dir
                        and backup_dir.exists()
                        and not agent_memory_path.exists()
                    ):
                        logger.warning(
                            f"Attempting rollback: renaming {backup_dir} back to {agent_memory_path}"  # noqa: E501
                        )
                        try:
                            os.replace(backup_dir, agent_memory_path)
                            logger.info(f"Rollback successful for {agent_id}.")
                            backup_dir = (
                                None  # Indicate rollback succeeded, backup is now live
                            )
                        except OSError as rbe:
                            logger.critical(
                                f"CRITICAL: Rollback FAILED for {agent_id}! Manual intervention needed. Backup at {backup_dir}. Error: {rbe}"  # noqa: E501
                            )
                    # else: logger error handled by exception log above

            elif error_count > 0:
                logger.warning(
                    f"Skipping replacement for agent {agent_id} due to {error_count} processing errors."  # noqa: E501
                )
            else:  # processed_count == 0
                logger.info(
                    f"Skipping replacement for agent {agent_id} as no files were processed or needed processing."  # noqa: E501
                )
                # replacement_successful remains False (or True if we consider no-op a success? Let's say False)  # noqa: E501

        finally:
            # ---------- 5. UNIFIED CLEAN-UP ----------
            # Always clean up snapshot if it exists (it shouldn't if os.replace succeeded)  # noqa: E501
            if snapshot_dir.exists():
                logger.info(f"Cleaning up snapshot directory: {snapshot_dir}")
                shutil.rmtree(
                    snapshot_dir, ignore_errors=True
                )  # Use ignore_errors for robustness

            # Clean up backup only if replacement was successful AND backup exists
            if replacement_successful and backup_dir and backup_dir.exists():
                logger.info(f"Cleaning up backup directory: {backup_dir}")
                shutil.rmtree(backup_dir, ignore_errors=True)
            # Log if backup is retained due to failure
            elif not replacement_successful and backup_dir and backup_dir.exists():
                logger.warning(
                    f"Replacement failed or was skipped. Backup directory retained: {backup_dir}"  # noqa: E501
                )

    async def _process_segment_file(
        self,
        segment_file_path: Path,
        compaction_policy: Optional[CompactionPolicyConfig],
        summarization_policy: Optional[SummarizationPolicyConfig],
    ) -> bool:
        """Applies compaction and summarization to a single segment file."""
        logger.debug(f"Processing segment file: {segment_file_path.name}")
        success = True

        # --- Compaction ---
        if compaction_policy and compaction_policy.enabled:
            logger.debug(
                f"Applying compaction using policy: {compaction_policy.dict()}"
            )
            try:
                compact_result = compact_segment_file(
                    segment_file_path,
                    compaction_policy.dict(),
                    compress_after=compaction_policy.compress_after_processing,
                )
                if not compact_result:
                    logger.warning(
                        f"Compaction failed for {segment_file_path.name} (returned False)"  # noqa: E501
                    )
                    success = False
            except CompactionError as ce:
                logger.error(
                    f"CompactionError for {segment_file_path.name}: {ce}", exc_info=True
                )
                success = False
            except Exception as e:
                logger.error(
                    f"Unexpected compaction error for {segment_file_path.name}: {e}",
                    exc_info=True,
                )
                success = False
        # ... (rest of compaction logic)

        # --- Summarization ---
        if summarization_policy and summarization_policy.enabled and self.summarizer:
            logger.debug(
                f"Applying summarization using policy: {summarization_policy.dict()}"
            )
            try:
                summarize_result = summarize_segment_file(
                    segment_file_path,
                    self.summarizer,
                    summarization_policy.dict(),
                    compress_after=summarization_policy.compress_after_processing,
                )
                if not summarize_result:
                    logger.warning(
                        f"Summarization failed for {segment_file_path.name} (returned False)"  # noqa: E501
                    )
                    success = False
            except SummarizationError as se:
                logger.error(
                    f"SummarizationError for {segment_file_path.name}: {se}",
                    exc_info=True,
                )
                success = False
            except Exception as e:
                logger.error(
                    f"Unexpected summarization error for {segment_file_path.name}: {e}",
                    exc_info=True,
                )
                success = False
        elif (
            summarization_policy
            and summarization_policy.enabled
            and not self.summarizer
        ):
            logger.warning(
                f"Summarization policy enabled for {segment_file_path.name}, but no summarizer provided."  # noqa: E501
            )
        # ... (rest of summarization logic)

        if not success:
            logger.warning(f"Segment processing FAILED for: {segment_file_path}")
        return success


# Example usage (for testing purposes) - KEEPING this simple
async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger.info("Starting Memory Maintenance Service Test...")

    # Simplified setup - Requires manual creation of ./temp_memory_test/agent_XYZ/memory/file.json  # noqa: E501
    test_config_path = Path("config/settings.dev.yaml")  # Or appropriate config
    if not test_config_path.exists():
        logger.error(f"Test config not found at {test_config_path}. Cannot run test.")
        return

    try:
        config = AppConfig.load(config_path=str(test_config_path))
        # Assume logging is configured globally or by AppConfig loader
        # No summarizer for basic test
        service = MemoryMaintenanceService(config=config, summarizer=None)
        await service.start()
        logger.info("Service started. Running for 10 seconds...")
        await asyncio.sleep(10)
        await service.stop()
        logger.info("Service stopped.")

    except Exception as e:
        logger.exception(f"Error during test execution: {e}")

    logger.info("Test finished. Check logs and ./temp_memory_test directory state.")


if __name__ == "__main__":
    # Note: Test requires manual setup and config file.
    asyncio.run(main())
