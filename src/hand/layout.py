from src.shared.config import CANVAS_WIDTH, CANVAS_HEIGHT

_ICON_SIZE = 180

_LAYOUTS: dict[int, list[tuple[float, float]]] = {
    1: [(CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2)],
    2: [
        (CANVAS_WIDTH / 2 - 200, CANVAS_HEIGHT / 2),
        (CANVAS_WIDTH / 2 + 200, CANVAS_HEIGHT / 2),
    ],
    3: [
        (CANVAS_WIDTH / 2 - 300, CANVAS_HEIGHT / 2),
        (CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2),
        (CANVAS_WIDTH / 2 + 300, CANVAS_HEIGHT / 2),
    ],
    4: [
        (CANVAS_WIDTH / 2 - 200, CANVAS_HEIGHT / 2 - 140),
        (CANVAS_WIDTH / 2 + 200, CANVAS_HEIGHT / 2 - 140),
        (CANVAS_WIDTH / 2 - 200, CANVAS_HEIGHT / 2 + 140),
        (CANVAS_WIDTH / 2 + 200, CANVAS_HEIGHT / 2 + 140),
    ],
    5: [
        (CANVAS_WIDTH / 2 - 300, CANVAS_HEIGHT / 2 - 140),
        (CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2 - 140),
        (CANVAS_WIDTH / 2 + 300, CANVAS_HEIGHT / 2 - 140),
        (CANVAS_WIDTH / 2 - 150, CANVAS_HEIGHT / 2 + 140),
        (CANVAS_WIDTH / 2 + 150, CANVAS_HEIGHT / 2 + 140),
    ],
    6: [
        (CANVAS_WIDTH / 2 - 300, CANVAS_HEIGHT / 2 - 140),
        (CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2 - 140),
        (CANVAS_WIDTH / 2 + 300, CANVAS_HEIGHT / 2 - 140),
        (CANVAS_WIDTH / 2 - 300, CANVAS_HEIGHT / 2 + 140),
        (CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2 + 140),
        (CANVAS_WIDTH / 2 + 300, CANVAS_HEIGHT / 2 + 140),
    ],
}

MAX_ELEMENTS_PER_SCENE = 6


def get_positions(count: int) -> list[tuple[float, float]]:
    if count < 1 or count > MAX_ELEMENTS_PER_SCENE:
        raise ValueError(f"Element count must be 1..{MAX_ELEMENTS_PER_SCENE}, got {count}")
    return _LAYOUTS[count]


def icon_size() -> int:
    return _ICON_SIZE
