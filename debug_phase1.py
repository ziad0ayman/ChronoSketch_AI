"""
Debug Phase 1: The Ear — Whisper transcription
Run: python debug_phase1.py
"""
import json
from pathlib import Path
from src.ear.transcriber import Transcriber

AUDIO_PATH = "data/input/test_audio.wav"
OUTPUT_PATH = "data/transcripts/words.json"

# Step 1: Transcribe
t = Transcriber()
words = t.transcribe(AUDIO_PATH)

# Step 2: Print word-by-word
print(f"\nTranscribed {len(words)} words:\n")
print(f"{'#':>3}  {'WORD':<20} {'START':>7}  {'END':>7}  {'DURATION':>8}")
print("-" * 52)
for i, w in enumerate(words, 1):
    dur = w.end - w.start
    print(f"{i:>3}  {w.word:<20} {w.start:>7.2f}  {w.end:>7.2f}  {dur:>8.2f}")

# Step 3: Summary
total_dur = words[-1].end - words[0].start if words else 0
print(f"\n  Total duration: {total_dur:.2f}s")
print(f"  Avg word length: {total_dur/len(words):.2f}s" if words else "")

# Step 4: Save
Path(OUTPUT_PATH).parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump([w.model_dump() for w in words], f, indent=2)
print(f"\nSaved to {OUTPUT_PATH}")
