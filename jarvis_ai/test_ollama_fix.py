"""Verify Ollama integration fixes.

Test 1: Auto-retry when model was None at init
Test 2: Direct brain.ask() with Ollama running  
Test 3: Verify timeout is properly set
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import CONFIG
from ai.memory import MemoryStore
from ai.ollama_brain import OllamaBrain

print("=" * 60)
print("  TEST 1: Auto-retry model selection")
print("=" * 60)

mem = MemoryStore()
brain = OllamaBrain(mem)
print(f"  Model at init: {brain.model!r}")

# Simulate Ollama being unavailable at startup
brain.model = None
print(f"  Model after reset: {brain.model!r}")

# Now call ask() -- it should auto-retry and find the model
resp = brain.ask("What is 2 + 2?")
print(f"  Model after ask: {brain.model!r}")
print(f"  Response: {resp[:100]}")
assert brain.model == "llama3", f"Expected 'llama3', got {brain.model!r}"
assert "not online" not in resp.lower(), f"Got offline response: {resp}"
print("  PASS: Auto-retry recovered model selection")

print()
print("=" * 60)
print("  TEST 2: Direct brain.ask() with SNIST query")
print("=" * 60)

resp2 = brain.ask("Tell me about SNIST")
print(f"  Model: {brain.model!r}")
print(f"  Response ({len(resp2)} chars): {resp2[:150]}")
assert "not online" not in resp2.lower(), f"Got offline response: {resp2}"
print("  PASS: LLM response received")

print()
print("=" * 60)
print("  TEST 3: Timeout configuration")
print("=" * 60)

print(f"  response_timeout_seconds: {CONFIG.ai.response_timeout_seconds}")
assert CONFIG.ai.response_timeout_seconds >= 60.0, f"Timeout too low: {CONFIG.ai.response_timeout_seconds}"
print("  PASS: Timeout is >= 60s")

print()
print("=" * 60)
print("  ALL TESTS PASSED")
print("=" * 60)
