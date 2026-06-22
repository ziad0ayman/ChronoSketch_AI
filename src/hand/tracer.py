import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

_REVEAL_DIRECTIONS = ("left_to_right", "right_to_left", "top_to_bottom", "bottom_to_top", "center_out", "diagonal_bounce", "pen_path")
_BLUR_RADIUS = 3
_DIAGONAL_CYCLES = 3
_PEN_MARGIN = 8
_PEN_WIDTH = 14
_PEN_STROKES = 8


def reveal_mask(size: tuple[int, int], progress: float, direction: str = "pen_path") -> Image.Image:
    progress = max(0.0, min(1.0, progress))
    w, h = size
    if progress >= 1.0:
        return Image.new("L", size, 255)
    if progress <= 0.0:
        return Image.new("L", size, 0)

    if direction == "pen_path":
        return _pen_path_mask(w, h, progress)
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


def _pen_path_mask(w: int, h: int, progress: float) -> Image.Image:
    path = _generate_pen_path(w, h)
    total_len = sum(math.dist(path[i], path[i + 1]) for i in range(len(path) - 1))
    target_len = total_len * progress

    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)

    accumulated = 0.0
    for i in range(len(path) - 1):
        seg_len = math.dist(path[i], path[i + 1])
        if accumulated + seg_len >= target_len:
            frac = (target_len - accumulated) / seg_len
            mx = path[i][0] + (path[i + 1][0] - path[i][0]) * frac
            my = path[i][1] + (path[i + 1][1] - path[i][1]) * frac
            draw.line([path[i], (mx, my)], fill=255, width=_PEN_WIDTH)
            break
        draw.line([path[i], path[i + 1]], fill=255, width=_PEN_WIDTH)
        accumulated += seg_len

    return mask.filter(ImageFilter.BoxBlur(_BLUR_RADIUS))


def _generate_pen_path(w: int, h: int) -> list[tuple[float, float]]:
    points = [(_PEN_MARGIN, _PEN_MARGIN + 8)]
    x, y = points[0]

    for i in range(_PEN_STROKES):
        if i % 2 == 0:
            angle = 45 + (i // 2) * 3
            rad = math.radians(angle)
            dx, dy = math.cos(rad), -math.sin(rad)
            t = float("inf")
            if dx > 0:
                t = min(t, (w - 1 - x) / dx)
            if dy < 0:
                t = min(t, y / -dy)
        else:
            angle = 60 + (i // 2) * 3
            rad = math.radians(angle)
            dx, dy = -math.cos(rad), math.sin(rad)
            t = float("inf")
            if dx < 0:
                t = min(t, x / -dx)
            if dy > 0:
                t = min(t, (h - 1 - y) / dy)

        x = x + dx * t
        y = y + dy * t
        points.append((x, y))

    return points


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
