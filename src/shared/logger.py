import logging
import threading
from pathlib import Path


class AsyncLogger:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, log_path: str | None = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, log_path: str | None = None):
        if self._initialized:
            return
        self._initialized = True
        log_dir = Path(log_path or "data/chronosketch.log")
        log_dir.parent.mkdir(parents=True, exist_ok=True)
        self._logger = logging.getLogger("chronosketch")
        self._logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler(str(log_dir), mode="a", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        self._logger.addHandler(fh)

    def info(self, msg: str) -> None:
        self._logger.info(msg)

    def warn(self, msg: str) -> None:
        self._logger.warning(msg)

    def error(self, msg: str) -> None:
        self._logger.error(msg, exc_info=True)


logger = AsyncLogger()
