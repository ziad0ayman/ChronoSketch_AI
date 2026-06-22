import argparse
import json
import subprocess
from pathlib import Path

from src.shared.logger import logger
from src.shared.models import WordTimestamp, SceneElement
from src.ear.transcriber import Transcriber
from src.brain.orchestrator import Orchestrator
from src.library.retriever import Retriever
from src.hand.renderer import Renderer
from src.director.assembler import Assembler


def _get_audio_duration(path: str) -> float:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
            capture_output=True, text=True, check=True
        )
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
    except Exception as e:
        logger.warn(f"Could not determine audio duration: {e}")
        return 0.0


def _clamp_elements(elements: list[SceneElement], max_time: float) -> list[SceneElement]:
    clamped = []
    for el in elements:
        if el.start_time > max_time:
            logger.info(f"Dropping element {el.element_id} ('{el.keyword}'): start {el.start_time:.2f}s > max {max_time:.2f}s")
            continue
        el.end_time = min(el.end_time, max_time)
        clamped.append(el)
    return clamped


def _prompt(label: str, file_path: str, auto_yes: bool) -> None:
    print(f"\n  === {label} ===")
    print(f"  File saved to: {file_path}")
    if auto_yes:
        print("  Auto-continue (-y)")
        return
    while True:
        resp = input("  Press Enter to continue, 'q' to quit and edit manually: ").strip().lower()
        if resp == "q":
            print(f"\n  Edit the file above, then re-run with --skip-* to resume from this phase.")
            raise SystemExit(0)
        if resp == "":
            return


def _summarize_words(words: list[WordTimestamp]) -> None:
    print(f"\n  Transcript: {len(words)} words, "
          f"{words[0].start:.2f}s - {words[-1].end:.2f}s")
    for w in words:
        print(f"    {w.start:6.2f}s - {w.end:6.2f}s  {w.word}")


def _summarize_elements(elements: list[SceneElement]) -> None:
    scenes: dict[int, list[SceneElement]] = {}
    for el in elements:
        scenes.setdefault(el.scene_id, []).append(el)
    print(f"\n  Scenes: {len(scenes)}, Elements: {len(elements)}")
    for sid in sorted(scenes):
        els = scenes[sid]
        print(f"  Scene {sid} ({len(els)} elements):")
        for el in els:
            print(f"    #{el.element_id:>2} '{el.keyword:<20}' "
                  f"{el.start_time:.2f}-{el.end_time:.2f}s "
                  f"pos=({el.pos_x:.0f},{el.pos_y:.0f})")


def _summarize_assets(elements: list[SceneElement], assets: list) -> None:
    asset_map = {a.event_id: a for a in assets}
    missing = [el for el in elements if el.element_id not in asset_map or not asset_map[el.element_id].svg_path]
    print(f"\n  Assets: {len(assets)}, Elements with assets: {len(elements) - len(missing)}")
    for a in assets:
        el = next((e for e in elements if e.element_id == a.event_id), None)
        kw = el.keyword if el else "?"
        svg = Path(a.svg_path).name if a.svg_path else "NONE"
        print(f"    #{a.event_id:>2} '{kw:<20}' -> {svg}")
        if a.candidates:
            for rank, (fname, score) in enumerate(a.candidates[:5], 1):
                print(f"           #{rank}: {fname:30s} (score={score:.3f})")
        elif not a.svg_path:
            print(f"           NO CANDIDATES FOUND")
    if missing:
        print(f"  MISSING SVGs: {[el.keyword for el in missing]}")


def main():
    parser = argparse.ArgumentParser(description="ChronoSketch_AI — Automated Whiteboard Animation")
    parser.add_argument("--input", "-i", required=True, help="Input audio file (.mp3/.wav)")
    parser.add_argument("--output", "-o", default="data/output/output.mp4", help="Output video path")
    parser.add_argument("--yes", "-y", action="store_true", help="Non-interactive mode (no prompts)")
    parser.add_argument("--skip-stt", action="store_true", help="Skip Phase 1, use existing transcript")
    parser.add_argument("--skip-brain", action="store_true", help="Skip Phase 2, use existing scene plan")
    parser.add_argument("--skip-library", action="store_true", help="Skip Phase 3, use existing asset map")
    parser.add_argument("--skip-render", action="store_true", help="Skip Phase 4, assemble from existing frames")
    args = parser.parse_args()

    transcript_path = "data/transcripts/words.json"
    scenes_path = "data/scenes/scenes.json"
    assets_path = "data/scenes/assets.json"

    # Phase 1: Ear
    if not args.skip_stt:
        logger.info("=== Phase 1: The Ear ===")
        t = Transcriber()
        words = t.transcribe(args.input)
        t.save_timestamps(words, transcript_path)
        _summarize_words(words)
        _prompt("Phase 1 — Transcription", transcript_path, args.yes)
    else:
        words = Transcriber.load_timestamps(transcript_path)
        logger.info(f"Loaded {len(words)} words from {transcript_path}")

    # Determine true audio duration (from file, not Whisper hallucination)
    audio_duration = _get_audio_duration(args.input)
    if audio_duration > 0:
        total_duration = min(words[-1].end if words else 0.0, audio_duration)
        logger.info(f"Audio duration: {audio_duration:.2f}s, total_duration: {total_duration:.2f}s")
    else:
        total_duration = words[-1].end if words else 0.0

    # Phase 2: Brain
    if not args.skip_brain:
        logger.info("=== Phase 2: The Brain ===")
        o = Orchestrator()
        elements = o.plan_scenes(words)
        Path(scenes_path).parent.mkdir(parents=True, exist_ok=True)
        with open(scenes_path, "w") as f:
            json.dump([e.model_dump() for e in elements], f, indent=2)
        logger.info(f"Saved {len(elements)} scene elements to {scenes_path}")
        _summarize_elements(elements)
        _prompt("Phase 2 — Scene Plan", scenes_path, args.yes)
    else:
        with open(scenes_path) as f:
            elements = [SceneElement(**e) for e in json.load(f)]
        logger.info(f"Loaded {len(elements)} elements from {scenes_path}")

    # Clamp elements to audio duration (drops hallucinated post-audio scenes)
    elements = _clamp_elements(elements, total_duration)

    # Phase 3: Library
    if not args.skip_library:
        logger.info("=== Phase 3: The Library ===")
        r = Retriever()
        kw_pairs = [(e.element_id, e.keyword) for e in elements]
        assets = r.resolve_assets(kw_pairs)
        with open(assets_path, "w") as f:
            json.dump([a.model_dump() for a in assets], f, indent=2)
        _summarize_assets(elements, assets)
        _prompt("Phase 3 — Asset Library", assets_path, args.yes)
    else:
        from src.shared.models import AssetMatch
        with open(assets_path) as f:
            assets = [AssetMatch(**a) for a in json.load(f)]

    # Phase 4: Hand
    if not args.skip_render:
        logger.info("=== Phase 4: The Hand ===")
        renderer = Renderer()
        renderer.render_all(elements, assets, total_duration=total_duration, words=words)

    # Phase 5: Director
    logger.info("=== Phase 5: The Director ===")
    assembler = Assembler()
    output_path = assembler.assemble(args.input, args.output)
    logger.info(f"=== Done: {output_path} ===")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()
