"""Package tts."""

from . import abc
from . import elevenlabs
from . import elevenlabs.client
from . import logging
from . import os
from . import pyttsx3
from . import typing


__all__ = [

    'AppConfig',
    'ElevenLabs',
    'ElevenLabsTTS',
    'LocalTTS',
    'TTSInterface',
    'get_tts_engine',
    'is_available',
    'save',
    'synthesize',
]
