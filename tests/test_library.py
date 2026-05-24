from pathlib import Path
from src.library.indexer import Indexer
from src.shared.config import ASSETS_DIR


def test_indexer_builds_index():
    idx = Indexer(ASSETS_DIR)
    index = idx.build_index()
    assert len(index) > 0
    assert "circle" in index or any("circle" in v for v in index.values())


def test_indexer_filenames():
    idx = Indexer(ASSETS_DIR)
    idx.build_index()
    names = idx.filenames
    assert len(names) > 0
    assert all(name.endswith("") for name in names)


def test_keywords_for():
    idx = Indexer(ASSETS_DIR)
    idx.build_index()
    if idx.filenames:
        kw = idx.keywords_for(idx.filenames[0])
        assert isinstance(kw, list)
        assert len(kw) >= 1


def test_retriever_query():
    from src.library.retriever import Retriever
    r = Retriever(str(ASSETS_DIR))
    path = r.query("circle")
    assert path is not None
    assert Path(path).exists()
    assert path.endswith(".svg")
