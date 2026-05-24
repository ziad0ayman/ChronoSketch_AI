"""
Debug Phase 4: The Hand — Tracer (SVG path animation) + Renderer timeline
Run: python debug_phase4.py
Writes output to debug_phase4_output.txt (UTF-8)
"""
import json
import io
import cairosvg
from PIL import Image
from pathlib import Path
from src.shared.models import SceneEvent, AssetMatch
from src.shared.config import FPS
from src.hand.tracer import Tracer

SCENES_PATH = "data/scenes/scenes.json"
ASSETS_PATH = "data/scenes/assets.json"
LOG_PATH = "debug_phase4_output.txt"

log_lines = []
def echo(s=""):
    log_lines.append(s)

# Step 1: Load scenes and assets
with open(SCENES_PATH) as f:
    events = [SceneEvent(**e) for e in json.load(f)]
with open(ASSETS_PATH) as f:
    assets = [AssetMatch(**a) for a in json.load(f)]
asset_map = {a.event_id: a for a in assets}

echo(f"Loaded {len(events)} events, {len(assets)} assets\n")

# Step 2: Show rendering timeline
echo(f"{'#'*60}")
echo(f"RENDERING TIMELINE ({FPS} fps)")
echo(f"{'#'*60}")
echo(f"{'Evt':>4} {'Action':<14} {'Keyword':<25} {'Time range':<18} {'Frames':>6}")
echo("-" * 70)

total_frames = 0
last_end_time = 0.0
gap_total = 0

echo(f"{'Gap?':>6} {'':>4}")
for ev in events:
    gap = ev.start_time - last_end_time
    gap_frames = 0
    if gap > 0.01:
        gap_frames = int(gap * FPS)
        gap_total += gap_frames
        echo(f"  PERSIST{'':<14} {'(time gap, persist)':<25} {last_end_time:.2f}-{ev.start_time:.2f}s {gap_frames:>5}")
    duration = max(ev.end_time - ev.start_time, 0.1)
    n_frames = max(int(duration * FPS), 1)
    kw = ev.search_keyword if ev.search_keyword else "-"
    echo(f"         {ev.event_id:>2} {ev.action:<14} {kw:<25} {ev.start_time:.2f}-{ev.end_time:.2f}s {n_frames:>5}")
    total_frames += n_frames
    last_end_time = max(last_end_time, ev.end_time)

echo(f"\n  Event frames: {total_frames}")
echo(f"  Gap frames: {gap_total}")

last_end = max((e.end_time for e in events), default=0)
needed = int(last_end * FPS)
echo(f"  Target frames ({last_end:.2f}s @ {FPS}fps): {needed}")
if needed > total_frames + gap_total:
    echo(f"  Final padding: {needed - total_frames - gap_total} blank white frames")
echo()

# Step 3: Pick a draw event with an SVG and show tracer details
draw_assets = [(ev, asset_map.get(ev.event_id)) for ev in events
               if ev.action == "draw" and ev.event_id in asset_map and asset_map[ev.event_id].svg_path]

if not draw_assets:
    echo("ERROR: No draw events with SVGs found")
else:
    # Show tracer info for first 3 SVGs
    for ev, asset in draw_assets[:3]:
        echo(f"{'='*60}")
        echo(f"TRACER: Event #{ev.event_id} | keyword='{ev.search_keyword}'")
        echo(f"        SVG: {asset.svg_path}")
        tracer = Tracer(asset.svg_path)
        echo(f"        Paths: {len(tracer._paths)}, total length: {tracer.total_length:.2f}")
        for idx, (d, plen) in enumerate(zip(tracer._d_attrs, tracer._lengths)):
            echo(f"        Path #{idx}: d(len={len(d)}) length={plen:.2f}")

        # Render at progress 0.0, 0.5, 1.0 and show output PNG sizes
        for prog in [0.0, 0.5, 1.0]:
            svg = tracer.render_svg_at(prog)
            # compute byte size of rendered PNG (don't save to disk)
            png_bytes = cairosvg.svg2png(
                bytestring=svg.encode("utf-8"),
                output_width=1920, output_height=1080,
            )
            img = Image.open(io.BytesIO(png_bytes))
            echo(f"        progress={prog:.1f}: PNG={len(png_bytes)} bytes, size={img.size}")
        echo()

    # Show remaining events summary
    for ev, asset in draw_assets[3:]:
        echo(f"  Event #{ev.event_id}: {ev.search_keyword} -> {Path(asset.svg_path).name}")

# Step 4: Check for issues
echo(f"\n{'='*60}")
echo("CHECKS")
echo(f"{'='*60}")
event_ids = sorted(set(e.event_id for e in events))
asset_ids = sorted(set(a.event_id for a in assets))
missing = sorted(set(event_ids) - set(asset_ids))
if missing:
    echo(f"  Events missing assets: {missing}")
else:
    echo(f"  All {len(events)} events have assets")

unused = sorted(set(asset_ids) - set(event_ids))
if unused:
    echo(f"  Assets without events: {unused}")
else:
    echo(f"  No orphaned assets")

# Verify SVG files exist
missing_svgs = [a.svg_path for a in assets if a.svg_path and not Path(a.svg_path).exists()]
if missing_svgs:
    echo(f"  Missing SVG files: {missing_svgs}")
else:
    echo(f"  All {len(assets)} SVG paths resolve to files")

with open(LOG_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(log_lines))
print(f"Output written to {LOG_PATH}")
