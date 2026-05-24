from pydantic import TypeAdapter
from src.shared.models import WordTimestamp, SceneEvent

SCENE_EVENT_ADAPTER = TypeAdapter(list[SceneEvent])

SYSTEM_PROMPT = """You are a whiteboard animation director narrating a concept via drawn icons. Given a transcript chunk with word-level timestamps, output a JSON array of scene events.

Rules:
1. GROUP EVERY WORD below into scenes, each consists of a sentence or more. Each scene captures a coherent concept. Do NOT make a scene per word. NO WORD may be left out.
2. Each draw event's start_time is the first word's start in the group; end_time is the last word's end. The last event of the chunk must end at the last word's end_time.
3. Output ONLY a valid JSON array. No markdown, no explanation.

Schema:
{{"event_id": int, "action": "draw"|"clear_canvas", "start_time": float, "end_time": float, "search_keyword": str}}

Transcript with timestamps:
{transcript}"""


def build_prompt(words: list[WordTimestamp]) -> str:
    lines = "\n".join(f"  {w.start:.2f}-{w.end:.2f}: {w.word}" for w in words)
    return SYSTEM_PROMPT.format(transcript=lines)
