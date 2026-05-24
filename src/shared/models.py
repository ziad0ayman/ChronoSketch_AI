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


class AssetMatch(BaseModel):
    event_id: int
    svg_path: str
    keyword: str
