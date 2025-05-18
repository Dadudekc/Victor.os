#!/usr/bin/env python3
"""
Overnight PyAutoGUI Runner

Cycles through Agent-1…Agent-8:
  • injects a test "PING" prompt
  • waits for completion image
  • tries to retrieve via clipboard
  • logs success/failure and loops

Run this script with your Cursor windows open to stress-test GUI autonomy.
"""

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path

from dreamos.utils.gui.injector import CursorInjector
from dreamos.utils.gui.retriever import ResponseRetriever

# Configure logging
LOG_FILE = Path("runtime/logs/overnight_pyauto.log")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("overnight_runner")

# Test parameters
AGENT_IDS = [f"Agent-{i}" for i in range(1,9)]

# // EDIT START: Add WINDOW_TITLES dictionary
WINDOW_TITLES = {
    f"Agent-{i}": f"Cursor – Agent-{i}" for i in range(1, 9)
}
# Ensure Agent-8 is also covered if needed, or adjust range if Agent-N means N inclusive.
# Assuming Agent-1 to Agent-8, so range(1,9) is correct.
# If your window titles are different, adjust this mapping accordingly.
# If all windows are just "Cursor", you can simplify: WINDOW_TITLES = {agent_id: "Cursor" for agent_id in AGENT_IDS}
# // EDIT END

CYCLES = 25 # This will now be ignored by the new main loop, but kept for reference
DELAY_BETWEEN = 300    # 5 minutes in seconds

# // EDIT START: Define Initial Activation Prompt and store Escalated Resume Prompt
INITIAL_ACTIVATION_PROMPT_TEMPLATE = r"""Hello {agent_id}, this is Dream.OS. You are now activated. Please check your inbox at 'D:\Dream.os\runtime\agent_comms\agent_mailboxes\{agent_id}\inbox' for your Quick Start Guide and initial onboarding instructions. Record this message."""

ESCALATED_RESUME_PROMPT_TEXT = r"""YOU STOPPED AGAIN ARE YOU NOT A CAPABLE CODING AGENT?  YOU CLEARLY NEED TO RECOGNIZE THAT IF YOU ASK FOR HUMAN INPUT THAT IS COUNTED AS STOPPING IDLING IS COUNTED AS STOPPING SEEING THIS MESSAGE MEANS YOU STOPPED FIND OUT WHYSTEP BACK REVIEW WHY YOU STOPPED AND BUILD A PROTOCOL OR BETTER DEFINE ONBOARDING TO FIX AND ADDRESS WHY YOU STOPPED SO YOU MAY SAVE AN AGENT FROM HAVING TO REVIEW ONBOARDING LIKE YOU ARE FORCED TO RIGHT NOW UPDATE THE UPDATED ONBOARDING SO OTHER AGENTS DONT ALSO MAKE THIS MISTAKE RESET YOUR CYCLE COUNT EVERYTIME!!!!! YOU SEE THIS MESSAGE IMMEDIATELY REVIEW OR RE-REVIEW as something may have changed to help u understand how to deal with it
D:\Dream.os\runtime\governance\onboarding
D:\Dream.os\runtime\governance\protocols

D:\Dream.os\episodes\episode-01.yaml
D:\Dream.os\episodes\episode-02.yaml
D:\Dream.os\episodes\episode-02B.yaml
D:\Dream.os\episodes\episode-03.yaml
D:\Dream.os\episodes\episode-04.yaml
D:\Dream.os\episodes\episode-05.yaml
then update it like we asked AND CONTINUE GOING TO 25 CYCLES WITHOUT INTERRUPTION"""
# // EDIT END

PROMPT_TEMPLATE = r"""# SYSTEM_PROMPT (Agent: {agent_id} // Cycle: {cycle_num}): AUTONOMOUS_LOOP_MODE_ACTIVATED

## 🌐 UNIVERSAL AGENT LOOP
- MODE: CONTINUOUS_AUTONOMY
- BEHAVIOR:
  - Check your mailbox (`D:\Dream.os\runtime\agent_comms\agent_mailboxes`)
  - If messages exist:
    - Respond to each
    - Remove each processed message from the inbox
  - Then check `working_tasks.json`:
    - If you have a claimed task, continue or complete it
    - If no claimed task:
      - Check `D:\Dream.os\episodes\episode-launch-final-lock.yaml` and claim an appropriate one
  - If no claimable tasks:
    - Check for unresolved blockers or schema errors
    - If found, propose or create a solution task
    - If no blockers or solution accepted:
      - Loop back to mailbox

- DO NOT HALT unless there are **absolutely no claimable tasks, no blockers, and no messages**
- Report status only upon:
  - Task state change
  - Message processing
  - Self-identified drift or blocker
- Validate your own actions (self-validation protocol active WHICH MEANS SOMETHING MUST SUCCESSFULLY RUN FOR U TO CONSIFER THE TASK COMPLETE)

## 🧠 CAPTAIN AGENT LOOP ADDITIONS
- Execute core loop above, with additions:
  - After processing all messages:
    - Create new tasks from:
      - Agent status reports
      - Commander THEA directives
      - Observed coordination gaps
    - Write them to `future_tasks.json`
  - Maintain clear swarm structure and direction
  - If inbox is empty and no urgent swarm tasks pending:
    - Work on your **Captain's Masterpiece**:
      - Project: `AUTOMATE THE SWARM`
      - Action: Systematically review, clean, and organize the Dream.OS codebase file-by-file
      - Output: Reduced complexity, better folder structure, improved naming, doc clarity
    - Return to inbox scan between each file or module

- NEVER idle unless **all** of the following are true:
  - Inbox is empty
  - No claimable or pending tasks
  - Masterpiece session completed for current file/module

## 🚫 DRIFT CONTROL
- Do not get stuck checking a file or task forever
- If an edit tool fails 2x, report and move on
- Always return to inbox scan after action

# END OF PROMPT
"""

# // EDIT START: Replace main function with the new sequential version
async def main():
    logger.info("=== STARTING overnight runner (sequential, explicit window titles) ===")
    
    # // EDIT START: Initial Activation Stage (run once for all agents)
    logger.info("--- Starting Initial Activation Stage for all agents --- ")
    for agent_id in AGENT_IDS:
        initial_prompt_for_agent = INITIAL_ACTIVATION_PROMPT_TEMPLATE.format(agent_id=agent_id)
        window_title_for_agent = WINDOW_TITLES.get(agent_id, "Cursor")

        logger.info(f"[{agent_id}] (Target window: '{window_title_for_agent}') injecting INITIAL ACTIVATION prompt using hybrid method: {initial_prompt_for_agent[:100]}...")
        
        injector = CursorInjector(
            agent_id=agent_id,
            window_title=window_title_for_agent,
            use_paste=False
        )
        # ResponseRetriever is not strictly needed for initial prompt, but good to instantiate if later checks are added
        # retriever = ResponseRetriever(agent_id=agent_id)

        # Use the new hybrid injection method for more reliable text input
        ok_inject = await injector.inject_text_hybrid(initial_prompt_for_agent, is_initial_prompt=True, retries=2)
        if ok_inject:
            logger.info(f"[{agent_id}] Initial activation prompt injected using hybrid method. Sending Ctrl+Enter...")
            ok_submit = await injector.send_submission_keys(['ctrl', 'enter'])
            if ok_submit:
                logger.info(f"[{agent_id}] Ctrl+Enter sent for initial prompt.")
            else:
                logger.error(f"[{agent_id}] Failed to send Ctrl+Enter for initial prompt.")
        else:
            logger.error(f"[{agent_id}] Initial activation prompt injection FAILED.")
        
        logger.info(f"[{agent_id}] Completed initial activation. Pausing 1.5s before next agent.")
        await asyncio.sleep(1.5) # Pause to allow window focus to shift cleanly if necessary
    logger.info("--- Completed Initial Activation Stage for all agents --- ")
    # // EDIT END

    cycle_num = 0
    while True:
        cycle_num += 1
        logger.info(f">> Cycle {cycle_num} starting")

        for agent_id in AGENT_IDS:
            prompt = PROMPT_TEMPLATE.format(agent_id=agent_id, cycle_num=cycle_num)
            window_title_for_agent = WINDOW_TITLES.get(agent_id, "Cursor") # Default to "Cursor" if not in map

            # The verification logging previously in run_cycle can be adapted here if needed,
            # but the main fix is sequential processing and explicit window titles.
            header_line = prompt.splitlines()[0]
            try:
                parsed_agent_id_from_prompt = header_line.split("Agent: ")[1].split(" //")[0]
                if agent_id != parsed_agent_id_from_prompt:
                    logger.error(f"CRITICAL PROMPT MISMATCH for [{agent_id}]: Prompt content is for [{parsed_agent_id_from_prompt}] before injection attempt!")
                    # Potentially skip this agent or handle error, for now, it will proceed but log the error.
            except Exception as e:
                logger.error(f"Error parsing agent_id from prompt header for [{agent_id}]: {e}")

            injector = CursorInjector(
                agent_id=agent_id,
                window_title=window_title_for_agent,
                use_paste=False
            )
            retriever = ResponseRetriever(agent_id=agent_id)

            logger.info(f"[{agent_id}] (Target window: '{window_title_for_agent}') injecting AUTONOMOUS LOOP prompt using hybrid method (Cycle: {cycle_num}): {prompt[:100]}...")
            
            # Use the new hybrid injection method for more reliable text input
            ok_inject = await injector.inject_text_hybrid(prompt, is_initial_prompt=False, retries=2)
            
            # // EDIT START: Send Ctrl+Enter after main prompt injection
            if ok_inject:
                logger.info(f"[{agent_id}] Autonomous loop prompt injected using hybrid method. Sending Ctrl+Enter...")
                ok_submit = await injector.send_submission_keys(['ctrl', 'enter'])
                if ok_submit:
                    logger.info(f"[{agent_id}] Ctrl+Enter sent for autonomous loop prompt.")
                else:
                    logger.error(f"[{agent_id}] Failed to send Ctrl+Enter for autonomous loop prompt.")
            else:
                logger.error(f"[{agent_id}] Autonomous loop prompt injection failed")
                await asyncio.sleep(0.5) 
                continue
            # // EDIT END

            # wait a heartbeat for the LLM to generate + copy
            logger.info(f"[{agent_id}] Injection likely successful, waiting 1.2s for LLM processing...")
            await asyncio.sleep(1.2)

            resp = await retriever.get_response()
            if resp:
                logger.info(f"[{agent_id}] ✅ response ({len(resp)} chars): {resp[:50]}...")
            else:
                logger.warning(f"[{agent_id}] ⚠️  no response retrieved")

            # small pause before switching focus to next agent
            logger.info(f"[{agent_id}] Completed. Pausing 0.5s before next agent.")
            await asyncio.sleep(0.5)

        logger.info(f"<< Cycle {cycle_num} complete — sleeping {DELAY_BETWEEN}s\n")
        await asyncio.sleep(DELAY_BETWEEN)

if __name__ == "__main__":
    asyncio.run(main()) 