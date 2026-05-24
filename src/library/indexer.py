from pathlib import Path
from src.shared.logger import logger
from src.shared.config import ASSETS_DIR


class Indexer:
    def __init__(self, assets_dir: str | Path = ASSETS_DIR):
        self._assets_dir = Path(assets_dir)
        self._index: dict[str, list[str]] = {}

    def build_index(self) -> dict[str, list[str]]:
        if not self._assets_dir.exists():
            logger.error(f"Assets directory not found: {self._assets_dir}")
            return {}
        self._index = {}
        for svg_path in sorted(self._assets_dir.glob("*.svg")):
            stem = svg_path.stem
            keywords = stem.replace("-", " ").replace("_", " ").split()
            self._index[stem] = keywords
        logger.info(f"Indexed {len(self._index)} SVGs from {self._assets_dir}")
        return self._index

    @property
    def filenames(self) -> list[str]:
        return list(self._index.keys())

    def keywords_for(self, filename: str) -> list[str]:
        return self._index.get(filename, [])
