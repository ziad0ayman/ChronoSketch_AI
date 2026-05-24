import argparse
import json
from pathlib import Path

from src.shared.logger import logger
from src.shared.models import WordTimestamp, SceneEvent
from src.ear.transcriber import Transcriber
from src.brain.orchestrator import Orchestrator
from src.library.retriever import Retriever
from src.hand.renderer import Renderer
from src.director.assembler import Assembler


def main():
    parser = argparse.ArgumentParser(description="ChronoSketch_AI — Automated Whiteboard Animation")
    parser.add_argument("--input", "-i", required=True, help="Input audio file (.mp3/.wav)")
    parser.add_argument("--output", "-o", default="data/output/output.mp4", help="Output video path")
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
    else:
        words = Transcriber.load_timestamps(transcript_path)
        logger.info(f"Loaded {len(words)} words from {transcript_path}")

    # Phase 2: Brain
    if not args.skip_brain:
        logger.info("=== Phase 2: The Brain ===")
        o = Orchestrator()
        events = o.plan_scenes(words)
        Path(scenes_path).parent.mkdir(parents=True, exist_ok=True)
        with open(scenes_path, "w") as f:
            json.dump([e.model_dump() for e in events], f, indent=2)
        logger.info(f"Saved {len(events)} scene events to {scenes_path}")
    else:
        with open(scenes_path) as f:
            events = [SceneEvent(**e) for e in json.load(f)]
        logger.info(f"Loaded {len(events)} events from {scenes_path}")

    # Phase 3: Library
    if not args.skip_library:
        logger.info("=== Phase 3: The Library ===")
        r = Retriever()
        kw_pairs = [(e.event_id, e.search_keyword) for e in events if e.action == "draw"]
        assets = r.resolve_assets(kw_pairs)
        with open(assets_path, "w") as f:
            json.dump([a.model_dump() for a in assets], f, indent=2)
    else:
        from src.shared.models import AssetMatch
        with open(assets_path) as f:
            assets = [AssetMatch(**a) for a in json.load(f)]

    # Phase 4: Hand
    if not args.skip_render:
        logger.info("=== Phase 4: The Hand ===")
        renderer = Renderer()
        total_duration = words[-1].end if words else 0.0
        renderer.render_all(events, assets, total_duration=total_duration)

    # Phase 5: Director
    logger.info("=== Phase 5: The Director ===")
    assembler = Assembler()
    output_path = assembler.assemble(args.input, args.output)
    logger.info(f"=== Done: {output_path} ===")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()
