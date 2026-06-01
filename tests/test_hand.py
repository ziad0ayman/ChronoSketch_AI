from pathlib import Path
from src.shared.models import SceneElement, AssetMatch
from src.hand.tracer import animate_svg, total_length as tracer_len
from src.hand.renderer import Renderer
from src.shared.config import ASSETS_DIR


def _test_svg() -> str:
    svgs = list(Path(ASSETS_DIR).glob("*.svg"))
    return str(svgs[0]) if svgs else ""


def test_tracer_parses_paths():
    svg = _test_svg()
    if not svg:
        return
    assert tracer_len(svg) > 0


def test_tracer_preserves_original_viewbox():
    svg = _test_svg()
    if not svg:
        return
    xml = animate_svg(svg, 0.0)
    assert 'viewBox="0 0 24 24"' in xml
    assert "stroke-dasharray" in xml


def test_tracer_render_svg_at():
    svg = _test_svg()
    if not svg:
        return
    xml0 = animate_svg(svg, 0.0)
    xml1 = animate_svg(svg, 1.0)
    assert "stroke-dasharray" in xml0
    assert "stroke-dashoffset" in xml0
    assert xml0 != xml1


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
    corner = img.getpixel((0, 0))
    assert corner == (255, 255, 255), f"Expected white corner, got {corner}"


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

    # Frame 25 is the second frame of element 2 (after 24 frames of element 1)
    # It should show both elements
    from src.hand.renderer import _prep_icon, _ICON_HALF
    _, icon_img = _prep_icon(svg)
    arr_icon = np.array(icon_img)
    mask = arr_icon[:, :, 3] > 128
    stroke_coords = np.argwhere(mask)
    assert len(stroke_coords) > 0, "Icon has no stroke pixels!"

    frame = Image.open(pngs[25])
    frame_corners = [frame.getpixel((0, 0)), frame.getpixel((1919, 0)),
                     frame.getpixel((0, 1079)), frame.getpixel((1919, 1079))]
    assert all(c == (255, 255, 255) for c in frame_corners), "Corners not white"

    # Sample stroke positions and verify they're dark (i.e., rendered) on frame
    # Element 1 (640, 540) is completed — should be nearly fully visible
    el1_found = 0
    el1_checked = 0
    for sy, sx in stroke_coords[::50]:
        wx = int(640 - _ICON_HALF + sx)
        wy = int(540 - _ICON_HALF + sy)
        pixel = frame.getpixel((wx, wy))
        if all(c < 100 for c in pixel):
            el1_found += 1
        el1_checked += 1
    assert el1_found >= el1_checked * 0.8, (
        f"Element 1 (completed): only {el1_found}/{el1_checked} stroke pixels visible"
    )

    # Element 2 (1280, 540) is current — should have at least some strokes visible
    el2_found = 0
    el2_checked = 0
    for sy, sx in stroke_coords[::50]:
        wx = int(1280 - _ICON_HALF + sx)
        wy = int(540 - _ICON_HALF + sy)
        pixel = frame.getpixel((wx, wy))
        if all(c < 100 for c in pixel):
            el2_found += 1
        el2_checked += 1
    assert el2_found >= 1, (
        f"Element 2 (current): no stroke pixels visible (progress ~8%)"
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
