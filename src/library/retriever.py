import re
import json
import urllib.request
import urllib.parse
import urllib.error
import numpy as np
from numpy.linalg import norm
from sentence_transformers import SentenceTransformer
from src.shared.logger import logger
from src.shared.models import AssetMatch
from src.library.indexer import Indexer
from src.shared.config import ASSETS_DIR, SIMILARITY_THRESHOLD, ONLINE_SVG_FALLBACK


def _sanitise_name(keyword: str) -> str:
    return re.sub(r"[^a-z0-9]", "-", keyword.lower()).strip("-")


def _search_iconify(term: str) -> str | None:
    query = urllib.parse.quote(term)
    search_url = f"https://api.iconify.design/search?query={query}&limit=1"
    headers = {"User-Agent": "ChronoSketch/1.0"}
    try:
        req = urllib.request.Request(search_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode()
    except Exception:
        return None
    try:
        results = json.loads(data)
    except Exception:
        return None
    icons = results.get("icons") or []
    if not icons:
        return None
    parts = icons[0].split(":")
    if len(parts) != 2:
        return None
    prefix, name = parts
    svg_url = f"https://api.iconify.design/{prefix}/{name}.svg"
    try:
        req2 = urllib.request.Request(svg_url, headers=headers)
        with urllib.request.urlopen(req2, timeout=10) as resp:
            svg_bytes = resp.read()
    except Exception:
        return None
    assets_dir = ASSETS_DIR
    assets_dir.mkdir(parents=True, exist_ok=True)
    safe = _sanitise_name(term)
    local_name = f"online-{safe}.svg"
    local_path = assets_dir / local_name
    with open(local_path, "wb") as f:
        f.write(svg_bytes)
    logger.info(f"Downloaded SVG from Iconify: {prefix}/{name} → {local_path}")
    return str(local_path)


def _fetch_svg_iconify(keyword: str) -> str | None:
    result = _search_iconify(keyword)
    if result:
        return result
    for word in keyword.split():
        result = _search_iconify(word)
        if result:
            return result
    logger.warn(f"No Iconify results for any word in '{keyword}'")
    return None


class Retriever:
    def __init__(self, assets_dir: str = str(ASSETS_DIR)):
        self._indexer = Indexer(assets_dir)
        self._index = self._indexer.build_index()
        logger.info("Loading embedding model: all-MiniLM-L6-v2")
        self._model = SentenceTransformer("all-MiniLM-L6-v2")
        self._filename_embeddings: dict[str, np.ndarray] = {}
        if self._index:
            phrases = [" ".join(kws) for kws in self._index.values()]
            embeds = self._model.encode(phrases, normalize_embeddings=True)
            for fname, vec in zip(self._index.keys(), embeds):
                self._filename_embeddings[fname] = vec

    def query(self, keyword: str) -> str | None:
        query_vec = self._model.encode(keyword, normalize_embeddings=True)
        best_fname = None
        best_score = -1.0
        for fname, vec in self._filename_embeddings.items():
            score = float(query_vec @ vec)
            if score > best_score:
                best_score = score
                best_fname = fname
        local_path = str(ASSETS_DIR / f"{best_fname}.svg") if best_fname else None
        logger.info(f"Library query '{keyword}' → {best_fname} (score={best_score:.3f})")

        if local_path and best_score >= SIMILARITY_THRESHOLD:
            return local_path

        if best_score < SIMILARITY_THRESHOLD and ONLINE_SVG_FALLBACK:
            logger.info(f"Score {best_score:.3f} < {SIMILARITY_THRESHOLD}, trying online fallback for '{keyword}'")
            online = _fetch_svg_iconify(keyword)
            if online:
                return online

        return local_path

    def resolve_assets(self, keywords: list[tuple[int, str]]) -> list[AssetMatch]:
        results: list[AssetMatch] = []
        for event_id, keyword in keywords:
            path = self.query(keyword)
            results.append(AssetMatch(event_id=event_id, svg_path=path or "", keyword=keyword))
        return results
