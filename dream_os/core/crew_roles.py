from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class CrewRole:
    name: str
    skills: List[str]
    default_tools: List[str] = field(default_factory=list)

ROLE_REGISTRY: Dict[str, CrewRole] = {
    "Strategist": CrewRole("Strategist", ["plan", "analyze"], ["openai"]),
    "Executor":  CrewRole("Executor",  ["code", "test"],      ["cursor"]),
    "Outreach":  CrewRole("Outreach",  ["social", "respond"], ["discord"]),
}

def get_role(name: str) -> CrewRole:
    return ROLE_REGISTRY[name] 