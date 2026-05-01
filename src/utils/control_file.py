import json
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger("devin_indexer.control")

_DONE_STATUSES = {"done", "skipped"}


class ControlFile:
    def __init__(self, path: str):
        self._path = path
        self._data: dict = {}

    def exists(self) -> bool:
        return os.path.exists(self._path)

    def matches(self, indexing_url: str, search_term: str) -> bool:
        return (
            self._data.get("indexing_url") == indexing_url
            and self._data.get("search_term") == search_term
        )

    def load(self) -> bool:
        try:
            with open(self._path, encoding="utf-8") as f:
                self._data = json.load(f)
            pending = self.pending_count()
            total = len(self._data.get("repositories", []))
            logger.info(f"Control file loaded: {self._path} ({pending}/{total} repos pending)")
            return True
        except Exception as e:
            logger.warning(f"Failed to load control file: {e}")
            return False

    def initialize(self, indexing_url: str, search_term: str, repositories: list[dict]) -> None:
        self._data = {
            "run_id": datetime.now(timezone.utc).isoformat(),
            "indexing_url": indexing_url,
            "search_term": search_term,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "repositories": [
                {
                    "name": r["name"],
                    "owner": r["owner"],
                    "url": r["url"],
                    "has_indexed_branches": r.get("has_indexed_branches", False),
                    "status": "pending",
                    "branches_found": [],
                    "branches_processed": [],
                    "results": [],
                    "last_updated": None,
                    "error": None,
                }
                for r in repositories
            ],
        }
        self._flush()
        logger.info(f"Control file created: {self._path} ({len(repositories)} repos)")

    def get_repositories(self) -> list[dict]:
        return self._data.get("repositories", [])

    def mark_processing(self, index: int) -> None:
        repo = self._data["repositories"][index]
        repo["status"] = "processing"
        repo["last_updated"] = _now()
        self._flush()

    def mark_done(self, index: int, result: dict) -> None:
        repo = self._data["repositories"][index]
        repo["status"] = "done"
        repo["branches_found"] = result.get("branches_found", [])
        repo["branches_processed"] = result.get("branches_processed", [])
        repo["results"] = result.get("results", [])
        repo["last_updated"] = _now()
        repo["error"] = None
        self._flush()

    def mark_skipped(self, index: int, reason: str = "") -> None:
        repo = self._data["repositories"][index]
        repo["status"] = "skipped"
        repo["last_updated"] = _now()
        repo["error"] = reason or None
        self._flush()

    def mark_error(self, index: int, error: str) -> None:
        repo = self._data["repositories"][index]
        repo["status"] = "error"
        repo["error"] = error
        repo["last_updated"] = _now()
        self._flush()

    def pending_count(self) -> int:
        return sum(1 for r in self._data.get("repositories", []) if r["status"] not in _DONE_STATUSES)

    def _flush(self) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
