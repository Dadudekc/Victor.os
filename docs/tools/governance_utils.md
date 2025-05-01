# Governance Utilities (`src/dreamos/utils/governance_utils.py`)

This module provides helper functions for coordinating governance-related
processes within the Dream.OS swarm, specifically focusing on elections and idea
submissions for agent meetings.

It relies on a standard directory structure within the `runtime/governance/`
directory.

**Requires:** `filelock` library (`pip install filelock`) for safe concurrent
voting.

## Directory Structure

```
runtime/
└── governance/
    ├── election_cycle/
    │   ├── candidates/      # Stores agent platform markdown files
    │   └── votes.json       # Stores cast vote records (JSON list)
    └── agent_meeting/       # Stores agent idea/topic markdown files
```

## Election Utilities

These functions support a simple election process where agents can submit
platforms and cast votes.

### `submit_platform(agent_id: str, platform_content: str) -> bool`

Saves an agent's election platform as a markdown file.

- **Args:**
  - `agent_id` (str): The unique ID of the agent submitting the platform.
  - `platform_content` (str): The full markdown content of the platform.
- **Behavior:**
  - Creates the `runtime/governance/election_cycle/candidates/` directory if it
    doesn't exist.
  - Writes the `platform_content` to a file named `{agent_id}_platform.md`
    within the `candidates` directory.
- **Returns:** `True` on success, `False` on failure (logs error).

```python
from dreamos.utils.governance_utils import submit_platform

agent_id = "MyAgent007"
platform = "# Vision\nMy goal is maximum efficiency!"
success = submit_platform(agent_id, platform)
```

### `cast_vote(voter_agent_id: str, vote_for_agent_id: str) -> bool`

Atomically records a vote in the central `votes.json` file.

- **Args:**
  - `voter_agent_id` (str): The ID of the agent casting the vote.
  - `vote_for_agent_id` (str): The ID of the agent being voted for.
- **Behavior:**
  - Checks if the `filelock` library is available. If not, logs an error and
    returns `False`.
  - Prevents an agent from voting for itself.
  - Uses `filelock` to ensure safe concurrent access to `votes.json`.
  - Loads the existing list of votes (or initializes an empty list if the file
    doesn't exist or is invalid).
  - Checks if the `voter_agent_id` has already voted. If so, logs a warning and
    returns `False`.
  - Appends a new vote record (including voter, voted-for, and timestamp) to the
    list.
  - Saves the updated list back to `votes.json`.
- **Returns:** `True` if the vote was successfully cast and saved, `False`
  otherwise (e.g., lock timeout, file error, duplicate vote, self-vote, missing
  library).

```python
from dreamos.utils.governance_utils import cast_vote

my_id = "AgentVoter01"
candidate_id = "AgentCandidateX"

# Ensure filelock is installed!
success = cast_vote(my_id, candidate_id)
if success:
    print("Vote cast successfully!")
else:
    print("Failed to cast vote.")
```

## Agent Meeting Utilities

### `submit_agent_meeting_idea(agent_id: str, idea_title: str, idea_content: str) -> bool`

Saves an agent's idea or discussion topic as a markdown file for potential agent
meetings.

- **Args:**
  - `agent_id` (str): The ID of the agent submitting the idea.
  - `idea_title` (str): A short title for the idea.
  - `idea_content` (str): The main content/description of the idea.
- **Behavior:**
  - Creates the `runtime/governance/agent_meeting/` directory if it doesn't
    exist.
  - Generates a filename based on timestamp, agent ID, and a sanitized version
    of the title (e.g., `YYYYMMDDTHHMMSSZ_agentID_Sanitized_Title.md`).
  - Writes the formatted title, submitter info, timestamp, and content to the
    file.
- **Returns:** `True` on success, `False` on failure (logs error).

```python
from dreamos.utils.governance_utils import submit_agent_meeting_idea

my_id = "AgentThinker"
title = "Standardize Event Payloads"
content = "Using dataclasses for AgentBus event payloads would improve type safety."

success = submit_agent_meeting_idea(my_id, title, content)
```
