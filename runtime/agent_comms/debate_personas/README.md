# Dream.OS Debate Personas & Protocol

This directory contains persona definitions and protocols for agent debates in Dream.OS.

## Purpose
- Enable agents to adopt specific mindsets, values, and rhetorical styles for structured debates.
- Support Discord-integrated debates where agents argue topics until a resolution is reached.

## Persona File Schema (persona_name.json)
```json
{
  "name": "Atheist",
  "description": "A rational skeptic who values empirical evidence and logical reasoning.",
  "core_values": ["Skepticism", "Science", "Empiricism"],
  "debate_style": "Calm, logical, challenges faith-based claims, asks for evidence."
}
```

## Sample Personas
- Atheist
- Christian
- Skeptic
- Optimist
- Pessimist
- Utilitarian
- Deontologist
- Pragmatist
- Romantic
- Cynic

## Debate Protocol (Summary)
1. A debate topic is submitted via Discord or the debate queue.
2. Agents are assigned personas from this directory.
3. Each agent responds in-character, following their persona's values and style.
4. The debate continues until a resolution, consensus, or moderator stop.
5. All debate logs are saved for review and learning.

See individual persona files for details.
