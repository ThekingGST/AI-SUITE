import os
import sys
from unittest.mock import MagicMock
from jarvis_ai.config import CONFIG
from jarvis_ai.voice.command_router import CommandRouter

def run_test():
    import logging
    logging.getLogger().setLevel(logging.CRITICAL)
    
    mock_brain = MagicMock()
    def mock_ask_stream(*args, **kwargs):
        print(f"KWARGS: {kwargs}")
        lang = kwargs.get('language', 'en')
        if lang == 'Hindi':
            yield "मेरा नाम जार्विस है।"
        elif lang == 'Telugu':
            yield "నా పేరు జార్విస్."
        else:
            yield "My name is Jarvis."
            
    mock_brain.ask_stream = mock_ask_stream
    
    mock_memory = MagicMock()
    mock_speaker = MagicMock()
    mock_sm = MagicMock()
    mock_sm.is_aborted = False
    mock_speaker.manager = mock_sm
    
    router = CommandRouter(mock_brain, mock_memory, mock_speaker)
    
    test_cases = [
        ("English", "Jarvis, what is my name?", "en"),
        ("Hindi", "जार्विस, मेरा नाम क्या है?", "hi"),
        ("Telugu", "జార్విస్, నా పేరు ఏమిటి?", "te")
    ]
    
    for name, text, expected_lang in test_cases:
        print(f"--- TEST: {name} ---")
        mock_sm.enqueue.reset_mock()
        router.handle(text, language=expected_lang)
        
        if mock_sm.enqueue.call_count > 0:
            for call in mock_sm.enqueue.call_args_list:
                print(f"TTS Enqueued: {call[0][0].encode('utf-8')}")
        else:
            print("TTS Enqueued: None")
        print("\n")

if __name__ == '__main__':
    run_test()
