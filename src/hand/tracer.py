import numpy as np
from PIL import Image, ImageDraw, ImageFilter

_REVEAL_DIRECTIONS = ("left_to_right", "right_to_left", "top_to_bottom", "bottom_to_top", "center_out", "diagonal_bounce")
_BLUR_RADIUS = 4
_DIAGONAL_CYCLES = 3


def reveal_mask(size: tuple[int, int], progress: float, direction: str = "diagonal_bounce") -> Image.Image:
    progress = max(0.0, min(1.0, progress))
    w, h = size
    if progress >= 1.0:
        return Image.new("L", size, 255)
    if progress <= 0.0:
        return Image.new("L", size, 0)

    if direction == "diagonal_bounce":
        return _diagonal_bounce_mask(w, h, progress)

    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)

    if direction == "left_to_right":
        draw.rectangle([0, 0, int(w * progress), h], fill=255)
    elif direction == "right_to_left":
        draw.rectangle([w - int(w * progress), 0, w, h], fill=255)
    elif direction == "top_to_bottom":
        draw.rectangle([0, 0, w, int(h * progress)], fill=255)
    elif direction == "bottom_to_top":
        draw.rectangle([0, h - int(h * progress), w, h], fill=255)
    elif direction == "center_out":
        cx, cy = w // 2, h // 2
        r = int(max(w, h) * progress)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)

    return mask.filter(ImageFilter.BoxBlur(_BLUR_RADIUS))


def _diagonal_bounce_mask(w: int, h: int, progress: float) -> Image.Image:
    max_p = w + h - 2
    n_halves = _DIAGONAL_CYCLES * 2
    revealed = min(n_halves, progress * n_halves)
    threshold_p = max_p * (revealed / n_halves)

    xv, yv = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    proj = xv + yv
    arr = np.where(proj <= threshold_p, 255, 0).astype(np.uint8)
    mask = Image.fromarray(arr, mode="L")
    return mask.filter(ImageFilter.BoxBlur(_BLUR_RADIUS))
