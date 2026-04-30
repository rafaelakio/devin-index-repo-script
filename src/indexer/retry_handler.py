"""
Retry logic and rate limiting for API operations.
"""
import time
from typing import Callable, Any, Optional
from functools import wraps
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
import logging

from src.utils.logger import get_logger

logger = get_logger()


class RetryHandler:
    """Handles retry logic with exponential backoff and rate limiting."""
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 10.0,
        rate_limit_delay: float = 1.0
    ):
        """
        Initialize retry handler.
        
        Args:
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            rate_limit_delay: Delay between successful operations
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.rate_limit_delay = rate_limit_delay
        self.last_request_time = 0
    
    def with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute a function with retry logic.
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result of the function
            
        Raises:
            Exception if all retries fail
        """
        attempt = 0
        last_exception = None
        
        while attempt < self.max_retries:
            try:
                # Apply rate limiting
                self.apply_rate_limit()
                
                # Execute function
                result = func(*args, **kwargs)
                
                # Log success if this was a retry
                if attempt > 0:
                    logger.info(f"Operation succeeded on attempt {attempt + 1}")
                
                return result
                
            except Exception as e:
                attempt += 1
                last_exception = e
                
                if attempt < self.max_retries:
                    delay = self._calculate_delay(attempt)
                    logger.warning(
                        f"Attempt {attempt} failed: {str(e)}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"All {self.max_retries} attempts failed. "
                        f"Last error: {str(e)}"
                    )
        
        raise last_exception
    
    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay.
        
        Args:
            attempt: Current attempt number (1-based)
            
        Returns:
            Delay in seconds
        """
        delay = self.initial_delay * (2 ** (attempt - 1))
        return min(delay, self.max_delay)
    
    def apply_rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        if self.rate_limit_delay > 0:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.rate_limit_delay:
                sleep_time = self.rate_limit_delay - elapsed
                logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
                time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def reset_rate_limit(self) -> None:
        """Reset the rate limit timer."""
        self.last_request_time = 0


def retry_on_exception(
    max_attempts: int = 3,
    initial_wait: float = 1.0,
    max_wait: float = 10.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts
        initial_wait: Initial wait time in seconds
        max_wait: Maximum wait time in seconds
        exceptions: Tuple of exception types to retry on
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            handler = RetryHandler(
                max_retries=max_attempts,
                initial_delay=initial_wait,
                max_delay=max_wait
            )
            return handler.with_retry(func, *args, **kwargs)
        return wrapper
    return decorator


def with_tenacity_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0
):
    """
    Decorator using tenacity library for advanced retry logic.
    
    Args:
        max_attempts: Maximum number of attempts
        min_wait: Minimum wait time in seconds
        max_wait: Maximum wait time in seconds
        
    Returns:
        Decorated function
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )


class RateLimiter:
    """Simple rate limiter for controlling request frequency."""
    
    def __init__(self, calls_per_second: float = 1.0):
        """
        Initialize rate limiter.
        
        Args:
            calls_per_second: Maximum number of calls per second
        """
        self.min_interval = 1.0 / calls_per_second if calls_per_second > 0 else 0
        self.last_call = 0
    
    def wait(self) -> None:
        """Wait if necessary to respect rate limit."""
        if self.min_interval > 0:
            elapsed = time.time() - self.last_call
            if elapsed < self.min_interval:
                sleep_time = self.min_interval - elapsed
                time.sleep(sleep_time)
        
        self.last_call = time.time()
    
    def __enter__(self):
        """Context manager entry."""
        self.wait()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass


class AdaptiveRateLimiter(RateLimiter):
    """Rate limiter that adapts based on success/failure."""
    
    def __init__(self, initial_calls_per_second: float = 1.0):
        """
        Initialize adaptive rate limiter.
        
        Args:
            initial_calls_per_second: Initial rate limit
        """
        super().__init__(initial_calls_per_second)
        self.calls_per_second = initial_calls_per_second
        self.success_count = 0
        self.failure_count = 0
    
    def record_success(self) -> None:
        """Record a successful operation."""
        self.success_count += 1
        self.failure_count = 0
        
        # Gradually increase rate after consecutive successes
        if self.success_count >= 10:
            self.calls_per_second = min(self.calls_per_second * 1.1, 10.0)
            self.min_interval = 1.0 / self.calls_per_second
            self.success_count = 0
            logger.debug(f"Increased rate to {self.calls_per_second:.2f} calls/sec")
    
    def record_failure(self) -> None:
        """Record a failed operation."""
        self.failure_count += 1
        self.success_count = 0
        
        # Decrease rate after failures
        if self.failure_count >= 2:
            self.calls_per_second = max(self.calls_per_second * 0.5, 0.1)
            self.min_interval = 1.0 / self.calls_per_second
            self.failure_count = 0
            logger.warning(f"Decreased rate to {self.calls_per_second:.2f} calls/sec")

# Made with Bob
