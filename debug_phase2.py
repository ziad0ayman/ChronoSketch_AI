"""
Debug Phase 2: The Brain — LLM scene planning
Run: python debug_phase2.py
Writes output to debug_phase2_output.txt (UTF-8)
"""
import json
from groq import Groq
from src.shared.models import WordTimestamp
from src.shared.config import GROQ_API_KEY, LLM_MODEL, CHUNK_DURATION
from src.brain.schemas import build_prompt, SCENE_EVENT_ADAPTER

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

# Step 2: Chunk splitting (mirrors orchestrator.py logic)
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

# Step 3: Call LLM chunk by chunk
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
if not client:
    echo("\nERROR: GROQ_API_KEY not set")
    raise SystemExit(1)

all_events = []
next_id = 1

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

    valid = []
    for item in data:
        try:
            ev = SCENE_EVENT_ADAPTER.validate_python([item])[0]
            valid.append(ev)
        except Exception as e:
            echo(f"  Skipping invalid event: {e}")

    echo(f"\n  LLM returned {len(data)} events, {len(valid)} valid")

    for ev in valid:
        old_id = ev.event_id
        ev.event_id = next_id
        echo(f"  Event #{old_id} -> global #{next_id}: action={ev.action} "
             f"keyword='{ev.search_keyword}' "
             f"time=[{ev.start_time:.2f}s-{ev.end_time:.2f}s]")
        next_id += 1

    all_events.extend(valid)

# Step 4: Final summary
echo(f"\n{'='*60}")
echo(f"TOTAL: {len(all_events)} scene events")
echo(f"{'='*60}")
for ev in all_events:
    echo(f"  #{ev.event_id:>2} | {ev.action:<12} | {ev.search_keyword:<30} | "
         f"{ev.start_time:.2f}s -> {ev.end_time:.2f}s")

# Step 5: Save
with open(OUTPUT_PATH, "w") as f:
    json.dump([e.model_dump() for e in all_events], f, indent=2)
echo(f"\nSaved scenes to {OUTPUT_PATH}")

with open(LOG_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(log_lines))
print(f"Output written to {LOG_PATH}")
