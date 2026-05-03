"""Rate limit detection and exponential backoff retry mechanism."""

import random
import time


# Retryable HTTP status codes (server errors + rate limit)
RETRYABLE_STATUS_CODES = {429, 500, 502, 503}

# Non-retryable status codes (client errors)
NON_RETRYABLE_STATUS_CODES = {400, 401, 403, 404}

# Default configuration
DEFAULT_BASE_DELAY = 1.0
DEFAULT_JITTER = 0.5
DEFAULT_MAX_RETRIES = 3


class RateLimitError(Exception):
    """Raised when max retries are exhausted."""
    pass


class NonRetryableError(Exception):
    """Raised for non-retryable HTTP errors."""
    def __init__(self, status_code, message="Non-retryable error"):
        self.status_code = status_code
        super().__init__(f"{message}: {status_code}")


class RateLimiter:
    """Rate limit detection and exponential backoff retry."""

    def __init__(self, base_delay=DEFAULT_BASE_DELAY, jitter=DEFAULT_JITTER):
        """
        Args:
            base_delay: Base delay in seconds for exponential backoff.
            jitter: Maximum random jitter in seconds added to backoff.
        """
        self.base_delay = base_delay
        self.jitter = jitter

    def should_retry(self, status_code, headers=None):
        """Determine if a request should be retried based on status code.

        Args:
            status_code: HTTP response status code.
            headers: Optional response headers dict. If present and contains
                     'Retry-After', it confirms retryability.

        Returns:
            True if the request should be retried, False otherwise.
        """
        if status_code in NON_RETRYABLE_STATUS_CODES:
            return False
        if status_code in RETRYABLE_STATUS_CODES:
            return True
        # Unknown status codes: don't retry by default
        return False

    def get_wait_time(self, attempt):
        """Calculate exponential backoff wait time with jitter.

        Formula: base_delay * 2^attempt + random(0, jitter)

        Args:
            attempt: Zero-based attempt number (0 for first retry).

        Returns:
            Wait time in seconds as a float.
        """
        delay = self.base_delay * (2 ** attempt)
        jitter_value = random.uniform(0, self.jitter)
        return delay + jitter_value

    def execute_with_retry(self, func, max_retries=DEFAULT_MAX_RETRIES):
        """Execute a function with automatic retry on retryable errors.

        Args:
            func: Callable that returns (status_code, headers, result) or
                  raises an exception.
            max_retries: Maximum number of retry attempts.

        Returns:
            The result from a successful function call.

        Raises:
            NonRetryableError: If a non-retryable status code is encountered.
            RateLimitError: If max retries are exhausted.
        """
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                status_code, headers, result = func()
                # Successful response
                return result
            except NonRetryableError:
                raise
            except (RateLimitError, Exception) as exc:
                last_exception = exc
                # Check if we should retry
                if attempt < max_retries:
                    wait_time = self.get_wait_time(attempt)
                    time.sleep(wait_time)
                else:
                    break

        raise RateLimitError(
            f"Max retries ({max_retries}) exhausted"
        ) from last_exception
