import math
import xml.etree.ElementTree as ET
from svg.path import parse_path
from src.shared.logger import logger

_NS = "http://www.w3.org/2000/svg"
_STROKEABLE_TAGS = ["path", "rect", "circle", "ellipse", "line", "polyline", "polygon"]


def _parse_points(attr: str) -> list[tuple[float, float]]:
    parts = attr.strip().replace(",", " ").split()
    pts = []
    for i in range(0, len(parts), 2):
        try:
            pts.append((float(parts[i]), float(parts[i + 1])))
        except (IndexError, ValueError):
            break
    return pts


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.sqrt((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2)


def _element_length(el: ET.Element, tag: str) -> float:
    try:
        if tag == "path":
            d = el.get("d", "")
            return parse_path(d).length() if d else 0.0
        if tag == "rect":
            w = float(el.get("width", 0))
            h = float(el.get("height", 0))
            return 2.0 * (w + h)
        if tag == "circle":
            r = float(el.get("r", 0))
            return 2.0 * math.pi * r
        if tag == "ellipse":
            rx = float(el.get("rx", 0))
            ry = float(el.get("ry", 0))
            s = rx + ry
            return math.pi * (3.0 * s - math.sqrt((3.0 * rx + ry) * (rx + 3.0 * ry)))
        if tag == "line":
            x1 = float(el.get("x1", 0))
            y1 = float(el.get("y1", 0))
            x2 = float(el.get("x2", 0))
            y2 = float(el.get("y2", 0))
            return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        if tag in ("polyline", "polygon"):
            pts = _parse_points(el.get("points", ""))
            if len(pts) < 2:
                return 0.0
            total = sum(_dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
            if tag == "polygon" and len(pts) > 2:
                total += _dist(pts[-1], pts[0])
            return total
    except Exception:
        pass
    return 0.0


def total_length(svg_path: str) -> float:
    tree = ET.parse(svg_path)
    root = tree.getroot()
    total = 0.0
    for tag in _STROKEABLE_TAGS:
        for el in root.findall(f".//{{{_NS}}}{tag}") or root.findall(f".//{tag}"):
            total += _element_length(el, tag)
    return total


def _stroke_width(root: ET.Element) -> str:
    vb = root.get("viewBox", "0 0 24 24")
    try:
        parts = vb.strip().split()
        w = float(parts[2])
    except (IndexError, ValueError):
        w = 24.0
    return str(max(1, round(w / 24)))


def _add_stroke_if_missing(el: ET.Element, sw: str) -> None:
    if el.get("stroke") is None or el.get("stroke") == "none":
        el.set("stroke", "currentColor")
        el.set("stroke-width", sw)
        if el.get("fill") is None or el.get("fill") != "none":
            el.set("fill", "none")


def animate_svg(svg_path: str, progress: float) -> str:
    progress = max(0.0, min(1.0, progress))
    tree = ET.parse(svg_path)
    root = tree.getroot()
    sw = _stroke_width(root)
    for tag in _STROKEABLE_TAGS:
        for el in root.findall(f".//{{{_NS}}}{tag}") or root.findall(f".//{tag}"):
            _add_stroke_if_missing(el, sw)
            plen = _element_length(el, tag)
            offset = plen * (1.0 - progress)
            el.set("stroke-dasharray", str(plen))
            el.set("stroke-dashoffset", str(offset))
    return ET.tostring(root, encoding="unicode")
