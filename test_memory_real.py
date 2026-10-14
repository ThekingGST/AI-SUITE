import os
from ai_suite.core.memory.engine import MemoryEngine
from ai_suite.core.memory.storage import MemoryStorage

def run_test():
    storage = MemoryStorage(":memory:")
    engine = MemoryEngine(storage)
    
    # 1. Store
    engine.add("My favorite food is biryani.", assistant_id="jarvis")
    
    # 2. Search
    results = engine.search("favorite food", assistant_id="jarvis")
    print("SEARCH 1:")
    for r in results:
        print(f" - {r.content}")
        
    # 3. Update / Forget
    engine.add("Actually, my favorite color is white.", assistant_id="jarvis")
    engine.forget("color", assistant_id="jarvis")
    engine.add("My favorite color is blue.", assistant_id="jarvis")
    
    # 4. Search again
    results2 = engine.search("favorite color", assistant_id="jarvis")
    print("SEARCH 2:")
    for r in results2:
        print(f" - {r.content} (Active: {r.active})")

if __name__ == '__main__':
    run_test()
