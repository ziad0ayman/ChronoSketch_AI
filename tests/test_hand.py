from pathlib import Path
from src.shared.models import SceneEvent, AssetMatch
from src.hand.tracer import Tracer
from src.hand.renderer import Renderer
from src.shared.config import ASSETS_DIR


def _test_svg() -> str:
    svgs = list(Path(ASSETS_DIR).glob("*.svg"))
    return str(svgs[0]) if svgs else ""


def test_tracer_parses_paths():
    svg = _test_svg()
    if not svg:
        return
    t = Tracer(svg)
    assert t.total_length > 0


def test_tracer_preserves_original_viewbox():
    svg = _test_svg()
    if not svg:
        return
    t = Tracer(svg)
    xml = t.render_svg_at(0.0)
    assert 'viewBox="0 0 24 24"' in xml
    assert "stroke-dasharray" in xml


def test_renderer_produces_white_background(tmp_path):
    svg = _test_svg()
    if not svg:
        return
    from src.shared.models import SceneEvent, AssetMatch
    from src.shared.config import FPS
    r = Renderer(str(tmp_path))
    ev = SceneEvent(event_id=1, action="draw", start_time=0.0, end_time=0.5,
                    search_keyword="test")
    asset = AssetMatch(event_id=1, svg_path=svg, keyword="test")
    n = r.render_event(ev, asset, 0)
    from PIL import Image
    pngs = list(tmp_path.glob("*.png"))
    assert len(pngs) == n
    img = Image.open(pngs[0])
    assert img.size == (1920, 1080)
    assert img.mode == "RGB"
    corner = img.getpixel((0, 0))
    assert corner == (255, 255, 255), f"Expected white corner, got {corner}"


def test_tracer_render_svg_at():
    svg = _test_svg()
    if not svg:
        return
    t = Tracer(svg)
    xml0 = t.render_svg_at(0.0)
    xml1 = t.render_svg_at(1.0)
    assert "stroke-dasharray" in xml0
    assert "stroke-dashoffset" in xml0
    assert xml0 != xml1


def test_renderer_clear_canvas(tmp_path):
    r = Renderer(str(tmp_path))
    ev = SceneEvent(
        event_id=1, action="clear_canvas",
        start_time=0.0, end_time=1.0,
        search_keyword="",
    )
    n = r.render_event(ev, None, 0)
    assert n > 0
    pngs = list(tmp_path.glob("*.png"))
    assert len(pngs) == n


def test_renderer_draw_event(tmp_path):
    svg = _test_svg()
    if not svg:
        return
    r = Renderer(str(tmp_path))
    ev = SceneEvent(
        event_id=1, action="draw",
        start_time=0.0, end_time=2.0,
        search_keyword="test",
    )
    asset = AssetMatch(event_id=1, svg_path=svg, keyword="test")
    n = r.render_event(ev, asset, 0)
    assert n > 0
    pngs = list(tmp_path.glob("*.png"))
    assert len(pngs) == n


def test_renderer_all(tmp_path):
    svg = _test_svg()
    if not svg:
        return
    r = Renderer(str(tmp_path))
    events = [
        SceneEvent(event_id=1, action="draw", start_time=0.0, end_time=1.0,
                   search_keyword="a"),
        SceneEvent(event_id=2, action="clear_canvas", start_time=1.0, end_time=1.5,
                   search_keyword=""),
        SceneEvent(event_id=3, action="draw", start_time=1.5, end_time=2.5,
                   search_keyword="b"),
    ]
    assets = [
        AssetMatch(event_id=1, svg_path=svg, keyword="a"),
        AssetMatch(event_id=3, svg_path=svg, keyword="b"),
    ]
    total = r.render_all(events, assets, total_duration=5.0)
    assert total == 5 * 24
    pngs = list(tmp_path.glob("*.png"))
    assert len(pngs) == total


def test_renderer_pads_to_duration(tmp_path):
    r = Renderer(str(tmp_path))
    total = r.render_all([], [], total_duration=2.0)
    assert total == 2 * 24
    pngs = list(tmp_path.glob("*.png"))
    assert len(pngs) == total
