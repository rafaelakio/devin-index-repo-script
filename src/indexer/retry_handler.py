import logging
import time

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)
from selenium.common.exceptions import TimeoutException, WebDriverException

logger = logging.getLogger("devin_indexer.retry")


class AdaptiveRateLimiter:
    def __init__(self, initial_delay: float = 1.0):
        self._delay = initial_delay
        self._last_request = 0.0

    def wait(self) -> None:
        elapsed = time.time() - self._last_request
        if elapsed < self._delay:
            time.sleep(self._delay - elapsed)
        self._last_request = time.time()

    def increase(self) -> None:
        self._delay = min(self._delay * 1.5, 10.0)
        logger.warning(f"Rate limit backoff increased to {self._delay:.1f}s")

    def decrease(self) -> None:
        self._delay = max(self._delay * 0.9, 0.5)


def make_retry_decorator(max_attempts: int = 3, min_wait: float = 2.0, max_wait: float = 10.0):
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type((TimeoutException, WebDriverException)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
