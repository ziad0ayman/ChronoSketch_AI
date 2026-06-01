from src.shared.models import WordTimestamp
from src.brain.schemas import build_prompt, SCENE_RAW_ADAPTER
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
    assert "EVERY WORD" in prompt
    assert "Max 3 elements per scene" in prompt


def test_schema_validation():
    raw = """[
        {"start_time": 0.0, "end_time": 2.5,
         "elements": [{"keyword": "cell division"}, {"keyword": "mitosis"}]},
        {"start_time": 3.0, "end_time": 5.0,
         "elements": [{"keyword": "protein"}]}
    ]"""
    scenes = SCENE_RAW_ADAPTER.validate_json(raw)
    assert len(scenes) == 2
    assert len(scenes[0].elements) == 2
    assert scenes[0].elements[0].keyword == "cell division"
    assert scenes[0].elements[1].keyword == "mitosis"


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
    elements = o.plan_scenes([])
    assert elements == []
