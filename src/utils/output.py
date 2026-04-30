import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("devin_indexer.output")


@dataclass
class IndexingResult:
    branch: str
    status: str  # "success" | "already_indexed" | "error"
    indexed_at: str = ""
    message: str = ""
    error: str = ""


@dataclass
class RepositoryResult:
    name: str
    owner: str
    url: str
    branches_found: list = field(default_factory=list)
    branches_processed: list = field(default_factory=list)
    results: list = field(default_factory=list)


@dataclass
class ErrorEntry:
    repository: str
    branch: str
    error_type: str
    error_message: str
    attempts: int
    last_attempt: str


@dataclass
class SkippedEntry:
    repository: str
    branch: str
    reason: str
    checked_at: str


class OutputWriter:
    def __init__(self, indexing_url: str, search_term: str):
        self._start_time = datetime.now(timezone.utc)
        self._indexing_url = indexing_url
        self._search_term = search_term
        self._repositories: list[RepositoryResult] = []
        self._errors: list[ErrorEntry] = []
        self._skipped: list[SkippedEntry] = []
        self._successful = 0
        self._failed = 0
        self._already_indexed = 0

    def add_repository(self, repo: RepositoryResult) -> None:
        self._repositories.append(repo)
        for result in repo.results:
            if result["status"] == "success":
                self._successful += 1
            elif result["status"] == "error":
                self._failed += 1
            elif result["status"] == "already_indexed":
                self._already_indexed += 1

    def add_error(self, entry: ErrorEntry) -> None:
        self._errors.append(entry)

    def add_skipped(self, entry: SkippedEntry) -> None:
        self._skipped.append(entry)

    def build(self, execution_time: float) -> dict[str, Any]:
        total_branches = self._successful + self._failed + self._already_indexed
        return {
            "metadata": {
                "execution_timestamp": self._start_time.isoformat(),
                "indexing_url": self._indexing_url,
                "search_term": self._search_term,
                "total_repositories_found": len(self._repositories),
                "total_repositories_processed": len(self._repositories),
                "total_branches_indexed": total_branches,
                "successful_indexations": self._successful,
                "failed_indexations": self._failed,
                "already_indexed": self._already_indexed,
                "execution_time_seconds": round(execution_time, 2),
            },
            "repositories": [self._repo_to_dict(r) for r in self._repositories],
            "errors": [asdict(e) for e in self._errors],
            "skipped": [asdict(s) for s in self._skipped],
        }

    def save(self, filepath: str, execution_time: float) -> None:
        data = self.build(execution_time)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Results saved to {filepath}")

    @staticmethod
    def _repo_to_dict(repo: RepositoryResult) -> dict:
        return {
            "name": repo.name,
            "owner": repo.owner,
            "url": repo.url,
            "branches_found": repo.branches_found,
            "branches_processed": repo.branches_processed,
            "results": repo.results,
        }
