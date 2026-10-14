"""Clean contaminated face embeddings by detecting and removing outlier clusters.

Analyzes the embeddings for each registered person and removes samples that
don't belong to the dominant cluster (i.e., different person's face registered
under the same name).
"""
import sys
sys.path.insert(0, "d:/Coding/Jarvis/jarvis_ai")
import pickle
import numpy as np
from config import FACE_EMBEDDINGS_DB

# Load
db = pickle.load(open(FACE_EMBEDDINGS_DB, "rb"))

for name, vectors in db.items():
    if not vectors:
        continue
    
    arr = np.array(vectors, dtype=np.float32)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    arr_normed = arr / norms
    n = len(arr_normed)
    
    print(f"\n{'='*60}")
    print(f"  {name}: {n} embeddings")
    print(f"{'='*60}")
    
    # Compute similarity matrix
    sim_matrix = arr_normed @ arr_normed.T
    
    # Average similarity of each sample to all other samples
    avg_sims = []
    for i in range(n):
        others = [sim_matrix[i, j] for j in range(n) if j != i]
        avg_sims.append(np.mean(others))
    
    print("\nPer-sample average similarity to others:")
    for i, avg in enumerate(avg_sims):
        status = "KEEP" if avg > 0.3 else "OUTLIER"
        print(f"  [{i}] avg_sim={avg:.3f} -> {status}")
    
    # Identify dominant cluster using the sample with highest average similarity
    best_idx = int(np.argmax(avg_sims))
    print(f"\nDominant cluster seed: sample [{best_idx}] (avg_sim={avg_sims[best_idx]:.3f})")
    
    # Keep samples that have >0.3 similarity to the dominant sample
    keep = []
    remove = []
    for i in range(n):
        sim_to_best = sim_matrix[i, best_idx]
        if sim_to_best > 0.3:
            keep.append(i)
        else:
            remove.append(i)
    
    print(f"\nKEEP: {keep}")
    print(f"REMOVE: {remove}")
    
    if remove:
        cleaned = [vectors[i] for i in keep]
        db[name] = cleaned
        print(f"\nCleaned: {len(vectors)} -> {len(cleaned)} embeddings")
    else:
        print("\nNo cleaning needed.")

# Save cleaned database
if any(True for name in db for vectors in [db[name]] if len(vectors) < len(pickle.load(open(FACE_EMBEDDINGS_DB, "rb")).get(name, []))):
    backup = str(FACE_EMBEDDINGS_DB) + ".bak"
    import shutil
    shutil.copy2(FACE_EMBEDDINGS_DB, backup)
    print(f"\nBackup saved: {backup}")
    
    with open(FACE_EMBEDDINGS_DB, "wb") as f:
        pickle.dump(db, f)
    print(f"Cleaned database saved: {FACE_EMBEDDINGS_DB}")
else:
    print("\nNo changes needed.")

# Verify cleaned data
print(f"\n{'='*60}")
print("  VERIFICATION")
print(f"{'='*60}")
db2 = pickle.load(open(FACE_EMBEDDINGS_DB, "rb"))
for name, vectors in db2.items():
    arr = np.array(vectors, dtype=np.float32)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    arr_normed = arr / norms
    sim_matrix = arr_normed @ arr_normed.T
    off_diag = [sim_matrix[i,j] for i in range(len(arr)) for j in range(len(arr)) if i != j]
    print(f"  {name}: {len(vectors)} embeddings")
    if off_diag:
        print(f"    Similarity: min={min(off_diag):.3f} max={max(off_diag):.3f} mean={np.mean(off_diag):.3f}")
