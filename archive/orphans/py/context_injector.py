import json
import logging
import os

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def inject_context(episode_id: str):
    """Inject Episode 3 outputs (briefing, lore, devlog) to all agent inboxes."""
    base_dir = "runtime/episode_outputs"
    agent_base_dir = "runtime/agent_comms/agent_mailboxes"

    # Load outputs
    with open(f"{base_dir}/EPISODE_{episode_id}_BRIEFING.md", "r") as f:
        briefing = f.read()
    with open(f"{base_dir}/episode_{episode_id}_lore.json", "r") as f:
        lore = json.load(f)
    with open(f"{base_dir}/EPISODE_{episode_id}_DEVLOG.md", "r") as f:
        devlog = f.read()

    # Prepare context payload
    context = {
        "episode": f"EPISODE_{episode_id}",
        "briefing": briefing,
        "lore": lore,
        "devlog": devlog,
    }

    # Inject to all agent inboxes (Agent-1 to Agent-8)
    for agent_id in range(1, 9):
        agent_dir = f"{agent_base_dir}/Agent-{agent_id}"
        os.makedirs(agent_dir, exist_ok=True)
        context_path = f"{agent_dir}/context_episode_{episode_id}.json"
        with open(context_path, "w") as f:
            json.dump(context, f, indent=2)
        logging.info(f"Injected context to {context_path}")


if __name__ == "__main__":
    inject_context("03")
