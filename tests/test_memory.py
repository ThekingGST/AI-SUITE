import unittest
import tempfile
import os
from pathlib import Path
from typing import Iterator

from ai_suite.core.memory.storage import SQLiteStorageProvider
from ai_suite.core.memory.engine import MemoryEngine
from ai_suite.core.memory.types import MemoryScope, MemoryType, MemoryMetadata
from jarvis_ai.ai.memory import MemoryStore
from ai_suite.core.events import EventBus

class TestMemorySystem(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_memory.sqlite3"
        self.eb = EventBus()
        self.sp = SQLiteStorageProvider(self.db_path)
        self.engine = MemoryEngine(self.eb, self.sp)
        
        # Override the ServiceContainer injected engine for MemoryStore
        import ai_suite.core.registry
        ai_suite.core.registry.ServiceContainer.register(MemoryEngine, self.engine)
        self.store = MemoryStore(self.db_path, assistant_id="jarvis")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_database_initialization(self):
        self.assertTrue(self.db_path.exists())

    def test_explicit_remember_and_search(self):
        self.store.remember("User's favorite color is blue.")
        
        # Exact keyword search
        results = self.store.search_memories("color")
        self.assertEqual(len(results), 1)
        self.assertIn("blue", results[0])
        
        # Multiple keyword search
        results2 = self.store.search_memories("favorite color")
        self.assertEqual(len(results2), 1)

    def test_forget_memory(self):
        self.store.remember("User likes apples.")
        self.store.remember("User likes oranges.")
        
        results = self.store.search_memories("apples")
        self.assertEqual(len(results), 1)
        
        # Forget
        success = self.store.forget("apples")
        self.assertTrue(success)
        
        results_after = self.store.search_memories("apples")
        self.assertEqual(len(results_after), 0)
        
        results_other = self.store.search_memories("oranges")
        self.assertEqual(len(results_other), 1)

    def test_persistence_across_restart(self):
        self.store.remember("Persistent fact 12345.")
        
        # Destroy
        del self.store
        del self.engine
        del self.sp
        
        # Recreate
        sp2 = SQLiteStorageProvider(self.db_path)
        engine2 = MemoryEngine(self.eb, sp2)
        import ai_suite.core.registry
        ai_suite.core.registry.ServiceContainer.register(MemoryEngine, engine2)
        store2 = MemoryStore(self.db_path, assistant_id="jarvis")
        
        results = store2.search_memories("Persistent fact")
        self.assertEqual(len(results), 1)
        self.assertIn("12345", results[0])

    def test_secret_rejection(self):
        secrets = [
            "sk-1234567890abcdef1234567890abcdef1234",
            "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
            "password=supersecret",
            "api_key: abcdefg"
        ]
        
        for sec in secrets:
            self.store.remember(f"My token is {sec}")
            
        # Should not be stored
        results = self.store.list_memories()
        self.assertEqual(len(results), 0)

    def test_assistant_isolation(self):
        # Create memory as JARVIS
        self.store.remember("JARVIS specific memory.")
        
        # Create a FRIDAY store
        friday_store = MemoryStore(self.db_path, assistant_id="friday")
        friday_store.remember("FRIDAY specific memory.")
        
        # JARVIS shouldn't see FRIDAY
        j_results = self.store.list_memories()
        self.assertEqual(len(j_results), 1)
        self.assertEqual(j_results[0], "JARVIS specific memory.")
        
        # FRIDAY shouldn't see JARVIS
        f_results = friday_store.list_memories()
        self.assertEqual(len(f_results), 1)
        self.assertEqual(f_results[0], "FRIDAY specific memory.")

    def test_retrieval_limit(self):
        for i in range(10):
            self.store.remember(f"Fact {i} about apples.")
            
        results = self.store.search_memories("apples", limit=5)
        self.assertEqual(len(results), 5)
        
    def test_conversation_context_isolation(self):
        # Add message to conversation history
        self.store.add_message("user", "I am studying Python.")
        self.assertEqual(len(self.store.recent_messages()), 1)
        
        # Should not be in long term memory
        results = self.store.search_memories("Python")
        self.assertEqual(len(results), 0)
        
    def test_list_memories(self):
        self.store.remember("Fact A")
        self.store.remember("Fact B")
        self.store.forget("Fact A")
        
        mems = self.store.list_memories()
        self.assertEqual(len(mems), 1)
        self.assertEqual(mems[0], "Fact B")

if __name__ == "__main__":
    unittest.main()
