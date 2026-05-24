import io
import shutil
from pathlib import Path
import cairosvg
from PIL import Image
from src.shared.logger import logger
from src.shared.models import SceneEvent, AssetMatch
from src.shared.config import FPS, CANVAS_WIDTH, CANVAS_HEIGHT
from src.hand.tracer import Tracer

_BLANK_SVG = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_WIDTH}" height="{CANVAS_HEIGHT}">
  <rect width="100%" height="100%" fill="white"/>
</svg>"""


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
        bg = Image.new("RGBA", img.size, "WHITE")
        if img.mode == "RGBA":
            bg.paste(img, (0, 0), img)
        else:
            bg.paste(img, (0, 0))
        png_path = self._output_dir / f"frame_{frame_idx:06d}.png"
        bg.convert("RGB").save(png_path, "PNG")

    def render_event(self, event: SceneEvent, asset: AssetMatch | None, frame_offset: int) -> int:
        duration = max(event.end_time - event.start_time, 0.1)
        n_frames = max(int(duration * FPS), 1)

        if event.action == "clear_canvas":
            for i in range(n_frames):
                self._render_svg_to_png(_BLANK_SVG, frame_offset + i)
            logger.info(f"Clear canvas: {n_frames} blank frames")
            return n_frames

        if asset is None or not asset.svg_path:
            logger.warn(f"No SVG for event {event.event_id}; rendering blank")
            for i in range(n_frames):
                self._render_svg_to_png(_BLANK_SVG, frame_offset + i)
            return n_frames

        tracer = Tracer(asset.svg_path)
        for i in range(n_frames):
            t = event.start_time + (i / n_frames) * duration
            progress = (t - event.start_time) / duration
            svg_xml = tracer.render_svg_at(progress)
            self._render_svg_to_png(svg_xml, frame_offset + i)
        logger.info(f"Event {event.event_id}: {n_frames} frames rendered")
        return n_frames

    def _copy_frame(self, src_idx: int, dst_idx: int) -> None:
        src = self._output_dir / f"frame_{src_idx:06d}.png"
        dst = self._output_dir / f"frame_{dst_idx:06d}.png"
        shutil.copy2(src, dst)

    def render_all(self, events: list[SceneEvent], assets: list[AssetMatch], total_duration: float = 0.0) -> int:
        asset_map = {a.event_id: a for a in assets}
        total = 0
        last_end_time = 0.0
        for ev in events:
            gap = ev.start_time - last_end_time
            if gap > 0.01:
                gap_frames = int(gap * FPS)
                for i in range(gap_frames):
                    if total > 0:
                        self._copy_frame(total - 1, total + i)
                    else:
                        self._render_svg_to_png(_BLANK_SVG, total + i)
                total += gap_frames
                logger.info(f"Gap: {gap_frames} frames ({gap:.2f}s)")
            a = asset_map.get(ev.event_id)
            total += self.render_event(ev, a, total)
            last_end_time = max(last_end_time, ev.end_time)
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
