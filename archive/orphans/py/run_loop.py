import argparse
import asyncio
import logging
import threading
import time

from dreamos.agents.chatgpt_web_agent import ChatGPTWebAgent
from dreamos.agents.cursor_worker import run as cursor_run
from dreamos.agents.supervisor_agent import SupervisorAgent
from dreamos.core.config import load_app_config
from docs.development.guides.onboarding.utils.enforcement import check_agent_compliance, ComplianceError

# Enforce using local blob channel for inter-agent communication
# os.environ["USE_LOCAL_BLOB"] = "1"

logging.basicConfig(level=logging.INFO)


def main():
    parser = argparse.ArgumentParser(description="Run the Dream.os autonomy loop")
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Enable ChatGPT WebAgent simulation mode",
    )
    parser.add_argument(
        "--workers", type=int, default=8, help="Number of Cursor workers to launch"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    # Configure logging level based on verbosity
    logging.getLogger().setLevel(logging.DEBUG if args.verbose else logging.INFO)

    # EDIT START: Load AppConfig
    config = load_app_config()
    if not config:
        logging.error("Failed to load AppConfig. Exiting.")
        return

    # Force local blob usage if needed by this run mode?
    # Alternatively, ensure the loaded config reflects this.
    if not getattr(config.memory_channel, "use_local_blob", False):
        logging.warning("Forcing use_local_blob=True for run_loop.py execution.")
        config.memory_channel.use_local_blob = True

    # Get paths from config
    human_directive_path = config.project_root / getattr(
        config.paths, "human_directive", "runtime/human_directive.json"
    )
    # supervisor_results_path = config.project_root / getattr(config.paths, 'supervisor_results', 'runtime/supervisor_results.json') # This seems unused by SupervisorAgent  # noqa: E501
    assets_dir = config.project_root / getattr(  # noqa: F841
        config.paths, "assets", "assets"
    )  # Get assets dir from config
    # EDIT END

    # Supervisor Agent
    # supervisor = SupervisorAgent(directive_path=HUMAN_DIRECTIVE_PATH)
    supervisor = SupervisorAgent(
        config=config, directive_path=str(human_directive_path)
    )  # Pass config and correct path

    # Start ChatGPT Agent thread if enabled and not simulating
    if config.chat_agent.enabled and not args.simulate:
        logging.info(
            f"Starting ChatGPTWebAgent for conversation: {config.chat_agent.conversation_url}"  # noqa: E501
        )
        chatgpt_agent = ChatGPTWebAgent(
            config=config,
            agent_id="gpt4_primary",
            conversation_url=config.chat_agent.conversation_url,
            simulate=args.simulate,
        )

        chatgpt_thread = threading.Thread(target=chatgpt_loop, args=(chatgpt_agent,))  # noqa: F821
        chatgpt_thread.daemon = True
        chatgpt_thread.start()
        logging.info("ChatGPT Agent thread started.")
    elif not config.chat_agent.enabled:
        logging.info("ChatGPT Agent is disabled in the config.")
    else:  # Simulation mode
        logging.info("Simulation mode enabled: skipping ChatGPT Agent.")

    # Launch Supervisor
    threading.Thread(target=supervisor.run_loop, daemon=True, name="Supervisor").start()

    # Launch ChatGPT simulated agent loop
    def chatgpt_loop(chatgpt_agent):
        while True:
            chatgpt_agent.run_cycle()

    # Launch Cursor workers (skip in simulation mode)
    # EDIT START: Enforce agent compliance at boot
    STRICT_COMPLIANCE = True  # Set to True to block noncompliant agents
    ONBOARDING_BASE_PATH = "docs/development/guides/onboarding"
    
    if not args.simulate:
        for i in range(1, args.workers + 1):
            worker_id = f"cursor_{i:03}"
            agent_id = worker_id  # Use worker_id as agent_id for compliance check
            try:
                compliance_result = check_agent_compliance(
                    agent_id=agent_id,
                    base_path=ONBOARDING_BASE_PATH,
                    strict=STRICT_COMPLIANCE,
                    escalate_violations=True
                )
                if not compliance_result["compliant"]:
                    logging.error(f"Agent {agent_id} failed compliance. Not launching worker.")
                    continue  # Skip launching this agent
            except ComplianceError as ce:
                logging.error(f"Agent {agent_id} blocked by strict compliance: {ce}")
                continue  # Skip launching this agent
            # Launch agent worker if compliant
            threading.Thread(
                target=cursor_run,
                args=(config, worker_id),
                daemon=True,
                name=f"Cursor{worker_id}",
            ).start()
    else:
        logging.info("Simulation mode enabled: skipping Cursor UI workers")
    # EDIT END: Compliance enforcement at agent boot

    # Keep main thread alive
    try:
        loop = asyncio.get_event_loop()  # noqa: F841
        # Configure logging centrally
        # config = AppConfig.load() # Loaded in main now
        # setup_logging(config)

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down")


if __name__ == "__main__":
    main()
