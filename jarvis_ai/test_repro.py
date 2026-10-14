import sys
sys.path.insert(0, 'd:/Coding/Jarvis/jarvis_ai')
from voice.command_router import CommandRouter
from ai.ollama_brain import OllamaBrain
from ai.memory import MemoryStore
import logging

logging.basicConfig(level=logging.INFO)

class DummySpeaker:
    def speak(self, t): pass

m = MemoryStore('d:/Coding/Jarvis/jarvis_ai/data/test_repro.db')
b = OllamaBrain(m)
r = CommandRouter(b, m, DummySpeaker())
print("Model at start:", b.model)
print(r.handle('Tell me about Railways', speak=False))
