from pydantic import BaseModel, TypeAdapter
from src.shared.models import WordTimestamp, SceneEvent

SCENE_EVENT_ADAPTER = TypeAdapter(list[SceneEvent])


class SceneElementRaw(BaseModel):
    keyword: str


class SceneRaw(BaseModel):
    start_time: float
    end_time: float
    elements: list[SceneElementRaw]


SCENE_RAW_ADAPTER = TypeAdapter(list[SceneRaw])

SYSTEM_PROMPT = """You are a whiteboard animation director. Given a transcript with word-level timestamps, divide the script into self-contained scenes.

Each scene is a single coherent concept (one sentence or thought). A scene contains elements (keywords) that will be drawn one by one on the same whiteboard. The whiteboard is cleared between scenes.

Rules:
1. GROUP EVERY WORD into scenes. Each scene captures one complete thought.
2. Scene start_time = first word's start in the scene. Scene end_time = last word's end in the scene.
3. Max 3 elements per scene. Each element must be a meaningful CONCEPT that can be represented by an icon. NEVER make an element for filler words (the, a, an, and, it, of, in, to, is, on, for, with, at, by, this, that, next, then, so).
4. GOOD: sentence "A gear icon represents the settings panel" → elements: ["gear", "settings"]
   BAD:  ["a", "gear", "icon", "represents", "the", "settings", "panel"]
   GOOD: "You can store files in cloud folders" → elements: ["file", "folder", "cloud"]
5. If a sentence has more than 3 distinct icon-worthy concepts, split into 2 scenes.
6. Output ONLY valid JSON. No markdown, no explanation.

Output format:
[
  {{
    "start_time": float,
    "end_time": float,
    "elements": [
      {{"keyword": str}},
      ...
    ]
  }},
  ...
]

Transcript with timestamps:
{transcript}"""


def build_prompt(words: list[WordTimestamp]) -> str:
    lines = "\n".join(f"  {w.start:.2f}-{w.end:.2f}: {w.word}" for w in words)
    return SYSTEM_PROMPT.format(transcript=lines)
