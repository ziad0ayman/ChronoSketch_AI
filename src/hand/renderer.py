import io
import shutil
from pathlib import Path
import cairosvg
from PIL import Image
from src.shared.logger import logger
from src.shared.models import SceneElement, AssetMatch
from src.shared.config import FPS, CANVAS_WIDTH, CANVAS_HEIGHT
from src.hand.tracer import animate_svg
from src.hand.layout import icon_size
from src.hand.texture import paper_background

_BLANK_SVG = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_WIDTH}" height="{CANVAS_HEIGHT}">
  <rect width="100%" height="100%" fill="white"/>
</svg>"""

_ICON_SIZE = icon_size()
_ICON_HALF = _ICON_SIZE // 2
_MIN_ELEMENT_DURATION = 0.1


def _render_svg_to_image(svg_xml: str, width: int, height: int) -> Image.Image:
    png_bytes = cairosvg.svg2png(
        bytestring=svg_xml.encode("utf-8"),
        output_width=width,
        output_height=height,
    )
    img = Image.open(io.BytesIO(png_bytes))
    return img.convert("RGBA") if img.mode != "RGBA" else img


def _prep_icon(svg_path: str, anim_progress: float | None = None) -> tuple[str, Image.Image]:
    """Return (svg_xml, rendered RGBA image) for an icon at _ICON_SIZE."""
    if anim_progress is not None:
        svg = animate_svg(svg_path, anim_progress)
    else:
        with open(svg_path) as f:
            svg = f.read()
    svg = svg.replace('width="24"', f'width="{_ICON_SIZE}"')
    svg = svg.replace('height="24"', f'height="{_ICON_SIZE}"')
    svg = svg.replace('stroke="currentColor"', 'stroke="black"')
    img = _render_svg_to_image(svg, _ICON_SIZE, _ICON_SIZE)
    return svg, img


class Renderer:
    def __init__(self, output_dir: str = "data/frames"):
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def _render_svg_to_png(self, svg_xml: str, frame_idx: int) -> None:
        png_bytes = cairosvg.svg2png(
            bytestring=svg_xml.encode("utf-8"),
            output_width=CANVAS_WIDTH,
            output_height=CANVAS_HEIGHT,
        )
        img = Image.open(io.BytesIO(png_bytes))
        bg = paper_background().convert("RGBA")
        bg.paste(img, (0, 0), img if img.mode == "RGBA" else None)
        png_path = self._output_dir / f"frame_{frame_idx:06d}.png"
        bg.convert("RGB").save(png_path, "PNG")

    def _save_frame(self, canvas: Image.Image, frame_idx: int) -> None:
        png_path = self._output_dir / f"frame_{frame_idx:06d}.png"
        canvas.convert("RGB").save(png_path, "PNG")

    def _render_scene(self, elements: list[SceneElement], asset_map: dict, frame_offset: int) -> int:
        total = 0

        # Pre-render fully-drawn icons for ALL elements in this scene
        full_icons: dict[int, Image.Image] = {}
        for el in elements:
            asset = asset_map.get(el.element_id)
            if asset and asset.svg_path:
                _, img = _prep_icon(asset.svg_path)
                full_icons[el.element_id] = img

        for idx, el in enumerate(elements):
            duration = max(el.end_time - el.start_time, _MIN_ELEMENT_DURATION)
            n_frames = max(int(duration * FPS), 1)

            for j in range(n_frames):
                progress = (j + 1) / n_frames
                canvas = paper_background().convert("RGBA")

                # Paste all completed (previous) icons — fully drawn
                for prev_el in elements[:idx]:
                    if prev_el.element_id in full_icons:
                        tx = int(prev_el.pos_x - _ICON_HALF)
                        ty = int(prev_el.pos_y - _ICON_HALF)
                        canvas.paste(full_icons[prev_el.element_id], (tx, ty),
                                     full_icons[prev_el.element_id])

                # Paste current element — animated
                asset = asset_map.get(el.element_id)
                if asset and asset.svg_path:
                    _, cur_img = _prep_icon(asset.svg_path, anim_progress=progress)
                    tx = int(el.pos_x - _ICON_HALF)
                    ty = int(el.pos_y - _ICON_HALF)
                    canvas.paste(cur_img, (tx, ty), cur_img)

                self._save_frame(canvas, frame_offset + total + j)

            total += n_frames
            logger.info(f"Element {el.element_id}: {n_frames} frames rendered")

        return total

    def _copy_frame(self, src_idx: int, dst_idx: int) -> None:
        src = self._output_dir / f"frame_{src_idx:06d}.png"
        dst = self._output_dir / f"frame_{dst_idx:06d}.png"
        shutil.copy2(src, dst)

    def render_all(self, elements: list[SceneElement], assets: list[AssetMatch], total_duration: float = 0.0) -> int:
        asset_map = {a.event_id: a for a in assets}
        total = 0

        scenes: dict[int, list[SceneElement]] = {}
        for el in elements:
            scenes.setdefault(el.scene_id, []).append(el)
        for elist in scenes.values():
            elist.sort(key=lambda e: e.start_time)

        scene_ids = sorted(scenes.keys())
        last_end = 0.0

        for sid in scene_ids:
            scene_els = scenes[sid]
            scene_start = scene_els[0].start_time
            scene_end = scene_els[-1].end_time

            gap = scene_start - last_end
            if gap > 0.01 and total > 0:
                gap_frames = int(gap * FPS)
                for i in range(gap_frames):
                    self._copy_frame(total - 1, total + i)
                total += gap_frames
                logger.info(f"Gap before scene {sid}: {gap_frames} persist frames ({gap:.2f}s)")
            elif gap > 0.01 and total == 0:
                gap_frames = int(gap * FPS)
                for i in range(gap_frames):
                    self._render_svg_to_png(_BLANK_SVG, total + i)
                total += gap_frames
                logger.info(f"Gap before scene {sid}: {gap_frames} blank frames ({gap:.2f}s)")

            total += self._render_scene(scene_els, asset_map, total)
            last_end = max(last_end, scene_end)

        needed = int(total_duration * FPS)
        if needed > total:
            logger.info(f"Padding with {needed - total} frames to match {total_duration:.1f}s")
            for i in range(total, needed):
                if total > 0:
                    self._copy_frame(total - 1, i)
                else:
                    self._render_svg_to_png(_BLANK_SVG, i)
            total = needed

        logger.info(f"Total frames rendered: {total}")
        return total
