from src.shared.models import WordTimestamp
from src.brain.schemas import build_prompt, SCENE_EVENT_ADAPTER
from src.brain.orchestrator import Orchestrator


def test_build_prompt():
    words = [WordTimestamp(word="mitosis", start=0.0, end=0.5),
             WordTimestamp(word="is", start=0.5, end=0.6),
             WordTimestamp(word="cell", start=0.6, end=0.8),
             WordTimestamp(word="division", start=0.8, end=1.2)]
    prompt = build_prompt(words)
    assert "0.00-0.50: mitosis" in prompt


def test_prompt_requires_full_coverage():
    words = [WordTimestamp(word="a", start=0.0, end=0.5)]
    prompt = build_prompt(words)
    assert "NO WORD" in prompt or "EVERY WORD" in prompt
    assert "last event of the chunk must end" in prompt


def test_schema_validation():
    raw = """[
        {"event_id": 1, "action": "draw", "start_time": 0.0, "end_time": 2.5,
         "search_keyword": "cell division"},
        {"event_id": 2, "action": "clear_canvas", "start_time": 30.0, "end_time": 30.5,
         "search_keyword": ""}
    ]"""
    events = SCENE_EVENT_ADAPTER.validate_json(raw)
    assert len(events) == 2
    assert events[0].action == "draw"
    assert events[1].action == "clear_canvas"


def test_chunk_splitting():
    words = [
        WordTimestamp(word=f"w{i}", start=i * 10.0, end=i * 10.0 + 0.5)
        for i in range(10)
    ]
    chunks = Orchestrator._split_chunks(words)
    assert len(chunks) >= 1
    for chunk in chunks:
        assert len(chunk) >= 1


def test_orchestrator_no_key():
    o = Orchestrator()
    events = o.plan_scenes([])
    assert events == []
