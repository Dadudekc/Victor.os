import threading
from dream_mode.agents.supervisor_agent import SupervisorAgent
from dream_mode.agents.chatgpt_web_agent import ChatGPTWebAgent
from dream_mode.agents.cursor_worker import run as cursor_run
import os
import logging
import time
import argparse

# Enforce using local blob channel for inter-agent communication
os.environ["USE_LOCAL_BLOB"] = "1"

logging.basicConfig(level=logging.INFO)

ASSETS_DIR = os.path.join(os.getcwd(), 'assets')
HUMAN_DIRECTIVE_PATH = os.getenv('HUMAN_DIRECTIVE_PATH', 'runtime/human_directive.json')
SUPERVISOR_RESULTS_PATH = os.getenv('SUPERVISOR_RESULTS_PATH', 'runtime/supervisor_results.json')


def main():
    parser = argparse.ArgumentParser(description="Run the Dream.os autonomy loop")
    parser.add_argument('--simulate', action='store_true', help='Enable ChatGPT WebAgent simulation mode')
    parser.add_argument('--workers', type=int, default=8, help='Number of Cursor workers to launch')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    args = parser.parse_args()

    # Configure logging level based on verbosity
    logging.getLogger().setLevel(logging.DEBUG if args.verbose else logging.INFO)

    # Supervisor Agent
    supervisor = SupervisorAgent(directive_path=HUMAN_DIRECTIVE_PATH)
    # ChatGPT WebAgent with optional simulation mode
    chatgpt_agent = ChatGPTWebAgent(agent_id='chatgpt_simulated', conversation_url=None, simulate=args.simulate)

    # Launch Supervisor
    threading.Thread(target=supervisor.run_loop, daemon=True, name='Supervisor').start()

    # Launch ChatGPT simulated agent loop
    def chatgpt_loop():
        while True:
            chatgpt_agent.run_cycle()
    threading.Thread(target=chatgpt_loop, daemon=True, name='ChatGPTSim').start()

    # Launch Cursor workers (skip in simulation mode)
    if not args.simulate:
        for i in range(1, args.workers + 1):
            worker_id = f'cursor_{i:03}'
            threading.Thread(target=cursor_run, args=(worker_id,), daemon=True, name=f'Cursor{worker_id}').start()
    else:
        logging.info("Simulation mode enabled: skipping Cursor UI workers")

    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('Shutting down')


if __name__ == '__main__':
    main() 