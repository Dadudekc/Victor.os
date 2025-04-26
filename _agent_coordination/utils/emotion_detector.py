# _agent_coordination/utils/emotion_detector.py

import re
from typing import Tuple

class EmotionCueDetector:
    """Detects emotional cues in reflection text using simple keyword heuristics."""

    def __init__(self):
        # Simple keyword→emotion mapping
        self.heuristics = {
            # include frustration keywords
            "loop|again|repetition|frustrated|frustration": "frustration",
            # include direct 'insight' keyword
            "breakthrough|emerged|unlocked|insight": "insight",
            "refused|relentless|pushed": "determination",
            "harmonize|clarity|balance": "clarity",
            "stirred|unseen|shadows": "dread",
            "ignite|catalyst|unleashed": "resolve",
            "disconnected|fragmented": "disorientation",
            # include direct 'inspiration' and 'motivation' keywords
            "light|hope|ascension|inspiration|motivatio[n]?": "inspiration",
        }

    def detect_emotion(self, text: str) -> str:
        """
        Detects and returns an emotion label or 'neutral' if no match.
        """
        for pattern, emotion in self.heuristics.items():
            if re.search(pattern, text, flags=re.IGNORECASE):
                return emotion
        return "neutral" 
