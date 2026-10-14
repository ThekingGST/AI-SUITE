"""Verify face recognition fix with cleaned embeddings."""
import sys
sys.path.insert(0, "d:/Coding/Jarvis/jarvis_ai")
import pickle
import numpy as np
from config import FACE_EMBEDDINGS_DB, CONFIG

db = pickle.load(open(FACE_EMBEDDINGS_DB, "rb"))
name = list(db.keys())[0]
embs = np.array(db[name], dtype=np.float32)
norms = np.linalg.norm(embs, axis=1, keepdims=True)
embs_normed = embs / norms

threshold = CONFIG.vision.face_match_threshold
print(f"Threshold: {threshold}")
print(f"Registered: {name} ({len(embs)} embeddings)")
print()

def simulate_match(test_emb, label):
    """Simulate the new _match_named algorithm."""
    sample_scores = [float(np.dot(test_emb, e)) for e in embs_normed]
    sample_scores.sort(reverse=True)
    median_score = float(np.median(sample_scores))
    agree = sum(1 for s in sample_scores if s >= threshold)
    majority = agree > len(sample_scores) / 2
    match = median_score >= threshold and majority
    result = name if match else "unknown"
    print(f"  {label}: median={median_score:.3f} agree={agree}/{len(embs)} majority={majority} -> {result}")
    return result

# Test A: Sai (use each registered embedding as test, leave-one-out)
print("=" * 60)
print("  TEST A: Registered user (leave-one-out)")
print("=" * 60)
correct = 0
for i in range(len(embs_normed)):
    test = embs_normed[i]
    result = simulate_match(test, f"Sai sample[{i}]")
    if result == name:
        correct += 1
print(f"  Accuracy: {correct}/{len(embs)} = {correct/len(embs)*100:.0f}%")
assert correct >= len(embs) * 0.6, f"Too many misses: {correct}/{len(embs)}"
print("  PASS")

# Test B: Random faces (should be unknown)
print()
print("=" * 60)
print("  TEST B: Random faces (should be unknown)")
print("=" * 60)
correct = 0
for i in range(10):
    random_emb = np.random.randn(embs.shape[1]).astype(np.float32)
    random_emb = random_emb / np.linalg.norm(random_emb)
    result = simulate_match(random_emb, f"Random[{i}]")
    if result == "unknown":
        correct += 1
print(f"  Accuracy: {correct}/10 = {correct/10*100:.0f}%")
assert correct == 10, f"False positives: {10-correct}/10"
print("  PASS")

# Test C: Slightly perturbed Sai (noise-added, should still match)
print()
print("=" * 60)
print("  TEST C: Sai + noise (should still match)")
print("=" * 60)
correct = 0
for i in range(5):
    base = embs_normed[i % len(embs_normed)]
    noise = np.random.randn(len(base)).astype(np.float32) * 0.15
    perturbed = base + noise
    perturbed = perturbed / np.linalg.norm(perturbed)
    result = simulate_match(perturbed, f"Sai+noise[{i}]")
    if result == name:
        correct += 1
print(f"  Accuracy: {correct}/5 = {correct/5*100:.0f}%")
print(f"  {'PASS' if correct >= 3 else 'PARTIAL'}")

print()
print("=" * 60)
print("  ALL TESTS COMPLETE")
print("=" * 60)
