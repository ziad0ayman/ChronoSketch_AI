import json
from groq import Groq
from src.shared.logger import logger
from src.shared.models import WordTimestamp, SceneElement
from src.shared.config import GROQ_API_KEY, LLM_MODEL, CHUNK_DURATION
from src.brain.schemas import build_prompt, SCENE_RAW_ADAPTER
from src.hand.layout import get_positions


class Orchestrator:
    def __init__(self):
        if not GROQ_API_KEY:
            logger.warn("GROQ_API_KEY not set; Brain phase will be skipped")
        self._client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

    def plan_scenes(self, words: list[WordTimestamp]) -> list[SceneElement]:
        if not self._client:
            logger.warn("No Groq client; returning empty scene plan")
            return []

        total_dur = words[-1].end - words[0].start if words else 0
        if total_dur <= CHUNK_DURATION * 1.5:
            chunks = [words]
            logger.info(f"Short clip ({total_dur:.1f}s <= {CHUNK_DURATION*1.5:.0f}s): skipping chunking")
        else:
            chunks = self._split_chunks(words)
        all_elements: list[SceneElement] = []
        next_element_id = 1
        next_scene_id = 1

        for i, chunk in enumerate(chunks):
            prompt = build_prompt(chunk)
            logger.info(f"LLM chunk {i + 1}/{len(chunks)}: {len(chunk)} words")
            scenes = self._llm_parse(prompt)
            if not scenes:
                continue
            for scene in scenes:
                count = len(scene.elements)
                if count == 0:
                    logger.warn(f"LLM returned scene with 0 elements, skipping")
                    continue
                positions = get_positions(count)
                scene_words = [w for w in chunk if scene.start_time <= w.start < scene.end_time]
                for idx, raw_el in enumerate(scene.elements):
                    px, py = positions[idx]
                    if scene_words:
                        start_w = int((idx / count) * len(scene_words))
                        end_w = int(((idx + 1) / count) * len(scene_words))
                        group = scene_words[start_w:end_w]
                        if group:
                            start = group[0].start
                            end = group[-1].end
                        else:
                            start = scene.start_time + (idx / count) * (scene.end_time - scene.start_time)
                            end = scene.start_time + ((idx + 1) / count) * (scene.end_time - scene.start_time)
                    else:
                        start = scene.start_time + (idx / count) * (scene.end_time - scene.start_time)
                        end = scene.start_time + ((idx + 1) / count) * (scene.end_time - scene.start_time)
                    se = SceneElement(
                        element_id=next_element_id,
                        scene_id=next_scene_id,
                        keyword=raw_el.keyword,
                        start_time=start,
                        end_time=end,
                        pos_x=px,
                        pos_y=py,
                    )
                    next_element_id += 1
                    all_elements.append(se)
                next_scene_id += 1

        logger.info(f"Planned {len(all_elements)} elements across {next_scene_id - 1} scenes")
        return all_elements

    def _llm_parse(self, prompt: str) -> list:
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

        try:
            scenes = SCENE_RAW_ADAPTER.validate_python(data)
        except Exception as e:
            logger.warn(f"Scene validation failed: {e}")
            return []

        if len(scenes) < len(data):
            logger.warn(f"Kept {len(scenes)}/{len(data)} scenes from chunk")
        return scenes

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
