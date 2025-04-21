# _agent_coordination/utils/emotion_detector.py

import re
from typing import Tuple

class EmotionCueDetector:
    """Detects emotional cues in reflection text using simple keyword heuristics."""

    def __init__(self):
        # Simple keyword→emotion mapping
        self.heuristics = {
            "loop|again|repetition": "frustration",
            "breakthrough|emerged|unlocked": "insight",
            "refused|relentless|pushed": "determination",
            "harmonize|clarity|balance": "clarity",
            "stirred|unseen|shadows": "dread",
            "ignite|catalyst|unleashed": "resolve",
            "disconnected|fragmented": "disorientation",
            "light|hope|ascension": "inspiration",
        }

    def detect_emotion(self, text: str) -> Tuple[str, str]:
        """
        Returns: (emotion_label, match_reason) or ("neutral", "") if no match.
        """
        for pattern, emotion in self.heuristics.items():
            if re.search(pattern, text, flags=re.IGNORECASE):
                return emotion, f"Matched pattern: '{pattern}'"
        return "neutral", "" 