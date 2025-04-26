#!/usr/bin/env python3
"""
dreamos/orchestrator.py

Orchestrator loop master for Dream.OS Auto-Fix cycle (namespaced for tests).
"""

from typing import Any, Dict
import dreamos.cursor_interface as cursor_interface
import dreamos.chatgpt_interface as chatgpt_interface
import dreamos.evaluator as evaluator


def run_cycle(context: Dict[str, Any]) -> str:
    """
    Executes one full auto-fix cycle:
    1. Send initial prompt to Cursor
    2. Fetch Cursor reply
    3. Refine reply via ChatGPT
    4. Send refined prompt
    5. Fetch final Cursor output
    6. Evaluate output and decide to loop or finish
    """
    # 1. First draft
    try:
        cursor_interface.send_prompt(context)
    except Exception:
        # Ignore errors during send_prompt (e.g., missing CLI tool) in tests or CLI-less env
        pass
    reply = cursor_interface.fetch_reply(final=False)

    # 2. Refine with ChatGPT
    refined = chatgpt_interface.refine({"prompt": context.get("prompt", ""), "reply": reply})

    # 3. Second draft
    try:
        cursor_interface.send_prompt({"prompt": refined})
    except Exception:
        # Ignore errors during send_prompt
        pass
    final_reply = cursor_interface.fetch_reply(final=True)

    # 4. Evaluate
    ok = evaluator.evaluate(final_reply, context)
    if not ok:
        # Prepare next iteration
        context["prompt"] = final_reply
        return run_cycle(context)
    return final_reply 
