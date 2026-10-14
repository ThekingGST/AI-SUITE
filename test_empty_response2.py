import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from jarvis_ai.config import CONFIG

from ai_suite.core.registry import ServiceContainer
from ai_suite.core.memory.engine import MemoryEngine
from ai_suite.core.memory.storage import SQLiteStorageProvider
from ai_suite.core.events import EventBus
from pathlib import Path
eb = EventBus()
sp = SQLiteStorageProvider(Path("test.db"))
me = MemoryEngine(eb, sp)
ServiceContainer._services = {}
ServiceContainer.register(MemoryEngine, me)

from jarvis_ai.ai.memory import MemoryStore
from jarvis_ai.ai.ollama_brain import OllamaBrain
from jarvis_ai.voice.command_router import CommandRouter

ms = MemoryStore()
brain = OllamaBrain(ms)
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
            
speaker = MockSpeaker()
router = CommandRouter(brain=brain, memory=ms, speaker=speaker)

res = router._route("tell me about yourself")
if isinstance(res, str):
    print("STR:", res)
else:
    print("ITER:", "".join(list(res)))
