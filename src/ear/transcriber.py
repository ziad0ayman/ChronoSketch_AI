import json
from pathlib import Path

import whisper
from src.shared.logger import logger
from src.shared.models import WordTimestamp
from src.shared.config import WHISPER_MODEL


class Transcriber:
    def __init__(self, model_name: str = WHISPER_MODEL):
        logger.info(f"Loading whisper model: {model_name}")
        self._model = whisper.load_model(model_name)

    def transcribe(self, audio_path: str) -> list[WordTimestamp]:
        audio = Path(audio_path)
        if not audio.exists():
            logger.error(f"Audio file not found: {audio_path}")
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        logger.info(f"Transcribing: {audio_path}")
        result = self._model.transcribe(str(audio), word_timestamps=True)
        words: list[WordTimestamp] = []
        for segment in result.get("segments", []):
            for w in segment.get("words", []):
                words.append(WordTimestamp(word=w["word"].strip(), start=w["start"], end=w["end"]))
        logger.info(f"Transcribed {len(words)} words")
        return words

    @staticmethod
    def save_timestamps(words: list[WordTimestamp], output_path: str) -> None:
        data = [w.model_dump() for w in words]
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Timestamps saved: {output_path}")

    @staticmethod
    def load_timestamps(path: str) -> list[WordTimestamp]:
        with open(path, "r", encoding="utf-8") as f:
            return [WordTimestamp(**w) for w in json.load(f)]
