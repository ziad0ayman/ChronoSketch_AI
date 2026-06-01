"""
Debug Phase 4: The Hand — Tracer + Renderer timeline
Run: python debug_phase4.py
Writes output to debug_phase4_output.txt (UTF-8)
"""
import json
import io
import cairosvg
from PIL import Image
from pathlib import Path
from src.shared.models import SceneElement, AssetMatch
from src.shared.config import FPS
from src.hand.tracer import animate_svg, total_length as tracer_len

SCENES_PATH = "data/scenes/scenes.json"
ASSETS_PATH = "data/scenes/assets.json"
LOG_PATH = "debug_phase4_output.txt"

log_lines = []
def echo(s=""):
    log_lines.append(s)

# Step 1: Load scenes and assets
with open(SCENES_PATH) as f:
    elements = [SceneElement(**e) for e in json.load(f)]
with open(ASSETS_PATH) as f:
    assets = [AssetMatch(**a) for a in json.load(f)]
asset_map = {a.event_id: a for a in assets}

echo(f"Loaded {len(elements)} elements, {len(assets)} assets\n")

# Step 2: Show rendering timeline by scene
echo(f"{'#'*60}")
echo(f"RENDERING TIMELINE ({FPS} fps)")
echo(f"{'#'*60}")

scenes: dict[int, list[SceneElement]] = {}
for el in elements:
    scenes.setdefault(el.scene_id, []).append(el)
for elist in scenes.values():
    elist.sort(key=lambda e: e.start_time)

total_frames = 0
for sid in sorted(scenes):
    scene_els = scenes[sid]
    echo(f"\n  Scene {sid} ({len(scene_els)} elements):")
    for el in scene_els:
        duration = max(el.end_time - el.start_time, 0.1)
        n_frames = max(int(duration * FPS), 1)
        total_frames += n_frames
        echo(f"    #{el.element_id} | '{el.keyword}' | pos=({el.pos_x:.0f},{el.pos_y:.0f}) | "
             f"{el.start_time:.2f}-{el.end_time:.2f}s | {n_frames} frames")
echo(f"\n  Total element frames: {total_frames}")

last_end = max((e.end_time for e in elements), default=0)
needed = int(last_end * FPS)
echo(f"  Target frames ({last_end:.2f}s @ {FPS}fps): {needed}")
echo()

# Step 3: Pick first element with SVG and show tracer details
draw_elements = [(el, asset_map.get(el.element_id)) for el in elements
                 if el.element_id in asset_map and asset_map[el.element_id].svg_path]

if not draw_elements:
    echo("ERROR: No elements with SVGs found")
else:
    for el, asset in draw_elements[:3]:
        echo(f"{'='*60}")
        echo(f"TRACER: Element #{el.element_id} | keyword='{el.keyword}'")
        echo(f"        SVG: {asset.svg_path}")
        length = tracer_len(asset.svg_path)
        echo(f"        Total stroke length: {length:.2f}")

        for prog in [0.0, 0.5, 1.0]:
            svg = animate_svg(asset.svg_path, prog)
            png_bytes = cairosvg.svg2png(
                bytestring=svg.encode("utf-8"),
                output_width=1920, output_height=1080,
            )
            img = Image.open(io.BytesIO(png_bytes))
            echo(f"        progress={prog:.1f}: PNG={len(png_bytes)} bytes, size={img.size}")
        echo()

    for el, asset in draw_elements[3:]:
        echo(f"  Element #{el.element_id}: {el.keyword} -> {Path(asset.svg_path).name}")

# Step 4: Checks
echo(f"\n{'='*60}")
echo("CHECKS")
echo(f"{'='*60}")
elem_ids = sorted(set(e.element_id for e in elements))
asset_ids = sorted(set(a.event_id for a in assets))
missing = sorted(set(elem_ids) - set(asset_ids))
if missing:
    echo(f"  Elements missing assets: {missing}")
else:
    echo(f"  All {len(elements)} elements have assets")

unused = sorted(set(asset_ids) - set(elem_ids))
if unused:
    echo(f"  Assets without elements: {unused}")
else:
    echo(f"  No orphaned assets")

missing_svgs = [a.svg_path for a in assets if a.svg_path and not Path(a.svg_path).exists()]
if missing_svgs:
    echo(f"  Missing SVG files: {missing_svgs}")
else:
    echo(f"  All {len(assets)} SVG paths resolve to files")

with open(LOG_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(log_lines))
print(f"Output written to {LOG_PATH}")
