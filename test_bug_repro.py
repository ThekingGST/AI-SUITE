import sys
import logging
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from jarvis_ai.voice.command_router import CommandRouter
from jarvis_ai.ai.ollama_brain import OllamaBrain
from jarvis_ai.ai.memory import MemoryStore

def run():
    logging.basicConfig(level=logging.INFO)
    
    memory = MemoryStore()
    memory.search_memories = lambda *args, **kwargs: []
    memory.add_message = lambda *args, **kwargs: None
    
    brain = OllamaBrain(memory)
    brain.context.messages = lambda: []
    brain.context.summary_for_planner = lambda: ""
    brain.context.add = lambda *args: None
    
    class MockSpeaker:
        def __init__(self):
            class MockManager:
                is_aborted = False
                def set_streaming_session(self, val): pass
                def enqueue(self, txt, prio): print("ENQUEUED:", txt)
            self.manager = MockManager()
        def speak(self, text):
            print("SPOKE:", text)
            
    router = CommandRouter(brain=brain, memory=memory, speaker=MockSpeaker())
    
    try:
        res = router.handle("what is my name?", language="en")
        print("Success:", res)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    run()
