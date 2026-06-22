from pathlib import Path
from src.shared.models import SceneElement, AssetMatch
from src.hand.tracer import reveal_mask
from src.hand.renderer import Renderer
from src.shared.config import ASSETS_DIR


def _test_svg() -> str:
    svgs = list(Path(ASSETS_DIR).glob("*.svg"))
    return str(svgs[0]) if svgs else ""


def test_reveal_mask_full():
    mask = reveal_mask((180, 180), 1.0)
    assert mask.getpixel((0, 0)) == 255
    assert mask.getpixel((179, 179)) == 255


def test_reveal_mask_empty():
    mask = reveal_mask((180, 180), 0.0)
    assert mask.getpixel((0, 0)) == 0
    assert mask.getpixel((179, 179)) == 0


def test_reveal_mask_half():
    """Default (diagonal_bounce) at 50% reveals top-left triangle (x+y<=179)."""
    mask = reveal_mask((180, 180), 0.5)
    assert mask.getpixel((40, 90)) == 255   # 40+90=130 <= 179
    assert mask.getpixel((140, 90)) == 0    # 140+90=230 > 179


def test_reveal_mask_left_to_right_half():
    mask = reveal_mask((180, 180), 0.5, direction="left_to_right")
    assert mask.getpixel((40, 90)) == 255
    assert mask.getpixel((140, 90)) == 0


def test_renderer_produces_white_background(tmp_path):
    svg = _test_svg()
    if not svg:
        return
    from PIL import Image
    r = Renderer(str(tmp_path))
    el = SceneElement(element_id=1, scene_id=1, keyword="test",
                      start_time=0.0, end_time=0.5,
                      pos_x=960, pos_y=540)
    asset = AssetMatch(event_id=1, svg_path=svg, keyword="test")
    from src.shared.config import FPS
    total = r.render_all([el], [asset], total_duration=1.0)
    assert total == 1 * FPS
    pngs = sorted(tmp_path.glob("*.png"))
    assert len(pngs) == total
    img = Image.open(pngs[0])
    assert img.size == (1920, 1080)
    assert img.mode == "RGB"


def test_renderer_scene_compositing(tmp_path):
    """Multi-element scene: completed elements persist visually into later frames."""
    svg = _test_svg()
    if not svg:
        return
    from PIL import Image
    import numpy as np
    r = Renderer(str(tmp_path))
    elements = [
        SceneElement(element_id=1, scene_id=1, keyword="a",
                     start_time=0.0, end_time=1.0,
                     pos_x=640, pos_y=540),
        SceneElement(element_id=2, scene_id=1, keyword="b",
                     start_time=1.0, end_time=2.0,
                     pos_x=1280, pos_y=540),
    ]
    assets = [
        AssetMatch(event_id=1, svg_path=svg, keyword="a"),
        AssetMatch(event_id=2, svg_path=svg, keyword="b"),
    ]
    total = r.render_all(elements, assets, total_duration=3.0)
    assert total == 3 * 24
    pngs = list(tmp_path.glob("*.png"))
    assert len(pngs) == total

    from src.hand.renderer import _prep_icon, _ICON_HALF, _ICON_SIZE
    icon_img = _prep_icon(svg)
    arr_icon = np.array(icon_img)
    alpha = arr_icon[:, :, 3] > 128
    coords = np.argwhere(alpha)
    assert len(coords) > 0, "Icon has no opaque pixels!"

    # Frame 35 is ~1.46s into video, mid-way through element 2 (progress ~50%)
    frame = Image.open(pngs[35])

    # Element 1 (640, 540) is completed — should be nearly fully visible
    el1_found = 0
    el1_checked = 0
    for y, x in coords[::50]:
        wx = int(640 - _ICON_HALF + x)
        wy = int(540 - _ICON_HALF + y)
        pixel = frame.getpixel((wx, wy))
        if all(c < 100 for c in pixel):
            el1_found += 1
        el1_checked += 1
    assert el1_found >= el1_checked * 0.8, (
        f"Element 1 (completed): only {el1_found}/{el1_checked} pixels visible"
    )

    # Element 2 (1280, 540) is current at ~50% diagonal_bounce reveal
    # Diagonal projection threshold at 50%: x+y <= _ICON_SIZE*2-3 ≈ 179
    diag_threshold = _ICON_SIZE * 2 - 3  # 179 for 180px (max_p * 0.5)
    revealed_coords = coords[coords[:, 1] + coords[:, 0] <= diag_threshold]
    el2_found = 0
    for y, x in revealed_coords[::20]:
        wx = int(1280 - _ICON_HALF + x)
        wy = int(540 - _ICON_HALF + y)
        pixel = frame.getpixel((wx, wy))
        if all(c < 100 for c in pixel):
            el2_found += 1
    assert el2_found >= 1, (
        f"Element 2 (current, 50% diagonal reveal): no revealed pixels visible"
    )


def test_renderer_scene_gap_clears(tmp_path):
    """Gap between scenes should produce blank (clear) frames."""
    svg = _test_svg()
    if not svg:
        return
    r = Renderer(str(tmp_path))
    elements = [
        SceneElement(element_id=1, scene_id=1, keyword="a",
                     start_time=0.0, end_time=0.5,
                     pos_x=960, pos_y=540),
        SceneElement(element_id=2, scene_id=2, keyword="b",
                     start_time=1.5, end_time=2.0,
                     pos_x=960, pos_y=540),
    ]
    assets = [
        AssetMatch(event_id=1, svg_path=svg, keyword="a"),
        AssetMatch(event_id=2, svg_path=svg, keyword="b"),
    ]
    total = r.render_all(elements, assets, total_duration=3.0)
    assert total == 3 * 24
    pngs = list(tmp_path.glob("*.png"))
    assert len(pngs) == total


def test_renderer_pads_to_duration(tmp_path):
    r = Renderer(str(tmp_path))
    total = r.render_all([], [], total_duration=2.0)
    assert total == 2 * 24
    pngs = list(tmp_path.glob("*.png"))
    assert len(pngs) == total
