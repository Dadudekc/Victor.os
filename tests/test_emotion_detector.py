import os
import sys
# Ensure project root is in path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
from _agent_coordination.utils.emotion_detector import EmotionCueDetector

@ pytest.fixture
def detector():
    return EmotionCueDetector()


def test_detect_frustration(detector):
    text = "Oh no, I'm so frustrated with this!"
    assert detector.detect_emotion(text) == "frustration"


def test_detect_insight(detector):
    text = "This moment gave me a new insight into the problem."
    assert detector.detect_emotion(text) == "insight"


def test_detect_inspiration(detector):
    text = "That speech was pure inspiration and motivation."
    assert detector.detect_emotion(text) == "inspiration"


def test_detect_neutral(detector):
    text = "Just a normal day without any strong emotion."
    assert detector.detect_emotion(text) == "neutral" 
