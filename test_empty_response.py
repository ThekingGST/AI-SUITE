import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from jarvis_ai.voice.command_router import CommandRouter
from jarvis_ai.ai.ollama_brain import OllamaBrain
from jarvis_ai.ai.memory import MemoryStore

class TestBug2(unittest.TestCase):
    def setUp(self):
        from ai_suite.core.memory.engine import MemoryEngine
        from ai_suite.core.registry import ServiceContainer
        ServiceContainer._services = {}
        ServiceContainer.register(MemoryEngine, MemoryEngine())
        self.memory = MemoryStore()
        self.memory._engine.sp._execute("DELETE FROM memories")
        self.brain = OllamaBrain(self.memory)
        
        class MockSpeaker:
            def __init__(self):
                class MockManager:
                    is_aborted = False
                    def set_streaming_session(self, val): pass
                    def enqueue(self, txt, prio): pass
                self.manager = MockManager()
                self.enabled = True
            def speak(self, text): pass
            def interrupt(self): pass
            
        self.speaker = MockSpeaker()
        self.router = CommandRouter(brain=self.brain, memory=self.memory, speaker=self.speaker)

    def test_empty_response(self):
        # The user says "tell me about yourself"
        res = self.router._route("tell me about yourself", language="English")
        if isinstance(res, str):
            response = res
        else:
            response = "".join(list(res))
            
        print(f"RESPONSE: '{response}'")
        self.assertTrue(len(response.strip()) > 0, "Response is empty!")

if __name__ == '__main__':
    unittest.main()
