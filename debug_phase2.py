"""
Debug Phase 2: The Brain — LLM scene planning (scene+element format)
Run: python debug_phase2.py
Writes output to debug_phase2_output.txt (UTF-8)
"""
import json
from groq import Groq
from src.shared.models import WordTimestamp, SceneElement
from src.shared.config import GROQ_API_KEY, LLM_MODEL, CHUNK_DURATION
from src.brain.schemas import build_prompt, SCENE_RAW_ADAPTER
from src.hand.layout import get_positions

TRANSCRIPT_PATH = "data/transcripts/words.json"
OUTPUT_PATH = "data/scenes/scenes.json"
LOG_PATH = "debug_phase2_output.txt"

log_lines = []
def echo(s=""):
    log_lines.append(s)

# Step 1: Load words
with open(TRANSCRIPT_PATH) as f:
    words = [WordTimestamp(**w) for w in json.load(f)]
echo(f"Loaded {len(words)} words\n")

# Step 2: Chunk splitting
total_dur = words[-1].end - words[0].start if words else 0

def split_chunks(words, chunk_dur=CHUNK_DURATION):
    chunks = []
    current = []
    cutoff = -1.0
    for w in words:
        if w.start >= cutoff and current:
            chunks.append(current)
            current = []
            cutoff = w.start + chunk_dur
        current.append(w)
    if current:
        chunks.append(current)
    return chunks

if total_dur <= CHUNK_DURATION * 1.5:
    chunks = [words]
    echo(f"Short clip ({total_dur:.1f}s <= {CHUNK_DURATION*1.5:.0f}s): single chunk, {len(words)} words")
else:
    chunks = split_chunks(words)
    echo(f"Split into {len(chunks)} chunks (CHUNK_DURATION={CHUNK_DURATION}s):")
    for i, c in enumerate(chunks):
        echo(f"  Chunk {i+1}: {len(c)} words, {c[0].start:.2f}s - {c[-1].end:.2f}s")

# Step 3: Call LLM
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
if not client:
    echo("\nERROR: GROQ_API_KEY not set")
    raise SystemExit(1)

all_elements: list[SceneElement] = []
next_element_id = 1
next_scene_id = 1

for i, chunk in enumerate(chunks):
    echo(f"\n{'='*60}")
    echo(f"CHUNK {i+1}/{len(chunks)} ({len(chunk)} words)")
    echo(f"{'='*60}")

    prompt = build_prompt(chunk)
    echo("\n--- PROMPT SENT TO LLM ---")
    echo(prompt)
    echo("\n--- END PROMPT ---")

    resp = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "system", "content": prompt}],
        temperature=0.1,
    )
    raw = resp.choices[0].message.content.strip()
    raw_clean = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    echo("\n--- RAW LLM RESPONSE ---")
    echo(raw)
    echo("\n--- END RAW RESPONSE ---")

    try:
        data = json.loads(raw_clean)
    except json.JSONDecodeError as e:
        echo(f"\n*** JSON PARSE FAILED: {e} ***")
        continue

    try:
        scenes = SCENE_RAW_ADAPTER.validate_python(data)
    except Exception as e:
        echo(f"\n*** VALIDATION FAILED: {e} ***")
        continue

    echo(f"\n  LLM returned {len(scenes)} scenes")

    for scene in scenes:
        count = len(scene.elements)
        positions = get_positions(count)
        scene_words = [w for w in chunk if scene.start_time <= w.start < scene.end_time]
        echo(f"\n  Scene: [{scene.start_time:.2f}-{scene.end_time:.2f}] ({count} elements, {len(scene_words)} words):")
        for idx, raw_el in enumerate(scene.elements):
            px, py = positions[idx]
            if scene_words:
                start_w = int((idx / count) * len(scene_words))
                end_w = int(((idx + 1) / count) * len(scene_words))
                group = scene_words[start_w:end_w]
                if group:
                    start = group[0].start
                    end = group[-1].end
                else:
                    start = scene.start_time + (idx / count) * (scene.end_time - scene.start_time)
                    end = scene.start_time + ((idx + 1) / count) * (scene.end_time - scene.start_time)
            else:
                start = scene.start_time + (idx / count) * (scene.end_time - scene.start_time)
                end = scene.start_time + ((idx + 1) / count) * (scene.end_time - scene.start_time)
            se = SceneElement(
                element_id=next_element_id,
                scene_id=next_scene_id,
                keyword=raw_el.keyword,
                start_time=start,
                end_time=end,
                pos_x=px,
                pos_y=py,
            )
            echo(f"    #{se.element_id}: keyword='{se.keyword}' "
                 f"time=[{se.start_time:.2f}-{se.end_time:.2f}] "
                 f"pos=({se.pos_x:.0f},{se.pos_y:.0f})")
            next_element_id += 1
            all_elements.append(se)
        next_scene_id += 1

# Step 4: Summary
echo(f"\n{'='*60}")
echo(f"TOTAL: {len(all_elements)} scene elements")
echo(f"{'='*60}")
for el in all_elements:
    echo(f"  #{el.element_id:>2} | scene={el.scene_id:>2} | {el.keyword:<30} | "
         f"{el.start_time:.2f}s -> {el.end_time:.2f}s | "
         f"pos=({el.pos_x:.0f},{el.pos_y:.0f})")

# Step 5: Save
with open(OUTPUT_PATH, "w") as f:
    json.dump([e.model_dump() for e in all_elements], f, indent=2)
echo(f"\nSaved elements to {OUTPUT_PATH}")

with open(LOG_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(log_lines))
print(f"Output written to {LOG_PATH}")
