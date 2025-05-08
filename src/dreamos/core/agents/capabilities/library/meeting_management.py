# src/dreamos/core/agents/capabilities/library/meeting_management.py
import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, TypedDict
from uuid import uuid4

# --- BEGIN EDIT: Import Mailbox Utils (Conceptual) ---
# Assuming mailbox utils exist at this path
from dreamos.core.comms.mailbox_utils import create_and_send_message  # Assumed function

# Import schemas
from dreamos.core.comms.meeting_schemas import (
    BaseMeetingMessage,
    MeetingAgendaItem,
    MeetingComment,
    MeetingManifest,
    MeetingProposal,
    MeetingStateChange,
    MeetingSummary,
    MeetingVote,
)

# Assuming access to config for paths
from dreamos.core.config import AppConfig
from dreamos.core.coordination.agent_bus import AgentBus, BaseEvent
from dreamos.core.coordination.event_payloads import (
    AgentJoinedMeetingPayload,
    MeetingCreatedPayload,
    NewMessageInMeetingPayload,
)
from dreamos.core.coordination.event_types import EventType
from filelock import FileLock, Timeout
from pydantic import BaseModel, ValidationError

# --- END EDIT: Import Mailbox Utils ---

logger = logging.getLogger(__name__)

# --- Capability Input/Output Schemas --- #


class MeetingCreateInput(TypedDict):
    topic: str
    goal: Optional[str]
    initial_participants: List[str]  # List of agent IDs to invite
    facilitator_agent_id: Optional[str]


class MeetingCreateOutput(TypedDict):
    meeting_id: Optional[str]
    error: Optional[str]


class MeetingPostMessageInput(TypedDict):
    meeting_id: str
    message_type: Literal[
        "comment", "proposal", "vote", "summary", "state_change", "agenda_item"
    ]
    message_data: Dict[str, Any]  # Data specific to the message type


class MeetingPostMessageOutput(TypedDict):
    message_id: Optional[str]
    error: Optional[str]


class MeetingReadMessagesInput(TypedDict, total=False):
    meeting_id: str
    # Filtering options (optional)
    message_type: Optional[str]
    agent_id: Optional[str]
    since_timestamp_utc: Optional[str]
    limit: Optional[int]


class MeetingReadMessagesOutput(TypedDict):
    messages: List[Dict[str, Any]]
    error: Optional[str]


class MeetingGetInfoInput(TypedDict):
    meeting_id: str


class MeetingGetInfoOutput(TypedDict):
    manifest: Optional[Dict[str, Any]]
    error: Optional[str]


class MeetingJoinInput(TypedDict):
    meeting_id: str


class MeetingJoinOutput(TypedDict):
    success: bool
    message: Optional[str]
    error: Optional[str]


class MeetingVoteInput(TypedDict):
    meeting_id: str
    proposal_id: str
    vote_value: Literal["yes", "no", "abstain"]
    rationale: Optional[str]


class MeetingVoteOutput(TypedDict):
    message_id: Optional[str]  # ID of the created vote message
    error: Optional[str]


# --- BEGIN EDIT: Add UpdateState Schemas ---
class MeetingUpdateStateInput(TypedDict):
    meeting_id: str
    new_state: Literal["open", "discussion", "voting", "closed", "archived"]
    reason: Optional[str]


class MeetingUpdateStateOutput(TypedDict):
    success: bool
    old_state: Optional[str]
    new_state: Optional[str]
    error: Optional[str]


# --- END EDIT: Add UpdateState Schemas ---


# --- BEGIN EDIT: Add Discover Schemas ---
class MeetingDiscoverInput(TypedDict, total=False):
    # Optional filters
    state: Optional[Literal["open", "discussion", "voting", "closed", "archived"]]
    creator_agent_id: Optional[str]
    # Could add participant filter later if needed


class MeetingDiscoverOutput(TypedDict):
    meetings: List[Dict[str, Any]]  # List of meeting manifests
    error: Optional[str]


# --- END EDIT: Add Discover Schemas ---

# Add other input/output schemas for other capabilities later...
# class MeetingPostMessageInput(TypedDict): ...
# class MeetingReadMessagesInput(TypedDict): ...
# etc.

# --- Pydantic Models for Meeting Structure ---


class MeetingParticipant(BaseModel):
    agent_id: str
    role: str  # e.g., 'initiator', 'participant', 'observer'


class MeetingAgendaItem(BaseModel):
    topic: str
    proposer: str  # agent_id
    notes: Optional[str] = None


class MeetingLogEntry(BaseModel):
    timestamp: str
    agent_id: str
    message: str


class MeetingSchema(BaseModel):
    meeting_id: str
    topic: str
    created_at: str
    status: str  # e.g., 'scheduled', 'active', 'concluded', 'cancelled'
    initiator: str  # agent_id
    participants: List[MeetingParticipant]
    agenda: List[MeetingAgendaItem]
    log: List[MeetingLogEntry]
    summary: Optional[str] = None


# --- Capability Implementations --- #


def meeting_create_capability(
    input_data: MeetingCreateInput,
    agent_id: str,  # ID of the agent calling the capability
    config: AppConfig,
    agent_bus: AgentBus,
) -> MeetingCreateOutput:
    """Creates a new meeting directory structure and manifest."""
    topic = input_data.get("topic")
    if not topic:
        return {"meeting_id": None, "error": "Meeting topic is required."}

    initial_participants = input_data.get("initial_participants", [])
    goal = input_data.get("goal")
    facilitator = input_data.get("facilitator_agent_id")

    try:
        # Determine base path for meetings from config
        meetings_base_dir = Path(config.paths.agent_comms) / "meetings"
        meetings_base_dir.mkdir(parents=True, exist_ok=True)
    except AttributeError:
        logger.error("Config missing paths.agent_comms for meeting creation.")
        return {"meeting_id": None, "error": "Configuration path missing."}
    except Exception as e:
        logger.error(f"Error creating base meetings directory: {e}", exc_info=True)
        return {"meeting_id": None, "error": f"Failed to create base directory: {e}"}

    # Generate a unique meeting ID (UUID for now)
    meeting_id = str(uuid4())
    meeting_dir = meetings_base_dir / meeting_id
    lock_path = meeting_dir / "manifest.lock"

    try:
        # Create meeting directory structure
        meeting_dir.mkdir(exist_ok=False)  # Fail if directory already exists
        (meeting_dir / "messages").mkdir()
        logger.info(f"Created meeting directory: {meeting_dir}")

        # Create manifest data
        manifest = MeetingManifest(
            meeting_id=meeting_id,
            topic=topic,
            goal=goal,
            creator_agent_id=agent_id,
            facilitator_agent_id=facilitator,
            # Timestamps default in model
        )

        # Write manifest.json
        manifest_path = meeting_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest.model_dump(mode="json"), f, indent=2)
        logger.info(f"Created meeting manifest: {manifest_path}")

        # Create participants.json (initial state)
        participants_data = [
            {"agent_id": p_id, "status": "invited"} for p_id in initial_participants
        ]
        # Add creator if not already invited
        if agent_id not in initial_participants:
            participants_data.append(
                {"agent_id": agent_id, "status": "joined"}
            )  # Creator joins automatically
        participants_path = meeting_dir / "participants.json"
        with open(participants_path, "w", encoding="utf-8") as f:
            json.dump(participants_data, f, indent=2)
        logger.info(f"Created participants file: {participants_path}")

        # Dispatch MEETING_CREATED event via AgentBus
        try:
            payload = MeetingCreatedPayload(
                meeting_id=meeting_id,
                creator_agent_id=agent_id,
                topic=manifest.topic,
                initial_participants=[
                    p["agent_id"] for p in participants_data if p["status"] == "invited"
                ],
            )
            event = BaseEvent(
                event_type=EventType.MEETING_CREATED,
                source_id=agent_id,  # Or capability ID?
                data=payload.model_dump(mode="json"),
            )
            # Assuming agent_bus has an async dispatch method
            # This might need to run in an executor if capability itself isn't async
            # For now, assume direct call works or needs adaptation later.
            asyncio.run(
                agent_bus.dispatch_event(event)
            )  # Or await if capability is async
            logger.info(f"Dispatched MEETING_CREATED event for meeting {meeting_id}.")
        except Exception as bus_e:
            logger.error(
                f"Failed to dispatch MEETING_CREATED event: {bus_e}", exc_info=True
            )
            # Continue with meeting creation, but log the dispatch failure

        # --- BEGIN EDIT: Send Mailbox Invitations --- #
        logger.info(
            f"Sending invitations to {len(initial_participants)} participants..."
        )
        invitation_subject = f"Meeting Invitation: {manifest.topic}"
        invitation_body = {
            "meeting_id": meeting_id,
            "topic": manifest.topic,
            "goal": manifest.goal,
            "creator": agent_id,
            "message": f"You are invited to join meeting {meeting_id} on topic: {manifest.topic}. Use capability meeting.join.",
        }
        invitation_type = "MEETING_INVITATION"  # Standardize this type

        successful_invites = 0
        failed_invites = []
        for participant_id in initial_participants:
            if participant_id == agent_id:  # Don't invite self
                continue
            try:
                # Use the assumed mailbox utility function
                send_success = create_and_send_message(
                    recipient_agent_id=participant_id,
                    sender_agent_id=agent_id,
                    subject=invitation_subject,
                    body=invitation_body,
                    msg_type=invitation_type,
                    config=config,  # Assuming function needs config for paths
                )
                if send_success:
                    successful_invites += 1
                else:
                    failed_invites.append(participant_id)
                    logger.warning(
                        f"Failed to send invitation message to {participant_id} for meeting {meeting_id}. Function returned False."
                    )
            except Exception as mail_e:
                failed_invites.append(participant_id)
                logger.error(
                    f"Error sending invitation message to {participant_id} for meeting {meeting_id}: {mail_e}",
                    exc_info=True,
                )

        logger.info(f"Sent {successful_invites} invitations successfully.")
        if failed_invites:
            logger.error(
                f"Failed to send invitations to {len(failed_invites)} agents: {', '.join(failed_invites)}"
            )
            # Note: Meeting is still created, but some agents weren't notified via mailbox.
        # --- END EDIT: Send Mailbox Invitations --- #

        return {"meeting_id": meeting_id, "error": None}

    except FileExistsError:
        logger.error(f"Meeting directory already exists: {meeting_dir}")
        return {"meeting_id": None, "error": "Meeting ID collision (rare)."}
    except Exception as e:
        logger.error(f"Failed to create meeting {meeting_id}: {e}", exc_info=True)
        # Attempt cleanup?
        # shutil.rmtree(meeting_dir, ignore_errors=True)
        return {"meeting_id": None, "error": f"Failed to create meeting structure: {e}"}


def meeting_post_message_capability(
    input_data: MeetingPostMessageInput,
    agent_id: str,
    config: AppConfig,
    agent_bus: AgentBus,
) -> MeetingPostMessageOutput:
    """Posts a new message to the specified meeting's messages directory."""
    meeting_id = input_data.get("meeting_id")
    message_type = input_data.get("message_type")
    message_data = input_data.get("message_data")

    if not all([meeting_id, message_type, message_data]):
        return {
            "message_id": None,
            "error": "Missing meeting_id, message_type, or message_data.",
        }

    try:
        # Determine meeting path
        meetings_base_dir = Path(config.paths.agent_comms) / "meetings"
        meeting_dir = meetings_base_dir / meeting_id
        messages_dir = meeting_dir / "messages"

        if not messages_dir.is_dir():
            logger.error(f"Meeting messages directory not found: {messages_dir}")
            return {
                "message_id": None,
                "error": f"Meeting {meeting_id} not found or messages directory missing.",
            }

        # Construct the specific message model based on type
        message_model: Optional[BaseMeetingMessage] = None
        common_data = {"meeting_id": meeting_id, "agent_id": agent_id}

        # Use Pydantic models for validation and structure
        if message_type == "comment":
            message_model = MeetingComment(**common_data, **message_data)
        elif message_type == "proposal":
            message_model = MeetingProposal(**common_data, **message_data)
        elif message_type == "vote":
            message_model = MeetingVote(**common_data, **message_data)
        elif message_type == "summary":
            message_model = MeetingSummary(**common_data, **message_data)
        elif message_type == "state_change":
            message_model = MeetingStateChange(**common_data, **message_data)
        elif message_type == "agenda_item":
            message_model = MeetingAgendaItem(**common_data, **message_data)
        else:
            return {
                "message_id": None,
                "error": f"Unsupported message type: {message_type}",
            }

        # Generate filename
        timestamp_str = (
            message_model.timestamp_utc.replace(":", "")
            .replace("-", "")
            .replace(".", "")
        )
        safe_agent_id = "".join(c for c in agent_id if c.isalnum() or c == "-")[:20]
        message_filename = f"msg_{timestamp_str}_{safe_agent_id}_{message_type}.json"
        message_filepath = messages_dir / message_filename

        # Write message file
        with open(message_filepath, "w", encoding="utf-8") as f:
            json.dump(message_model.model_dump(mode="json"), f, indent=2)

        logger.info(
            f"Posted message {message_model.message_id} to meeting {meeting_id} ({message_type}). File: {message_filename}"
        )

        # Dispatch NEW_MESSAGE_IN_MEETING event via AgentBus
        try:
            payload = NewMessageInMeetingPayload(
                meeting_id=meeting_id,
                message_id=message_model.message_id,
                message_type=message_type,
                sender_agent_id=agent_id,
            )
            event = BaseEvent(
                event_type=EventType.NEW_MESSAGE_IN_MEETING,
                source_id=agent_id,
                data=payload.model_dump(mode="json"),
            )
            asyncio.run(agent_bus.dispatch_event(event))
            logger.info(
                f"Dispatched NEW_MESSAGE_IN_MEETING event for message {message_model.message_id}."
            )
        except Exception as bus_e:
            logger.error(
                f"Failed to dispatch NEW_MESSAGE_IN_MEETING event: {bus_e}",
                exc_info=True,
            )

        return {"message_id": message_model.message_id, "error": None}

    except ValidationError as e:
        logger.error(f"Invalid message data for type {message_type}: {e}")
        return {"message_id": None, "error": f"Invalid message data: {e}"}
    except AttributeError:
        logger.error("Config missing paths.agent_comms for posting message.")
        return {"message_id": None, "error": "Configuration path missing."}
    except Exception as e:
        logger.error(
            f"Failed to post message to meeting {meeting_id}: {e}", exc_info=True
        )
        return {"message_id": None, "error": f"Failed to post message: {e}"}


def meeting_read_messages_capability(
    input_data: MeetingReadMessagesInput,
    # agent_id: str, # Requesting agent - not needed for read
    config: AppConfig,
) -> MeetingReadMessagesOutput:
    """Reads messages from a specified meeting, with optional filtering."""
    meeting_id = input_data.get("meeting_id")
    if not meeting_id:
        return {"messages": [], "error": "Missing meeting_id."}

    # Get filter parameters
    filter_type = input_data.get("message_type")
    filter_agent = input_data.get("agent_id")
    filter_since = input_data.get("since_timestamp_utc")
    limit = input_data.get("limit")

    messages = []
    try:
        # Determine meeting path
        meetings_base_dir = Path(config.paths.agent_comms) / "meetings"
        meeting_dir = meetings_base_dir / meeting_id
        messages_dir = meeting_dir / "messages"

        if not messages_dir.is_dir():
            logger.warning(f"Meeting messages directory not found: {messages_dir}")
            # Return empty list, not necessarily an error if meeting just created
            return {"messages": [], "error": None}

        # List message files, sort by name (which includes timestamp)
        # Use reversed to get newest first potentially, or sort later
        message_files = sorted(messages_dir.glob("msg_*.json"), reverse=True)

        # Parse since_timestamp if provided
        since_dt: Optional[datetime] = None
        if filter_since:
            try:
                since_dt = datetime.fromisoformat(filter_since.replace("Z", "+00:00"))
            except ValueError:
                logger.warning(f"Invalid since_timestamp_utc format: {filter_since}")
                return {
                    "messages": [],
                    "error": "Invalid timestamp format for filtering.",
                }

        # Iterate, load, filter messages
        count = 0
        for msg_file in message_files:
            try:
                with open(msg_file, "r", encoding="utf-8") as f:
                    msg_data = json.load(f)

                # --- Apply Filters --- #
                # Type filter
                if filter_type and msg_data.get("message_type") != filter_type:
                    continue
                # Agent filter
                if filter_agent and msg_data.get("agent_id") != filter_agent:
                    continue
                # Timestamp filter
                if since_dt:
                    msg_ts_str = msg_data.get("timestamp_utc")
                    try:
                        msg_dt = datetime.fromisoformat(
                            msg_ts_str.replace("Z", "+00:00")
                        )
                        if msg_dt < since_dt:
                            continue  # Skip messages older than filter
                    except (TypeError, ValueError):
                        logger.warning(
                            f"Could not parse timestamp in message file {msg_file.name}, skipping for time filter."
                        )
                        continue

                # If all filters pass, add to results
                messages.append(msg_data)
                count += 1

                # Limit filter
                if limit is not None and count >= limit:
                    break  # Stop reading once limit is reached

            except json.JSONDecodeError:
                logger.error(
                    f"Failed to decode JSON from message file: {msg_file.name}"
                )
            except Exception as e:
                logger.error(
                    f"Error processing message file {msg_file.name}: {e}", exc_info=True
                )

        # Return messages in chronological order (oldest first)
        messages.reverse()
        logger.info(f"Read {len(messages)} messages from meeting {meeting_id}.")
        return {"messages": messages, "error": None}

    except AttributeError:
        logger.error("Config missing paths.agent_comms for reading messages.")
        return {"messages": [], "error": "Configuration path missing."}
    except Exception as e:
        logger.error(
            f"Failed to read messages from meeting {meeting_id}: {e}", exc_info=True
        )
        return {"messages": [], "error": f"Failed to read messages: {e}"}


def meeting_get_info_capability(
    input_data: MeetingGetInfoInput,
    # agent_id: str, # Requesting agent - not needed
    config: AppConfig,
) -> MeetingGetInfoOutput:
    """Retrieves the manifest metadata for a specified meeting."""
    meeting_id = input_data.get("meeting_id")
    if not meeting_id:
        return {"manifest": None, "error": "Missing meeting_id."}

    try:
        # Determine meeting path
        meetings_base_dir = Path(config.paths.agent_comms) / "meetings"
        meeting_dir = meetings_base_dir / meeting_id
        manifest_path = meeting_dir / "manifest.json"

        if not manifest_path.is_file():
            logger.warning(f"Meeting manifest not found: {manifest_path}")
            return {
                "manifest": None,
                "error": f"Meeting {meeting_id} manifest not found.",
            }

        # Read and parse manifest
        # TODO: Add file lock for reading if manifest can be updated concurrently?
        # For now, assume read is safe enough or updates are infrequent/atomic enough.
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        # Optional: Validate against Pydantic model?
        # try:
        #     MeetingManifest.model_validate(manifest_data)
        # except ValidationError as e:
        #     logger.error(f"Invalid manifest format for meeting {meeting_id}: {e}")
        #     return {"manifest": None, "error": "Invalid meeting manifest format."}

        logger.info(f"Retrieved manifest for meeting {meeting_id}.")
        return {"manifest": manifest_data, "error": None}

    except AttributeError:
        logger.error("Config missing paths.agent_comms for getting meeting info.")
        return {"manifest": None, "error": "Configuration path missing."}
    except json.JSONDecodeError:
        logger.error(f"Failed to decode JSON from manifest file: {manifest_path}")
        return {"manifest": None, "error": "Failed to parse meeting manifest."}
    except Exception as e:
        logger.error(f"Failed to get info for meeting {meeting_id}: {e}", exc_info=True)
        return {"manifest": None, "error": f"Failed to get meeting info: {e}"}


def meeting_join_capability(
    input_data: MeetingJoinInput, agent_id: str, config: AppConfig, agent_bus: AgentBus
) -> MeetingJoinOutput:
    """Allows an agent to join a meeting by updating participants.json."""
    meeting_id = input_data.get("meeting_id")
    if not meeting_id:
        return {"success": False, "message": None, "error": "Missing meeting_id."}

    lock_path = None
    try:
        # Determine paths
        meetings_base_dir = Path(config.paths.agent_comms) / "meetings"
        meeting_dir = meetings_base_dir / meeting_id
        participants_path = meeting_dir / "participants.json"
        lock_path = meeting_dir / "participants.lock"  # Lock file for participants.json

        if not meeting_dir.is_dir():
            logger.error(f"Meeting directory not found: {meeting_dir}")
            return {
                "success": False,
                "message": None,
                "error": f"Meeting {meeting_id} not found.",
            }

        # Acquire lock for reading/writing participants file
        lock = FileLock(lock_path, timeout=5)  # 5 second timeout
        with lock:
            participants_data = []
            if participants_path.is_file():
                try:
                    with open(participants_path, "r", encoding="utf-8") as f:
                        participants_data = json.load(f)
                except json.JSONDecodeError:
                    logger.error(
                        f"Failed to decode participants file: {participants_path}"
                    )
                    return {
                        "success": False,
                        "message": None,
                        "error": "Failed to parse participants file.",
                    }
            else:
                logger.warning(
                    f"Participants file not found, creating: {participants_path}"
                )
                # Allow join even if file missing initially?

            # Find agent and update status
            agent_found = False
            updated = False
            for participant in participants_data:
                if participant.get("agent_id") == agent_id:
                    agent_found = True
                    if participant.get("status") != "joined":
                        participant["status"] = "joined"
                        participant["joined_at_utc"] = datetime.now(
                            timezone.utc
                        ).isoformat()
                        updated = True
                    break  # Agent found

            # If agent wasn't in the list initially (e.g., not pre-invited)
            if not agent_found:
                # Optionally check manifest if only invited agents can join?
                # For now, allow any agent to join
                participants_data.append(
                    {
                        "agent_id": agent_id,
                        "status": "joined",
                        "joined_at_utc": datetime.now(timezone.utc).isoformat(),
                    }
                )
                updated = True

            if updated:
                # Write the updated data back to file
                try:
                    with open(participants_path, "w", encoding="utf-8") as f:
                        json.dump(participants_data, f, indent=2)
                    logger.info(
                        f"Agent {agent_id} successfully joined meeting {meeting_id}."
                    )

                    # Dispatch AGENT_JOINED_MEETING event via AgentBus
                    try:
                        payload = AgentJoinedMeetingPayload(
                            meeting_id=meeting_id, agent_id=agent_id
                        )
                        event = BaseEvent(
                            event_type=EventType.AGENT_JOINED_MEETING,
                            source_id=agent_id,
                            data=payload.model_dump(mode="json"),
                        )
                        asyncio.run(agent_bus.dispatch_event(event))
                        logger.info(
                            f"Dispatched AGENT_JOINED_MEETING event for agent {agent_id} in meeting {meeting_id}."
                        )
                    except Exception as bus_e:
                        logger.error(
                            f"Failed to dispatch AGENT_JOINED_MEETING event: {bus_e}",
                            exc_info=True,
                        )

                    return {
                        "success": True,
                        "message": f"Successfully joined meeting {meeting_id}.",
                        "error": None,
                    }
                except Exception as write_e:
                    logger.error(
                        f"Failed to write updated participants file: {write_e}"
                    )
                    # State might be inconsistent now!
                    return {
                        "success": False,
                        "message": None,
                        "error": "Failed to save participant update.",
                    }
            else:
                logger.info(
                    f"Agent {agent_id} already marked as joined in meeting {meeting_id}."
                )
                return {
                    "success": True,
                    "message": "Agent already joined.",
                    "error": None,
                }

    except Timeout:
        logger.error(
            f"Failed to acquire lock for {participants_path} for agent {agent_id} joining meeting {meeting_id}"
        )
        return {
            "success": False,
            "message": None,
            "error": "Failed to acquire participant file lock.",
        }
    except AttributeError:
        logger.error("Config missing paths.agent_comms for joining meeting.")
        return {
            "success": False,
            "message": None,
            "error": "Configuration path missing.",
        }
    except Exception as e:
        logger.error(
            f"Failed to process join request for agent {agent_id} in meeting {meeting_id}: {e}",
            exc_info=True,
        )
        return {
            "success": False,
            "message": None,
            "error": f"Failed to process join request: {e}",
        }
    finally:
        # Clean up lock file if it exists and wasn't released (though context manager should handle)
        if lock_path and lock_path.exists():
            try:
                lock_path.unlink()
            except OSError:
                pass  # Ignore cleanup errors


def meeting_vote_capability(
    input_data: MeetingVoteInput,
    agent_id: str,  # ID of the agent voting
    config: AppConfig,
) -> MeetingVoteOutput:
    """Allows an agent to cast a vote on a meeting proposal by posting a vote message."""
    meeting_id = input_data.get("meeting_id")
    proposal_id = input_data.get("proposal_id")
    vote_value = input_data.get("vote_value")

    if not all([meeting_id, proposal_id, vote_value]):
        return {
            "message_id": None,
            "error": "Missing meeting_id, proposal_id, or vote_value.",
        }

    # Construct the message data for the post_message capability
    vote_message_data = {
        "proposal_id": proposal_id,
        "vote_value": vote_value,
        "rationale": input_data.get("rationale"),  # Pass rationale if provided
    }

    post_message_input = MeetingPostMessageInput(
        meeting_id=meeting_id, message_type="vote", message_data=vote_message_data
    )

    # Call the existing post_message capability
    # Note: This assumes capabilities can call each other directly, or
    # that this logic exists within an agent that can call capabilities.
    # For now, call the function directly for simplicity.
    try:
        result = meeting_post_message_capability(
            input_data=post_message_input, agent_id=agent_id, config=config
        )
        if result.get("error"):
            logger.error(
                f"Error posting vote message for agent {agent_id} on proposal {proposal_id}: {result['error']}"
            )
            return {
                "message_id": None,
                "error": f"Failed to post vote message: {result['error']}",
            }
        else:
            logger.info(
                f"Agent {agent_id} successfully voted on proposal {proposal_id} in meeting {meeting_id}."
            )
            return {"message_id": result.get("message_id"), "error": None}

    except Exception as e:
        logger.error(
            f"Unexpected error casting vote for agent {agent_id} on proposal {proposal_id}: {e}",
            exc_info=True,
        )
        return {"message_id": None, "error": f"Unexpected error during voting: {e}"}


# --- BEGIN EDIT: Add update_state Capability --- #
def meeting_update_state_capability(
    input_data: MeetingUpdateStateInput,
    agent_id: str,  # Agent initiating the state change
    config: AppConfig,
    agent_bus: AgentBus,
) -> MeetingUpdateStateOutput:
    """Updates the state of a meeting manifest and logs the change."""
    meeting_id = input_data.get("meeting_id")
    new_state = input_data.get("new_state")
    reason = input_data.get("reason")

    if not meeting_id or not new_state:
        return {
            "success": False,
            "old_state": None,
            "new_state": None,
            "error": "Missing meeting_id or new_state.",
        }

    try:
        meetings_base_dir = Path(config.paths.agent_comms) / "meetings"
        meeting_dir = meetings_base_dir / meeting_id
        manifest_path = meeting_dir / "manifest.json"
        lock_path = manifest_path.with_suffix(".lock")  # Lock file next to manifest

        if not manifest_path.is_file():
            return {
                "success": False,
                "old_state": None,
                "new_state": None,
                "error": f"Meeting manifest not found: {manifest_path}",
            }

        old_state = None
        lock = FileLock(lock_path, timeout=5)  # 5 second timeout

        with lock:
            # Read current manifest
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
                old_state = manifest_data.get("current_state")

            if old_state == new_state:
                logger.warning(
                    f"Meeting {meeting_id} already in state '{new_state}'. No change made."
                )
                return {
                    "success": True,
                    "old_state": old_state,
                    "new_state": new_state,
                    "error": None,
                }

            # Update manifest data
            manifest_data["current_state"] = new_state
            manifest_data["last_updated_utc"] = datetime.now(timezone.utc).isoformat()

            # Validate with Pydantic before writing (optional but recommended)
            try:
                MeetingManifest(**manifest_data)
            except Exception as pydantic_e:
                logger.error(
                    f"Updated manifest data failed validation for {meeting_id}: {pydantic_e}"
                )
                return {
                    "success": False,
                    "old_state": old_state,
                    "new_state": None,
                    "error": f"Internal error: Updated manifest data invalid: {pydantic_e}",
                }

            # Write updated manifest
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, indent=2)

        logger.info(
            f"Updated meeting {meeting_id} state from '{old_state}' to '{new_state}'."
        )

        # Post a state change message
        state_change_msg = MeetingStateChange(
            meeting_id=meeting_id,
            agent_id=agent_id,
            old_state=old_state or "unknown",
            new_state=new_state,
            reason=reason,
        )
        post_input = {
            "meeting_id": meeting_id,
            "message_type": "state_change",
            "message_data": state_change_msg.model_dump(mode="json"),
        }
        post_result = meeting_post_message_capability(
            post_input, agent_id, config, agent_bus
        )
        if post_result.get("error"):
            logger.error(
                f"Failed to post state change message for meeting {meeting_id}: {post_result['error']}"
            )
            # Continue even if message posting fails, but log it

        # Dispatch MEETING_STATE_CHANGED event (Define payload if needed)
        try:
            # Example payload - adjust as needed
            payload_dict = {
                "meeting_id": meeting_id,
                "changer_agent_id": agent_id,
                "old_state": old_state,
                "new_state": new_state,
                "reason": reason,
            }
            event = BaseEvent(
                event_type=EventType.MEETING_STATE_CHANGED,  # Assumes this exists
                source_id=agent_id,
                data=payload_dict,
            )
            asyncio.run(agent_bus.dispatch_event(event))
            logger.info(
                f"Dispatched MEETING_STATE_CHANGED event for meeting {meeting_id}."
            )
        except AttributeError:
            logger.warning("EventType.MEETING_STATE_CHANGED not defined?")
        except Exception as bus_e:
            logger.error(
                f"Failed to dispatch MEETING_STATE_CHANGED event: {bus_e}",
                exc_info=True,
            )

        return {
            "success": True,
            "old_state": old_state,
            "new_state": new_state,
            "error": None,
        }

    except Timeout:
        logger.error(f"Timeout acquiring lock for meeting manifest {manifest_path}")
        return {
            "success": False,
            "old_state": None,
            "new_state": None,
            "error": "Failed to acquire lock.",
        }
    except Exception as e:
        logger.error(
            f"Error updating meeting state for {meeting_id}: {e}", exc_info=True
        )
        return {
            "success": False,
            "old_state": None,
            "new_state": None,
            "error": f"Error updating state: {e}",
        }


# --- END EDIT: Add update_state Capability --- #


# --- BEGIN EDIT: Add discover Capability --- #
def meeting_discover_capability(
    input_data: MeetingDiscoverInput,
    # agent_id: str, # Requesting agent - not needed for discovery
    config: AppConfig,
) -> MeetingDiscoverOutput:
    """Discovers meetings by scanning the meetings directory and reading manifests."""
    discovered_meetings = []
    filter_state = input_data.get("state")
    filter_creator = input_data.get("creator_agent_id")

    try:
        meetings_base_dir = Path(config.paths.agent_comms) / "meetings"
        if not meetings_base_dir.is_dir():
            logger.warning(f"Meetings base directory not found: {meetings_base_dir}")
            return {"meetings": [], "error": "Meetings directory not found."}

        logger.info(f"Scanning for meetings in {meetings_base_dir}...")
        for item in meetings_base_dir.iterdir():
            if item.is_dir():
                meeting_id = item.name
                manifest_path = item / "manifest.json"
                if manifest_path.is_file():
                    try:
                        with open(manifest_path, "r", encoding="utf-8") as f:
                            manifest_data = json.load(f)

                        # Apply filters
                        if (
                            filter_state
                            and manifest_data.get("current_state") != filter_state
                        ):
                            continue
                        if (
                            filter_creator
                            and manifest_data.get("creator_agent_id") != filter_creator
                        ):
                            continue

                        # Optionally validate with Pydantic
                        # MeetingManifest(**manifest_data)
                        discovered_meetings.append(manifest_data)
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in manifest: {manifest_path}")
                    except Exception as read_e:
                        logger.warning(
                            f"Error reading manifest {manifest_path}: {read_e}"
                        )
                else:
                    logger.debug(f"No manifest found in directory: {item}")

        logger.info(f"Discovered {len(discovered_meetings)} meetings.")
        return {"meetings": discovered_meetings, "error": None}

    except AttributeError:
        logger.error("Config missing paths.agent_comms for meeting discovery.")
        return {"meetings": [], "error": "Configuration path missing."}
    except Exception as e:
        logger.error(f"Error during meeting discovery: {e}", exc_info=True)
        return {"meetings": [], "error": f"Error during discovery: {e}"}


# --- END EDIT: Add discover Capability --- #

# --- Capability Definitions (for registration) --- #

MEETING_CREATE_CAPABILITY_ID = "meeting.create"
MEETING_CREATE_CAPABILITY_INFO = {
    "capability_id": MEETING_CREATE_CAPABILITY_ID,
    "capability_name": "Create Meeting",
    "description": "Initiates a new agent meeting, creating the necessary structure and inviting participants.",
    "parameters": MeetingCreateInput.__annotations__,  # Use TypedDict annotations
    "output_schema": MeetingCreateOutput.__annotations__,
    # Handler info depends on how capabilities are invoked (e.g., direct function call, agent method)
    "handler_info": {
        "type": "function",
        "path": "dreamos.core.agents.capabilities.library.meeting_management.meeting_create_capability",
    },
}

MEETING_POST_MESSAGE_CAPABILITY_ID = "meeting.post_message"
MEETING_POST_MESSAGE_CAPABILITY_INFO = {
    "capability_id": MEETING_POST_MESSAGE_CAPABILITY_ID,
    "capability_name": "Post Meeting Message",
    "description": "Posts a message (comment, proposal, vote, etc.) to a specified meeting.",
    "parameters": MeetingPostMessageInput.__annotations__,
    "output_schema": MeetingPostMessageOutput.__annotations__,
    "handler_info": {
        "type": "function",
        "path": "dreamos.core.agents.capabilities.library.meeting_management.meeting_post_message_capability",
    },
}

MEETING_READ_MESSAGES_CAPABILITY_ID = "meeting.read_messages"
MEETING_READ_MESSAGES_CAPABILITY_INFO = {
    "capability_id": MEETING_READ_MESSAGES_CAPABILITY_ID,
    "capability_name": "Read Meeting Messages",
    "description": "Reads messages from a specified meeting, with optional filtering by type, agent, timestamp, or limit.",
    "parameters": MeetingReadMessagesInput.__annotations__,
    "output_schema": MeetingReadMessagesOutput.__annotations__,
    "handler_info": {
        "type": "function",
        "path": "dreamos.core.agents.capabilities.library.meeting_management.meeting_read_messages_capability",
    },
}

MEETING_GET_INFO_CAPABILITY_ID = "meeting.get_info"
MEETING_GET_INFO_CAPABILITY_INFO = {
    "capability_id": MEETING_GET_INFO_CAPABILITY_ID,
    "capability_name": "Get Meeting Info",
    "description": "Retrieves the manifest metadata (topic, state, creator, etc.) for a specified meeting.",
    "parameters": MeetingGetInfoInput.__annotations__,
    "output_schema": MeetingGetInfoOutput.__annotations__,
    "handler_info": {
        "type": "function",
        "path": "dreamos.core.agents.capabilities.library.meeting_management.meeting_get_info_capability",
    },
}

MEETING_JOIN_CAPABILITY_ID = "meeting.join"
MEETING_JOIN_CAPABILITY_INFO = {
    "capability_id": MEETING_JOIN_CAPABILITY_ID,
    "capability_name": "Join Meeting",
    "description": "Allows an agent to formally join a meeting, updating the participant list.",
    "parameters": MeetingJoinInput.__annotations__,
    "output_schema": MeetingJoinOutput.__annotations__,
    "handler_info": {
        "type": "function",
        "path": "dreamos.core.agents.capabilities.library.meeting_management.meeting_join_capability",
    },
}

MEETING_VOTE_CAPABILITY_ID = "meeting.vote"
MEETING_VOTE_CAPABILITY_INFO = {
    "capability_id": MEETING_VOTE_CAPABILITY_ID,
    "capability_name": "Vote on Proposal",
    "description": "Casts a vote (yes/no/abstain) on a specific meeting proposal.",
    "parameters": MeetingVoteInput.__annotations__,
    "output_schema": MeetingVoteOutput.__annotations__,
    "handler_info": {
        "type": "function",
        "path": "dreamos.core.agents.capabilities.library.meeting_management.meeting_vote_capability",
    },
}

# Add other capability infos here...
