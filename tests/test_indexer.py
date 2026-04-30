import pytest
from src.indexer.retry_handler import AdaptiveRateLimiter


def test_rate_limiter_increase():
    rl = AdaptiveRateLimiter(initial_delay=1.0)
    rl.increase()
    assert rl._delay == pytest.approx(1.5)


def test_rate_limiter_decrease():
    rl = AdaptiveRateLimiter(initial_delay=1.0)
    rl.decrease()
    assert rl._delay == pytest.approx(0.9)


def test_rate_limiter_max_cap():
    rl = AdaptiveRateLimiter(initial_delay=8.0)
    rl.increase()
    assert rl._delay <= 10.0


def test_rate_limiter_min_floor():
    rl = AdaptiveRateLimiter(initial_delay=0.5)
    rl.decrease()
    assert rl._delay >= 0.5
