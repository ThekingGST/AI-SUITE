"""Analyze face embeddings to understand scoring."""
import sys
sys.path.insert(0, "d:/Coding/Jarvis/jarvis_ai")
import pickle
import numpy as np
from config import FACE_EMBEDDINGS_DB

db = pickle.load(open(FACE_EMBEDDINGS_DB, "rb"))
embs = np.array(list(db.values())[0], dtype=np.float32)
n = len(embs)
name = list(db.keys())[0]
print(f"{n} embeddings for {name}")
print()

# Normalize
norms = np.linalg.norm(embs, axis=1, keepdims=True)
embs_normed = embs / norms

# Internal cosine similarity matrix
print("Sample-to-sample cosine similarities (same person):")
sims = embs_normed @ embs_normed.T
for i in range(n):
    row = " ".join(f"{sims[i,j]:.3f}" for j in range(n))
    print(f"  [{i}] {row}")

off_diag = [sims[i,j] for i in range(n) for j in range(n) if i != j]
print(f"\nOff-diagonal: min={min(off_diag):.3f} max={max(off_diag):.3f} mean={np.mean(off_diag):.3f}")

# Centroid analysis
centroid = embs_normed.mean(axis=0)
centroid = centroid / np.linalg.norm(centroid)
centroid_sims = [float(np.dot(centroid, e)) for e in embs_normed]
print(f"\nCentroid similarities: min={min(centroid_sims):.3f} max={max(centroid_sims):.3f} mean={np.mean(centroid_sims):.3f}")

# Blended score (current formula)
max_sample_sims = [float(max(np.dot(e, embs_normed.T))) for e in embs_normed]
blended = [(c * 0.65 + m * 0.35) for c, m in zip(centroid_sims, max_sample_sims)]
print(f"Blended scores (self): min={min(blended):.3f} max={max(blended):.3f} mean={np.mean(blended):.3f}")

# Simulate random embedding
print("\n--- Simulating random/different face ---")
for trial in range(5):
    random_emb = np.random.randn(embs.shape[1]).astype(np.float32)
    random_emb = random_emb / np.linalg.norm(random_emb)
    c_score = float(np.dot(centroid, random_emb))
    s_scores = [float(np.dot(random_emb, e)) for e in embs_normed]
    m_score = max(s_scores)
    blended_score = c_score * 0.65 + m_score * 0.35
    print(f"  Random[{trial}]: centroid={c_score:.3f} max_sample={m_score:.3f} blended={blended_score:.3f}")
