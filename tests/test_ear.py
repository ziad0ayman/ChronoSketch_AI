import json
import pytest
from pathlib import Path
from src.shared.models import WordTimestamp
from src.ear.transcriber import Transcriber


def _fake_segments(words_data):
    return {
        "segments": [
            {
                "words": [
                    {"word": w["word"], "start": w["start"], "end": w["end"]}
                    for w in words_data
                ]
            }
        ]
    }


def test_transcriber_save_load(tmp_path):
    words = [
        WordTimestamp(word="hello", start=0.0, end=0.5),
        WordTimestamp(word="world", start=0.6, end=1.0),
    ]
    p = tmp_path / "words.json"
    Transcriber.save_timestamps(words, str(p))
    loaded = Transcriber.load_timestamps(str(p))
    assert len(loaded) == 2
    assert loaded[0].word == "hello"
    assert loaded[0].start == 0.0
    assert loaded[1].end == 1.0


def test_transcriber_file_not_found():
    t = Transcriber("tiny")
    with pytest.raises(FileNotFoundError):
        t.transcribe("nonexistent.mp3")
