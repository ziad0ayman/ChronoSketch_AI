import io
import shutil
from pathlib import Path
import cairosvg
from PIL import Image, ImageDraw, ImageFont
from src.shared.logger import logger
from src.shared.models import SceneElement, AssetMatch, WordTimestamp
from src.shared.config import FPS, CANVAS_WIDTH, CANVAS_HEIGHT
from src.hand.tracer import reveal_mask
from src.hand.layout import icon_size
from src.hand.texture import paper_background
from src.shared.config import REVEAL_DIRECTION

_BLANK_SVG = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_WIDTH}" height="{CANVAS_HEIGHT}">
  <rect width="100%" height="100%" fill="white"/>
</svg>"""

_ICON_SIZE = icon_size()
_ICON_HALF = _ICON_SIZE // 2
_MIN_ELEMENT_DURATION = 0.1
_CAPTION_FONT_SIZE = 30
_CAPTION_PAD = 10
_CAPTION_WINDOW = 8
_CAPTION_MARGIN_BOTTOM = 70

_CAPTION_FONT: ImageFont.ImageFont | None = None


def _get_caption_font() -> ImageFont.ImageFont:
    global _CAPTION_FONT
    if _CAPTION_FONT is not None:
        return _CAPTION_FONT
    for name in ("segoeui.ttf", "arial.ttf", "calibri.ttf"):
        try:
            _CAPTION_FONT = ImageFont.truetype(name, _CAPTION_FONT_SIZE)
            return _CAPTION_FONT
        except (IOError, OSError):
            continue
    _CAPTION_FONT = ImageFont.load_default()
    return _CAPTION_FONT


def _render_captions(canvas: Image.Image, words: list[WordTimestamp], current_time: float) -> None:
    if not words:
        return

    current_idx = -1
    for i, w in enumerate(words):
        if w.start <= current_time <= w.end:
            current_idx = i
            break
    if current_idx < 0:
        return

    font = _get_caption_font()
    cw, ch = canvas.size

    window_start = max(0, current_idx - _CAPTION_WINDOW)
    parts = [words[i].word for i in range(window_start, current_idx + 1)]
    full_text = " ".join(parts)

    bbox = canvas.getbbox() or (0, 0, 0, 0)
    full_bbox = ImageDraw.Draw(canvas).textbbox((0, 0), full_text, font=font)
    text_w = full_bbox[2] - full_bbox[0]
    text_h = full_bbox[3] - full_bbox[1]

    x = (cw - text_w) // 2
    y = ch - _CAPTION_MARGIN_BOTTOM - text_h

    bg = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    bg_draw = ImageDraw.Draw(bg)
    bg_draw.rectangle(
        [x - _CAPTION_PAD, y - _CAPTION_PAD, x + text_w + _CAPTION_PAD, y + text_h + _CAPTION_PAD],
        fill=(255, 255, 255, 220),
    )
    canvas.paste(bg, (0, 0), bg)

    draw = ImageDraw.Draw(canvas)
    prefix = ""
    for i in range(window_start, current_idx + 1):
        w = words[i]
        word_text = w.word
        pbox = draw.textbbox((0, 0), prefix, font=font)
        wx = x + (pbox[2] - pbox[0])
        if prefix:
            wx += draw.textbbox((0, 0), " ", font=font)[2] - draw.textbbox((0, 0), " ", font=font)[0]

        color = (120, 120, 120) if i < current_idx else (30, 30, 30)
        draw.text((wx, y), word_text, fill=color, font=font)

        if i == current_idx:
            wbox = draw.textbbox((0, 0), word_text, font=font)
            ww = wbox[2] - wbox[0]
            draw.line([(wx, y + text_h + 2), (wx + ww, y + text_h + 2)], fill=(50, 110, 200), width=2)

        prefix = prefix + (" " if prefix else "") + word_text


def _render_svg_to_image(svg_xml: str, width: int, height: int) -> Image.Image:
    png_bytes = cairosvg.svg2png(
        bytestring=svg_xml.encode("utf-8"),
        output_width=width,
        output_height=height,
    )
    img = Image.open(io.BytesIO(png_bytes))
    return img.convert("RGBA") if img.mode != "RGBA" else img


def _prep_icon(svg_path: str) -> Image.Image:
    """Render an SVG icon to an RGBA PIL Image at _ICON_SIZE."""
    with open(svg_path) as f:
        svg = f.read()
    svg = svg.replace('width="24"', f'width="{_ICON_SIZE}"')
    svg = svg.replace('height="24"', f'height="{_ICON_SIZE}"')
    svg = svg.replace('stroke="currentColor"', 'stroke="black"')
    return _render_svg_to_image(svg, _ICON_SIZE, _ICON_SIZE)


class Renderer:
    def __init__(self, output_dir: str = "data/frames"):
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def _save_frame(self, canvas: Image.Image, frame_idx: int) -> None:
        png_path = self._output_dir / f"frame_{frame_idx:06d}.png"
        canvas.convert("RGB").save(png_path, "PNG")

    def _annotate_frame(self, frame_idx: int) -> None:
        if not self._words:
            return
        png_path = self._output_dir / f"frame_{frame_idx:06d}.png"
        img = Image.open(png_path).convert("RGBA")
        _render_captions(img, self._words, frame_idx / FPS)
        img.convert("RGB").save(png_path, "PNG")

    def _save_blank_frame(self, frame_idx: int) -> None:
        canvas = paper_background().convert("RGBA")
        _render_captions(canvas, self._words or [], frame_idx / FPS)
        self._save_frame(canvas, frame_idx)

    def _render_scene(self, elements: list[SceneElement], asset_map: dict, frame_offset: int) -> int:
        words = self._words or []
        total = 0

        # Pre-render fully-drawn icons for ALL elements in this scene
        full_icons: dict[int, Image.Image] = {}
        for el in elements:
            asset = asset_map.get(el.element_id)
            if asset and asset.svg_path:
                full_icons[el.element_id] = _prep_icon(asset.svg_path)

        _transparent = Image.new("RGBA", (_ICON_SIZE, _ICON_SIZE), (0, 0, 0, 0))

        for idx, el in enumerate(elements):
            duration = max(el.end_time - el.start_time, _MIN_ELEMENT_DURATION)
            n_frames = max(int(duration * FPS), 1)
            full_img = full_icons.get(el.element_id)
            tx = int(el.pos_x - _ICON_HALF)
            ty = int(el.pos_y - _ICON_HALF)

            for j in range(n_frames):
                progress = (j + 1) / n_frames
                canvas = paper_background().convert("RGBA")

                # Paste all completed (previous) icons — fully drawn
                for prev_el in elements[:idx]:
                    if prev_el.element_id in full_icons:
                        ptx = int(prev_el.pos_x - _ICON_HALF)
                        pty = int(prev_el.pos_y - _ICON_HALF)
                        canvas.paste(full_icons[prev_el.element_id], (ptx, pty),
                                     full_icons[prev_el.element_id])

                # Paste current element — revealed via mask wipe
                if full_img:
                    mask = reveal_mask((_ICON_SIZE, _ICON_SIZE), progress, REVEAL_DIRECTION)
                    revealed = Image.composite(full_img, _transparent, mask)
                    canvas.paste(revealed, (tx, ty), revealed)

                frame_idx = frame_offset + total + j
                _render_captions(canvas, words, frame_idx / FPS)
                self._save_frame(canvas, frame_idx)

            total += n_frames
            logger.info(f"Element {el.element_id}: {n_frames} frames rendered")

        return total

    def _copy_frame(self, src_idx: int, dst_idx: int) -> None:
        src = self._output_dir / f"frame_{src_idx:06d}.png"
        dst = self._output_dir / f"frame_{dst_idx:06d}.png"
        shutil.copy2(src, dst)

    def render_all(self, elements: list[SceneElement], assets: list[AssetMatch], total_duration: float = 0.0,
                   words: list[WordTimestamp] | None = None) -> int:
        self._words = words
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
                    self._annotate_frame(total + i)
                total += gap_frames
                logger.info(f"Gap before scene {sid}: {gap_frames} persist frames ({gap:.2f}s)")
            elif gap > 0.01 and total == 0:
                gap_frames = int(gap * FPS)
                for i in range(gap_frames):
                    self._save_blank_frame(total + i)
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
                    self._annotate_frame(i)
                else:
                    self._save_blank_frame(i)
            total = needed

        logger.info(f"Total frames rendered: {total}")
        return total
