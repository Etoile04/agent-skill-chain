"""Tests for rate limit detection and exponential backoff retry."""

import random
import unittest
from unittest.mock import patch, MagicMock

from ratelimit import (
    RateLimiter,
    RateLimitError,
    NonRetryableError,
    RETRYABLE_STATUS_CODES,
    NON_RETRYABLE_STATUS_CODES,
)


class TestShouldRetry(unittest.TestCase):
    """Test RateLimiter.should_retry() classification logic."""

    def setUp(self):
        self.limiter = RateLimiter()

    def test_retryable_429(self):
        self.assertTrue(self.limiter.should_retry(429))

    def test_retryable_500(self):
        self.assertTrue(self.limiter.should_retry(500))

    def test_retryable_502(self):
        self.assertTrue(self.limiter.should_retry(502))

    def test_retryable_503(self):
        self.assertTrue(self.limiter.should_retry(503))

    def test_non_retryable_400(self):
        self.assertFalse(self.limiter.should_retry(400))

    def test_non_retryable_401(self):
        self.assertFalse(self.limiter.should_retry(401))

    def test_non_retryable_403(self):
        self.assertFalse(self.limiter.should_retry(403))

    def test_non_retryable_404(self):
        self.assertFalse(self.limiter.should_retry(404))

    def test_unknown_status_code_not_retryable(self):
        self.assertFalse(self.limiter.should_retry(418))
        self.assertFalse(self.limiter.should_retry(200))

    def test_all_retryable_codes(self):
        """Verify all declared retryable codes are correctly handled."""
        for code in RETRYABLE_STATUS_CODES:
            with self.subTest(code=code):
                self.assertTrue(self.limiter.should_retry(code))

    def test_all_non_retryable_codes(self):
        """Verify all declared non-retryable codes are correctly handled."""
        for code in NON_RETRYABLE_STATUS_CODES:
            with self.subTest(code=code):
                self.assertFalse(self.limiter.should_retry(code))

    def test_with_retry_after_header(self):
        """Headers parameter is accepted without error."""
        headers = {"Retry-After": "30"}
        self.assertTrue(self.limiter.should_retry(429, headers))


class TestGetWaitTime(unittest.TestCase):
    """Test RateLimiter.get_wait_time() exponential backoff calculation."""

    def setUp(self):
        self.limiter = RateLimiter(base_delay=1.0, jitter=0.5)

    @patch("ratelimit.random.uniform", return_value=0.0)
    def test_attempt_0_base_delay(self, mock_uniform):
        """First retry: base_delay * 2^0 + 0 = 1.0"""
        wait = self.limiter.get_wait_time(0)
        self.assertAlmostEqual(wait, 1.0)

    @patch("ratelimit.random.uniform", return_value=0.0)
    def test_attempt_1_doubles(self, mock_uniform):
        """Second retry: base_delay * 2^1 + 0 = 2.0"""
        wait = self.limiter.get_wait_time(1)
        self.assertAlmostEqual(wait, 2.0)

    @patch("ratelimit.random.uniform", return_value=0.0)
    def test_attempt_2_quadruples(self, mock_uniform):
        """Third retry: base_delay * 2^2 + 0 = 4.0"""
        wait = self.limiter.get_wait_time(2)
        self.assertAlmostEqual(wait, 4.0)

    @patch("ratelimit.random.uniform", return_value=0.3)
    def test_jitter_added(self, mock_uniform):
        """Jitter is added to the base exponential delay."""
        wait = self.limiter.get_wait_time(0)
        self.assertAlmostEqual(wait, 1.3)

    @patch("ratelimit.random.uniform", return_value=0.5)
    def test_max_jitter(self, mock_uniform):
        """Maximum jitter equals configured value."""
        wait = self.limiter.get_wait_time(1)
        self.assertAlmostEqual(wait, 2.5)

    def test_monotonically_increasing(self):
        """Wait times should generally increase with attempt number."""
        # Fix random seed for deterministic test
        random.seed(42)
        waits = [self.limiter.get_wait_time(i) for i in range(5)]
        for i in range(len(waits) - 1):
            self.assertGreater(waits[i + 1], waits[i],
                               f"Wait time decreased from attempt {i} to {i+1}")

    def test_custom_base_delay(self):
        """Custom base_delay is respected."""
        limiter = RateLimiter(base_delay=2.0, jitter=0.0)
        with patch("ratelimit.random.uniform", return_value=0.0):
            wait = limiter.get_wait_time(2)
        self.assertAlmostEqual(wait, 8.0)  # 2.0 * 2^2


class TestExecuteWithRetry(unittest.TestCase):
    """Test RateLimiter.execute_with_retry() retry wrapper."""

    def setUp(self):
        self.limiter = RateLimiter(base_delay=0.01, jitter=0.0)

    @patch("ratelimit.time.sleep")
    def test_success_on_first_try(self, mock_sleep):
        """Function succeeds immediately, no retries."""
        func = MagicMock(return_value=(200, {}, "ok"))
        result = self.limiter.execute_with_retry(func)
        self.assertEqual(result, "ok")
        func.assert_called_once()
        mock_sleep.assert_not_called()

    @patch("ratelimit.time.sleep")
    def test_success_after_retry(self, mock_sleep):
        """Function fails once then succeeds."""
        func = MagicMock(
            side_effect=[
                Exception("transient error"),
                (200, {}, "recovered"),
            ]
        )
        result = self.limiter.execute_with_retry(func, max_retries=3)
        self.assertEqual(result, "recovered")
        self.assertEqual(func.call_count, 2)
        mock_sleep.assert_called_once()

    @patch("ratelimit.time.sleep")
    def test_max_retries_exhausted(self, mock_sleep):
        """Raises RateLimitError after exhausting all retries."""
        func = MagicMock(side_effect=Exception("always fails"))
        with self.assertRaises(RateLimitError):
            self.limiter.execute_with_retry(func, max_retries=3)
        # 3 retries = 4 total calls (initial + 3 retries)
        self.assertEqual(func.call_count, 4)
        self.assertEqual(mock_sleep.call_count, 3)

    @patch("ratelimit.time.sleep")
    def test_non_retryable_error_no_retry(self, mock_sleep):
        """NonRetryableError is raised immediately without retry."""
        func = MagicMock(side_effect=NonRetryableError(403))
        with self.assertRaises(NonRetryableError) as ctx:
            self.limiter.execute_with_retry(func, max_retries=3)
        self.assertEqual(ctx.exception.status_code, 403)
        func.assert_called_once()
        mock_sleep.assert_not_called()

    @patch("ratelimit.time.sleep")
    def test_zero_retries(self, mock_sleep):
        """With max_retries=0, no retries are attempted."""
        func = MagicMock(side_effect=Exception("fail"))
        with self.assertRaises(RateLimitError):
            self.limiter.execute_with_retry(func, max_retries=0)
        func.assert_called_once()
        mock_sleep.assert_not_called()

    @patch("ratelimit.time.sleep")
    def test_retry_uses_exponential_backoff(self, mock_sleep):
        """Sleep durations increase exponentially across retries."""
        call_count = 0

        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                raise Exception(f"fail {call_count}")
            return (200, {}, "done")

        with patch("ratelimit.random.uniform", return_value=0.0):
            result = self.limiter.execute_with_retry(failing_func, max_retries=3)

        self.assertEqual(result, "done")
        # Check sleep was called with increasing delays
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        self.assertEqual(len(sleep_calls), 3)
        # base_delay=0.01: 0.01, 0.02, 0.04
        self.assertAlmostEqual(sleep_calls[0], 0.01)
        self.assertAlmostEqual(sleep_calls[1], 0.02)
        self.assertAlmostEqual(sleep_calls[2], 0.04)


class TestStatusCodeClassification(unittest.TestCase):
    """Edge cases for status code classification."""

    def setUp(self):
        self.limiter = RateLimiter()

    def test_distinct_retryable_and_non_retryable(self):
        """Retryable and non-retryable sets must not overlap."""
        self.assertEqual(
            RETRYABLE_STATUS_CODES & NON_RETRYABLE_STATUS_CODES,
            set()
        )

    def test_200_is_not_retryable(self):
        """Success codes should not be retryable."""
        self.assertFalse(self.limiter.should_retry(200))

    def test_201_is_not_retryable(self):
        self.assertFalse(self.limiter.should_retry(201))


if __name__ == "__main__":
    unittest.main()
