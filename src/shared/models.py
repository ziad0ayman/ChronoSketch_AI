from pydantic import BaseModel
from typing import Literal


class WordTimestamp(BaseModel):
    word: str
    start: float
    end: float


class SceneEvent(BaseModel):
    event_id: int
    action: Literal["draw", "clear_canvas"]
    start_time: float
    end_time: float
    search_keyword: str


class SceneElement(BaseModel):
    element_id: int
    scene_id: int
    keyword: str
    start_time: float
    end_time: float
    pos_x: float = 0.0
    pos_y: float = 0.0


class AssetMatch(BaseModel):
    event_id: int
    svg_path: str
    keyword: str
    candidates: list[tuple[str, float]] = []
