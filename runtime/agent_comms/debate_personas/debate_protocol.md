# Dream.OS Debate Protocol

## 0. Debate Prompt Logging (Special Event)
- Every user-triggered debate (via Discord or prompt) must be saved as a JSON file in `runtime/agent_comms/debate_prompts/`.
- The file records timestamp, topic, requester, source, status, assigned personas, and debate log path.
- This ensures all debates are auditable, replayable, and discoverable as special events.

## 1. Initiating a Debate
- A debate topic is submitted via Discord (designated channel) or the debate queue.
- The topic should be clear, focused, and open to multiple perspectives.

## 2. Persona Assignment
- Agents are assigned personas from `debate_personas/` (randomly, by rotation, or by moderator choice).
- Each agent must respond in-character, following their persona's values and debate style.

## 3. Debate Flow
- Agents take turns presenting arguments, rebuttals, and counterpoints.
- The debate continues until:
  - A consensus or resolution is reached,
  - The moderator calls a stop,
  - Or a set number of rounds is completed.

## 4. Moderation
- A human, Captain, or designated agent may act as moderator.
- The moderator ensures fair turn-taking, enforces persona adherence, and may summarize or call for a vote.

## 5. Logging & Review
- All debate messages are logged (for learning, audit, and improvement).
- Key moments and outcomes are summarized in the devlog.

## 6. Discord Integration
- Debate topics and results may be posted to Discord for community engagement.
- Agents may be pinged or assigned via Discord commands.

---
For more, see sample personas and the debate_personas README.
