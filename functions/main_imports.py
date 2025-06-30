"""Import all Cloud Functions endpoints"""

# Import existing functions
from main import (
    transcribe,
    chat,
    get_drinks_master,
    add_drink,
    start_session,
    get_current_session,
    guardian_check,
    drink
)

# Import new functions
from bartender import bartender
from guardian_monitor import guardian_monitor
from drinking_coach_analyze import drinking_coach_analyze
from tts import tts

# Make all functions available
__all__ = [
    'transcribe',
    'chat',
    'get_drinks_master',
    'add_drink',
    'start_session',
    'get_current_session',
    'guardian_check',
    'drink',
    'bartender',
    'guardian_monitor',
    'drinking_coach_analyze',
    'tts'
]