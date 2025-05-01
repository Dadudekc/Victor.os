import json  # Moved import to top
import os
import re
import sys
import traceback

# Add project root to sys.path
script_dir = os.path.dirname(__file__)  # social/
project_root = os.path.abspath(
    os.path.join(script_dir, "..")
)  # Go up one level from social/
if project_root not in sys.path:
    sys.path.insert(0, project_root)
del sys  # Remove sys from module scope after use

# Core imports
try:
    from governance_memory_engine import (  # Corrected import path (assuming root)
        load_memory,
    )
    from template_engine import render_template

    from dreamos.core.logging.swarm_logger import (  # Assuming this is the correct path
        log_event,
    )

    # Import prompt staging service and template engine
    from dreamos.prompt_staging_service import stage_and_execute_prompt
except ImportError as e:
    # print(f"[PostContextGenerator] Warning: Failed to import dependencies: {e}")
    # Log the import error before exiting
    log_event(
        "AGENT_CRITICAL",
        "PostContextGenerator",
        {"error": "Failed to import dependencies", "details": str(e)},
    )
    # Re-import sys to use sys.exit
    import sys

    sys.exit(f"Critical dependency missing: {e}")

# Define source for logging
_SOURCE = "PostContextGenerator"

# Constants
MAX_GOVERNANCE_EVENTS = 5
LATEST_EVENT_INDEX = -1
JSON_BLOCK_REGEX_GROUP = 1


def generate_context_from_governance(max_events=MAX_GOVERNANCE_EVENTS):
    """Generates a context dictionary based on the latest governance event using LLM analysis."""
    log_event(
        "AGENT_INFO",
        _SOURCE,
        {"message": "Generating post context from governance memory..."},
    )
    context = {
        "title": None,
        "proposal_summary": None,
        "gpt_decision": None,
        "reflection_snippet": None,
        "general_update": None,
        "status_update": None,
        "governance_update": False,
    }

    try:
        memory = load_memory()
        if not memory:
            context["general_update"] = "No recent governance activity."
            log_event("AGENT_WARNING", _SOURCE, {"warning": "No memory found"})
            return context

        sorted_events = sorted(memory, key=lambda x: x["timestamp"])
        if not sorted_events:
            context["general_update"] = "No events found after sorting."
            log_event(
                "AGENT_WARNING", _SOURCE, {"warning": "No events after sorting memory"}
            )
            return context

        latest_event = sorted_events[LATEST_EVENT_INDEX]
        context["governance_update"] = True
        context["event_type"] = latest_event.get("event_type", "UNKNOWN_EVENT")

        logger.info(
            f"Attempting LLM context generation for event: {context['event_type']}"
        )
        try:
            # 1. Prepare context for the new template
            template_context = {"event": latest_event}
            # 2. Define path to the new template (assuming it exists)
            template_path = "prompts/governance/generate_context_from_event.j2"
            # 3. Render prompt
            prompt_text = render_template(template_path, template_context)

            if prompt_text:
                # 4. Call LLM via staging service
                llm_response = stage_and_execute_prompt(
                    prompt_text,
                    agent_id="PostContextGenerator",
                    purpose="generate_governance_context",
                )

                if llm_response:
                    # 5. Parse response (assuming JSON with title, summary, etc.)
                    try:
                        # Attempt to find and parse JSON block
                        json_match = re.search(
                            r"```json\s*(\{.*?\})\s*```",
                            llm_response,
                            re.DOTALL | re.IGNORECASE,
                        )
                        if json_match:
                            generated_data = json.loads(
                                json_match.group(JSON_BLOCK_REGEX_GROUP)
                            )
                            # 6. Update context dictionary
                            context["title"] = generated_data.get(
                                "title", "LLM Generated Title"
                            )
                            context["proposal_summary"] = generated_data.get("summary")
                            context["reflection_snippet"] = generated_data.get(
                                "reflection"
                            )
                            context["general_update"] = generated_data.get(
                                "general_update"
                            )
                            context["status_update"] = generated_data.get(
                                "status_update"
                            )
                            # Add other fields as defined by the expected LLM output schema
                            log_event(
                                "LLM_CONTEXT_GEN_SUCCESS",
                                _SOURCE,
                                {
                                    "info": "LLM context generation successful",
                                    "event_type": context["event_type"],
                                },
                            )
                        else:
                            log_event(
                                "LLM_CONTEXT_GEN_WARNING",
                                _SOURCE,
                                {
                                    "warning": "LLM context gen JSON block not found",
                                    "llm_response": llm_response,
                                },
                            )
                            context["general_update"] = (
                                "LLM response parsing failed (JSON block)."
                            )
                    except json.JSONDecodeError as json_e:
                        log_event(
                            "LLM_CONTEXT_GEN_ERROR",
                            _SOURCE,
                            {
                                "error": "LLM context gen JSON decode error",
                                "details": str(json_e),
                                "llm_response": llm_response,
                            },
                        )
                        context["general_update"] = (
                            f"LLM response parsing failed (JSON Decode: {str(json_e)})."
                        )
                    except Exception as parse_e:
                        log_event(
                            "LLM_CONTEXT_GEN_ERROR",
                            _SOURCE,
                            {
                                "error": "LLM context gen parsing failed",
                                "details": str(parse_e),
                            },
                        )
                        context["general_update"] = (
                            f"LLM response parsing failed ({str(parse_e)})."
                        )
                else:
                    log_event(
                        "LLM_CONTEXT_GEN_WARNING",
                        _SOURCE,
                        {"warning": "LLM context generation returned no response"},
                    )
                    context["general_update"] = (
                        "LLM context generation failed (no response)."
                    )
            else:
                log_event(
                    "LLM_CONTEXT_GEN_ERROR",
                    _SOURCE,
                    {
                        "error": "Failed to render context gen template",
                        "template": template_path,
                    },
                )
                context["general_update"] = (
                    "Context generation template rendering failed."
                )

        except Exception as gen_e:
            log_event(
                "LLM_CONTEXT_GEN_ERROR",
                _SOURCE,
                {"error": "Error during LLM context generation", "details": str(gen_e)},
            )
            context["general_update"] = f"LLM context generation failed: {str(gen_e)}"
        # --- End LLM Context Generation ---

        # --- (Keep the existing LLM call that analyzes the *whole* context dict) ---
        # Call LLM to analyze context (This might now analyze LLM-generated fields)
        # Limit the number of events (ensure max_events is defined or passed in)
        # max_events = 50  # Example limit, remove if unused
        # recent_events = sorted_events[-max_events:] # Commented out as max_events is unused
        recent_events = sorted_events  # Use all sorted events for now

        # Get the latest relevant event (customize this logic heavily)
        latest_event = recent_events[
            LATEST_EVENT_INDEX
        ]  # Assuming memory is list of dicts
        context["governance_update"] = True
        event_type = latest_event.get("event_type", "UNKNOWN_EVENT")
        details = latest_event.get("details", {})
        context["event_type"] = event_type  # Add event type to context

        # --- Example Logic (Highly Simplistic - Needs Significant Enhancement) ---
        if event_type == "PROPOSAL_CREATED":
            context["title"] = "New Proposal Submitted"
            context["proposal_summary"] = details.get(
                "proposal_header", "See details in log."
            )
            context["status_update"] = details.get("status")
        elif event_type == "PROPOSAL_STATUS_UPDATED":
            context["title"] = "Proposal Status Change"
            context["proposal_summary"] = (
                f"{details.get('proposal_header', 'Proposal')} -> {details.get('new_status', 'Updated')}"
            )
            context["status_update"] = details.get("new_status")
            context["reflection_snippet"] = details.get(
                "reason"
            )  # Maybe use reason as a snippet
        elif event_type == "DISAGREEMENT_LOGGED":
            context["title"] = "Disagreement Logged"
            context["reflection_snippet"] = (
                f"Objection on Ref: {details.get('reflection_id')} - {details.get('objection_summary', '')}"
            )
            context["status_update"] = details.get("status")
        elif event_type == "HUMAN_DECISION":
            context["title"] = "Human Review Decision"
            item_type = details.get("item_type", "Item")
            item_header = details.get("item_header", "")
            action = details.get("human_action", "processed")
            context["general_update"] = (
                f"Human reviewer {action} {item_type} '{item_header}'"
            )
            context["status_update"] = details.get("new_status")
        else:
            context["general_update"] = f"Recent system activity logged: {event_type}"

        # print(f"[context_gen] Generated context based on event: {event_type}")
        log_event(
            "AGENT_INFO",
            _SOURCE,
            {"info": "Generated context based on event", "event_type": event_type},
        )

        # --- Call LLM to analyze context ---
        try:
            # Pass the context built so far to the analysis template
            analysis_context = {"current_context": context}
            template_path = "prompts/social/analyze_context.j2"
            prompt_text = render_template(template_path, analysis_context)

            if prompt_text:
                # Assuming stage_and_execute_prompt exists and works
                llm_response = stage_and_execute_prompt(
                    prompt_text,
                    agent_id="PostContextGenerator",
                    purpose="analyze_social_context",
                )
                if llm_response:
                    # Parse the JSON response from the LLM
                    try:
                        # Basic parsing, assuming ```json block
                        json_match = re.search(
                            r"```json\s*(\{.*?\})\s*```",
                            llm_response,
                            re.DOTALL | re.IGNORECASE,
                        )
                        if json_match:
                            analysis_result = json.loads(
                                json_match.group(JSON_BLOCK_REGEX_GROUP)
                            )
                            context["gpt_decision"] = (
                                analysis_result  # Store the whole analysis
                            )
                            log_event(
                                "LLM_ANALYSIS_SUCCESS",
                                _SOURCE,
                                {
                                    "info": "LLM context analysis successful",
                                    "analysis": analysis_result,
                                },
                            )
                        else:
                            log_event(
                                "LLM_ANALYSIS_WARNING",
                                _SOURCE,
                                {
                                    "warning": "LLM analysis JSON block not found",
                                    "llm_response": llm_response,
                                },
                            )
                            context["gpt_decision"] = {
                                "error": "Parsing failed: JSON block not found"
                            }
                    except json.JSONDecodeError as json_e:
                        log_event(
                            "LLM_ANALYSIS_ERROR",
                            _SOURCE,
                            {
                                "error": "LLM analysis JSON decode error",
                                "details": str(json_e),
                                "llm_response": llm_response,
                            },
                        )
                        context["gpt_decision"] = {
                            "error": f"Parsing failed: {str(json_e)}"
                        }
                    except Exception as parse_e:
                        log_event(
                            "LLM_ANALYSIS_ERROR",
                            _SOURCE,
                            {
                                "error": "LLM analysis parsing failed",
                                "details": str(parse_e),
                            },
                        )
                        context["gpt_decision"] = {
                            "error": f"Parsing failed: {str(parse_e)}"
                        }
                else:
                    log_event(
                        "LLM_ANALYSIS_WARNING",
                        _SOURCE,
                        {"warning": "LLM analysis returned no response"},
                    )
                    context["gpt_decision"] = {"error": "LLM did not respond"}
            else:
                log_event(
                    "LLM_ANALYSIS_ERROR",
                    _SOURCE,
                    {
                        "error": "Failed to render analysis template",
                        "template": template_path,
                    },
                )
                context["gpt_decision"] = {"error": "Template rendering failed"}
        except Exception as llm_e:
            log_event(
                "LLM_ANALYSIS_ERROR",
                _SOURCE,
                {"error": "Error during LLM context analysis", "details": str(llm_e)},
            )
            context["gpt_decision"] = {"error": f"LLM analysis failed: {str(llm_e)}"}
        # --- End LLM Context Analysis ---

    except Exception as e:
        # print(f"[context_gen] Error generating context: {e}")
        log_event(
            "AGENT_ERROR",
            _SOURCE,
            {
                "error": "Failed to generate context",
                "details": str(e),
                "traceback": traceback.format_exc(),
            },
        )
        context["general_update"] = "Error retrieving latest governance status."
        context["gpt_decision"] = {"error": "Context generation failed"}

    return context


# --- Example Usage --- #
if __name__ == "__main__":
    # Ensure Agent1/governance_memory.json exists and has some data for testing
    test_context = generate_context_from_governance()
    print("\n--- Generated Context ---")
    print(json.dumps(test_context, indent=2))
    print("-----------------------")
