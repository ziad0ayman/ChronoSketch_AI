import numpy as np
from PIL import Image
from src.shared.config import CANVAS_WIDTH, CANVAS_HEIGHT

_BASE = (245, 238, 220)
_CACHE: Image.Image | None = None


def paper_background() -> Image.Image:
    global _CACHE
    if _CACHE is not None:
        return _CACHE.copy()
    rng = np.random.default_rng(42)
    canvas = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), _BASE)
    noise = rng.normal(0, 8, (CANVAS_HEIGHT, CANVAS_WIDTH, 3))
    arr = np.array(canvas, dtype=np.float32)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    _CACHE = Image.fromarray(arr)
    return _CACHE.copy()
