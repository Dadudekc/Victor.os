# src/dreamos/core/agents/capabilities/library/debate_management.py
import json
import logging
from pathlib import Path
from typing import List, Optional, TypedDict
from uuid import uuid4

# Import schemas
from dreamos.core.comms.debate_schemas import (
    DebateManifest,
    DebateParticipantInfo,
    Persona,
)

# Assuming access to config for paths
from dreamos.core.config import AppConfig

# Import file locking
from filelock import FileLock, Timeout

logger = logging.getLogger(__name__)

# --- Capability Input/Output Schemas --- #


class PersonaInput(TypedDict):
    agent_id: str
    role_name: str
    stance_summary: str
    instructions: str
    background_context: Optional[str]


class DebateInitiateInput(TypedDict):
    topic: str
    proposal_ref: Optional[str]
    participants_personas: List[PersonaInput]  # List of personas to assign
    protocol_id: Optional[str]
    moderator_agent_id: Optional[str]


class DebateInitiateOutput(TypedDict):
    debate_id: Optional[str]
    error: Optional[str]


# ... other schemas ...

# --- Capability Implementations --- #


def debate_initiate_capability(
    input_data: DebateInitiateInput,
    agent_id: str,  # ID of the agent calling the capability (creator)
    config: AppConfig,
) -> DebateInitiateOutput:
    """Initiates a new debate, creating directory structure, manifest, and persona files."""
    topic = input_data.get("topic")
    participants_personas = input_data.get("participants_personas")

    if not topic or not participants_personas:
        return {
            "debate_id": None,
            "error": "Missing topic or participants_personas data.",
        }

    try:
        # Determine base path for debates from config
        debates_base_dir = Path(config.paths.agent_comms) / "debates"
        debates_base_dir.mkdir(parents=True, exist_ok=True)
    except AttributeError:
        logger.error("Config missing paths.agent_comms for debate creation.")
        return {"debate_id": None, "error": "Configuration path missing."}
    except Exception as e:
        logger.error(f"Error creating base debates directory: {e}", exc_info=True)
        return {"debate_id": None, "error": f"Failed to create base directory: {e}"}

    # Generate unique debate ID
    debate_id = str(uuid4())
    debate_dir = debates_base_dir / debate_id
    lock_path = debate_dir / "manifest.lock"  # Lock for manifest creation/update

    try:
        # Create debate directory structure
        debate_dir.mkdir(exist_ok=False)  # Fail if exists
        personas_dir = debate_dir / "personas"
        personas_dir.mkdir()
        transcript_dir = debate_dir / "transcript"
        transcript_dir.mkdir()
        logger.info(f"Created debate directory structure: {debate_dir}")

        # Create Persona objects and files
        participant_info_list: List[DebateParticipantInfo] = []
        all_agent_ids = set()
        for persona_input in participants_personas:
            target_agent_id = persona_input.get("agent_id")
            if not target_agent_id:
                logger.warning("Skipping persona input with missing agent_id.")
                continue

            persona = Persona(debate_id=debate_id, **persona_input)
            persona_filename = (
                f"{target_agent_id}_persona.json"  # Store as JSON for easier parsing
            )
            persona_filepath = personas_dir / persona_filename
            try:
                with open(persona_filepath, "w", encoding="utf-8") as f:
                    json.dump(persona.model_dump(mode="json"), f, indent=2)
                logger.info(
                    f"Created persona file for agent {target_agent_id}: {persona_filename}"
                )
                participant_info_list.append(
                    DebateParticipantInfo(
                        agent_id=target_agent_id,
                        role_name=persona.role_name,
                        persona_id=persona.persona_id,
                        status="invited",  # Initial status
                    )
                )
                all_agent_ids.add(target_agent_id)
            except Exception as p_write_e:
                logger.error(
                    f"Failed to write persona file for {target_agent_id}: {p_write_e}"
                )
                # Continue creating other personas, but debate might be incomplete

        # Create Manifest data
        manifest = DebateManifest(
            debate_id=debate_id,
            topic=topic,
            proposal_ref=input_data.get("proposal_ref"),
            creator_agent_id=agent_id,
            protocol_id=input_data.get("protocol_id", "v1_simple_turn_based"),
            moderator_agent_id=input_data.get("moderator_agent_id"),
            participants=participant_info_list,
            # next_agent_id can be set based on protocol (e.g., first participant)
            next_agent_id=participant_info_list[0].agent_id
            if participant_info_list
            else None,
        )

        # Write manifest using lock
        manifest_path = debate_dir / "manifest.json"
        lock = FileLock(lock_path, timeout=5)
        with lock:
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest.model_dump(mode="json"), f, indent=2)
        logger.info(f"Created debate manifest: {manifest_path}")

        # TODO: Dispatch DEBATE_CREATED event
        # TODO: Send invitations/persona details to participating agents

        return {"debate_id": debate_id, "error": None}

    except FileExistsError:
        logger.error(f"Debate directory already exists: {debate_dir}")
        return {"debate_id": None, "error": "Debate ID collision (rare)."}
    except Timeout:
        logger.error(f"Failed to acquire lock for manifest {manifest_path}")
        return {"debate_id": None, "error": "Failed to acquire manifest lock."}
    except Exception as e:
        logger.error(f"Failed to create debate {debate_id}: {e}", exc_info=True)
        # Attempt cleanup?
        # shutil.rmtree(debate_dir, ignore_errors=True)
        return {"debate_id": None, "error": f"Failed to create debate structure: {e}"}
    finally:
        # Clean up lock file if it exists
        if lock_path and lock_path.exists():
            try:
                lock_path.unlink()
            except OSError:
                pass  # Ignore cleanup errors


# --- Capability Definitions (for registration) --- #

DEBATE_INITIATE_CAPABILITY_ID = "debate.initiate"
DEBATE_INITIATE_CAPABILITY_INFO = {
    "capability_id": DEBATE_INITIATE_CAPABILITY_ID,
    "capability_name": "Initiate Debate",
    "description": "Creates a new debate arena, assigning topic, participants, and personas.",
    "parameters": DebateInitiateInput.__annotations__,
    "output_schema": DebateInitiateOutput.__annotations__,
    "handler_info": {
        "type": "function",
        "path": "dreamos.core.agents.capabilities.library.debate_management.debate_initiate_capability",
    },
}

# ... other capability infos ...
