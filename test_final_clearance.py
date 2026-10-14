import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from jarvis_ai.voice.command_router import CommandRouter
from jarvis_ai.ai.ollama_brain import OllamaBrain
from jarvis_ai.ai.memory import MemoryStore

class TestFinalClearance(unittest.TestCase):
    def setUp(self):
        from ai_suite.core.memory.engine import MemoryEngine
        from ai_suite.core.registry import ServiceContainer
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

    def test_task_1_english_bug_fixed(self):
        # Memory must exist to trigger the string indices bug
        self.memory.remember("My name is John")
        # Should not raise exception
        result = self.router._route("what is my name?", language="en")
        response = "".join(list(result))
        self.assertNotIn("Command execution failed", response)
        self.assertTrue(len(response) > 0)

    def test_task_2_multilingual_text(self):
        # HI
        res = self.router._route("मेरा नाम क्या है?", language="hi")
        self.assertTrue(len("".join(list(res))) > 0)
        # TE
        res = self.router._route("నా పేరు ఏమిటి?", language="te")
        self.assertTrue(len("".join(list(res))) > 0)
        
    def test_task_5_pdf_intelligence(self):
        # Just ensure context injection is working
        doc_context = "This is a test PDF about AI."
        self.brain.context.add("user", "Explain this pdf")
        res = self.brain.ask_grounded_stream("Explain this pdf", doc_context)
        response = "".join(list(res))
        self.assertTrue(len(response) > 0)
        
    def test_task_6_memory(self):
        self.memory.remember("Fact A")
        mems = self.memory.list_memories()
        self.assertTrue(any("Fact A" in m for m in mems))
        self.memory.forget("Fact A")
        mems2 = self.memory.list_memories()
        self.assertFalse(any("Fact A" in m for m in mems2))

if __name__ == '__main__':
    unittest.main()
