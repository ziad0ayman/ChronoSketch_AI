"""
Debug Phase 3: The Library — embedding-based SVG asset retrieval
Run: python debug_phase3.py
Writes output to debug_phase3_output.txt (UTF-8)
"""
import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
from src.shared.models import SceneElement, AssetMatch
from src.shared.config import ASSETS_DIR
from src.library.indexer import Indexer

SCENES_PATH = "data/scenes/scenes.json"
OUTPUT_PATH = "data/scenes/assets.json"
LOG_PATH = "debug_phase3_output.txt"

log_lines = []
def echo(s=""):
    log_lines.append(s)

# Step 1: Load scenes
with open(SCENES_PATH) as f:
    elements = [SceneElement(**e) for e in json.load(f)]
echo(f"Loaded {len(elements)} scene elements\n")

# Step 2: Build index
indexer = Indexer(str(ASSETS_DIR))
index = indexer.build_index()
echo(f"Indexed {len(index)} SVGs from {ASSETS_DIR}\n")

# Show first 20 filenames as sample
echo("Sample indexed SVGs (first 20):")
for i, fn in enumerate(sorted(index.keys())[:20]):
    echo(f"  {i+1:>2}. {fn:30s} keywords={index[fn]}")
echo()

# Step 3: Embed all filenames
echo("Loading embedding model: all-MiniLM-L6-v2")
model = SentenceTransformer("all-MiniLM-L6-v2")
echo()

filename_embeddings: dict[str, np.ndarray] = {}
if index:
    phrases = [" ".join(kws) for kws in index.values()]
    embeds = model.encode(phrases, normalize_embeddings=True)
    for fname, vec in zip(index.keys(), embeds):
        filename_embeddings[fname] = vec

# Step 4: Query each element, show top-5 results
all_assets: list[AssetMatch] = []

for el in elements:
    keyword = el.keyword
    if not keyword:
        echo(f"  Element #{el.element_id}: empty keyword, skipping")
        all_assets.append(AssetMatch(event_id=el.element_id, svg_path="", keyword=keyword))
        continue

    query_vec = model.encode(keyword, normalize_embeddings=True)

    scored = []
    for fname, vec in filename_embeddings.items():
        score = float(query_vec @ vec)
        scored.append((score, fname))
    scored.sort(key=lambda x: -x[0])
    top5 = scored[:5]

    echo(f"  Element #{el.element_id:>2} | keyword='{keyword}'")
    for rank, (score, fname) in enumerate(top5, 1):
        echo(f"         #{rank}: {fname:30s} (score={score:.3f})")
    echo()

    candidates = [(fname, score) for score, fname in top5]
    best = scored[0][1] if scored else None
    best_path = str(ASSETS_DIR / f"{best}.svg") if best else ""
    all_assets.append(AssetMatch(
        event_id=el.element_id, svg_path=best_path, keyword=keyword,
        candidates=candidates
    ))

# Step 5: Save
with open(OUTPUT_PATH, "w") as f:
    json.dump([a.model_dump() for a in all_assets], f, indent=2)
echo(f"Saved {len(all_assets)} assets to {OUTPUT_PATH}")

with open(LOG_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(log_lines))
print(f"Output written to {LOG_PATH}")
