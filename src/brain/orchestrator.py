import json
from groq import Groq
from src.shared.logger import logger
from src.shared.models import WordTimestamp, SceneEvent
from src.shared.config import GROQ_API_KEY, LLM_MODEL, CHUNK_DURATION
from src.brain.schemas import build_prompt


class Orchestrator:
    def __init__(self):
        if not GROQ_API_KEY:
            logger.warn("GROQ_API_KEY not set; Brain phase will be skipped")
        self._client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

    def plan_scenes(self, words: list[WordTimestamp]) -> list[SceneEvent]:
        if not self._client:
            logger.warn("No Groq client; returning empty scene plan")
            return []

        total_dur = words[-1].end - words[0].start if words else 0
        if total_dur <= CHUNK_DURATION * 1.5:
            chunks = [words]
            logger.info(f"Short clip ({total_dur:.1f}s <= {CHUNK_DURATION*1.5:.0f}s): skipping chunking")
        else:
            chunks = self._split_chunks(words)
        all_events: list[SceneEvent] = []
        next_id = 1

        for i, chunk in enumerate(chunks):
            prompt = build_prompt(chunk)
            logger.info(f"LLM chunk {i + 1}/{len(chunks)}: {len(chunk)} words")
            events = self._llm_parse(prompt)
            if not events:
                continue
            for ev in events:
                ev.event_id = next_id
                next_id += 1
            all_events.extend(events)

        logger.info(f"Planned {len(all_events)} scene events")
        return all_events

    def _llm_parse(self, prompt: str) -> list[SceneEvent]:
        try:
            resp = self._client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "system", "content": prompt}],
                temperature=0.1,
            )
            raw = resp.choices[0].message.content.strip()
            logger.info(f"LLM raw response:\n{raw[:2000]}")
            raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            data = json.loads(raw)
        except Exception as e:
            logger.warn(f"LLM call or JSON parse failed: {e}")
            return []

        valid = []
        for item in data:
            try:
                ev = SceneEvent(**item)
                valid.append(ev)
            except Exception as e:
                logger.warn(f"Skipping invalid event: {e}")
        if len(valid) < len(data):
            logger.warn(f"Kept {len(valid)}/{len(data)} events from chunk")
        return valid

    @staticmethod
    def _split_chunks(words: list[WordTimestamp]) -> list[list[WordTimestamp]]:
        chunks: list[list[WordTimestamp]] = []
        current: list[WordTimestamp] = []
        cutoff = -1.0
        for w in words:
            if w.start >= cutoff and current:
                chunks.append(current)
                current = []
                cutoff = w.start + CHUNK_DURATION
            current.append(w)
        if current:
            chunks.append(current)
        return chunks
