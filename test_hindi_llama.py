import sys, os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from jarvis_ai.ai.ollama_brain import OllamaBrain
from jarvis_ai.ai.memory import MemoryStore
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
ms = MemoryStore()
brain = OllamaBrain(ms)
res = brain.ask_stream("tell me about yourself", language="Hindi")
print("RESPONSE:", "".join(list(res)))
