from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from src.services.rate_limiter import SimpleRateLimiter


@pytest.mark.unit
class TestSimpleRateLimiter:
    def test_init_default_values(self):
        """Test initialization with default values"""
        limiter = SimpleRateLimiter()

        assert limiter.max_attempts == 5
        assert limiter.window_minutes == 5
        assert limiter.block_minutes == 10
        assert limiter.attempts == {}
        assert limiter.blocks == {}

    def test_init_custom_values(self):
        """Test initialization with custom values"""
        limiter = SimpleRateLimiter(
            max_attempts=3,
            window_minutes=2,
            block_minutes=5
        )

        assert limiter.max_attempts == 3
        assert limiter.window_minutes == 2
        assert limiter.block_minutes == 5

    def test_cleanup_old_attempts(self):
        """Test cleanup of old attempts"""
        limiter = SimpleRateLimiter(window_minutes=5)
        key = "test_key"

        # Add attempts - some outside window, some inside
        now = datetime.now(UTC)
        limiter.attempts[key] = [
            now - timedelta(minutes=6),  # Outside window (should be removed)
            now - timedelta(minutes=3),  # Inside window (should be kept)
            now - timedelta(minutes=1),  # Inside window (should be kept)
            now - timedelta(minutes=10)  # Outside window (should be removed)
        ]

        # Cleanup
        limiter._cleanup_old_attempts(key)

        # Should only keep attempts within 5-minute window
        assert len(limiter.attempts[key]) == 2
        # Verify the remaining attempts are the recent ones
        for attempt in limiter.attempts[key]:
            assert attempt > now - timedelta(minutes=5)

    def test_is_blocked_no_attempts(self):
        """Test is_blocked with no previous attempts"""
        limiter = SimpleRateLimiter()

        is_blocked, remaining_time = limiter.is_blocked("test_key")

        assert is_blocked is False
        assert remaining_time is None

    def test_is_blocked_under_limit(self):
        """Test is_blocked with attempts under limit"""
        limiter = SimpleRateLimiter(max_attempts=3, window_minutes=5)
        key = "test_key"

        # Add attempts under limit
        for i in range(2):
            limiter.attempts[key].append(datetime.now(UTC))

        is_blocked, remaining_time = limiter.is_blocked(key)

        assert is_blocked is False
        assert remaining_time is None

    def test_is_blocked_over_limit(self):
        """Test is_blocked with attempts over limit"""
        limiter = SimpleRateLimiter(max_attempts=2, window_minutes=5, block_minutes=10)
        key = "test_key"

        # Add attempts over limit
        for i in range(3):
            limiter.record_attempt(key)

        # Check if blocked using check_attempt method
        allowed, remaining_time = limiter.check_attempt(key)

        # Should be blocked due to rate limit
        assert allowed is False
        assert remaining_time is not None
        assert remaining_time > 0

    def test_is_blocked_with_existing_block(self):
        """Test is_blocked with existing block"""
        limiter = SimpleRateLimiter(block_minutes=10)
        key = "test_key"

        # Set existing block (not expired)
        block_time = datetime.now(UTC) + timedelta(minutes=5)
        limiter.blocks[key] = block_time

        is_blocked, remaining_time = limiter.is_blocked(key)

        # Should be blocked due to existing block
        assert is_blocked is True
        assert remaining_time is not None
        assert remaining_time > 0
        assert remaining_time <= 5 * 60  # Should be less than 5 minutes in seconds

    def test_is_blocked_expired_block(self):
        """Test is_blocked with expired block"""
        limiter = SimpleRateLimiter(block_minutes=5)
        key = "test_key"

        # Set expired block
        block_time = datetime.now(UTC) - timedelta(minutes=10)
        limiter.blocks[key] = block_time

        is_blocked, remaining_time = limiter.is_blocked(key)

        assert is_blocked is False
        assert remaining_time is None
        # Block should be removed
        assert key not in limiter.blocks

    def test_record_attempt_new_key(self):
        """Test record_attempt with new key"""
        limiter = SimpleRateLimiter()
        key = "new_key"

        limiter.record_attempt(key)

        assert key in limiter.attempts
        assert len(limiter.attempts[key]) == 1
        assert limiter.attempts[key][0] <= datetime.now(UTC)

    def test_record_attempt_existing_key(self):
        """Test record_attempt with existing key"""
        limiter = SimpleRateLimiter()
        key = "existing_key"

        # Add existing attempt
        limiter.attempts[key] = [datetime.now(UTC) - timedelta(minutes=1)]

        limiter.record_attempt(key)

        assert len(limiter.attempts[key]) == 2
        assert limiter.attempts[key][1] >= limiter.attempts[key][0]

    def test_check_attempt_no_attempts(self):
        """Test check_attempt with no attempts"""
        limiter = SimpleRateLimiter()

        allowed, remaining = limiter.check_attempt("test_key")

        assert allowed is True
        assert remaining is None

    def test_check_attempt_under_limit(self):
        """Test check_attempt with attempts under limit"""
        limiter = SimpleRateLimiter(max_attempts=3, window_minutes=5)
        key = "test_key"

        # Add attempts under limit
        for i in range(2):
            limiter.record_attempt(key)

        allowed, remaining = limiter.check_attempt(key)

        assert allowed is True
        assert remaining is None

    def test_check_attempt_over_limit(self):
        """Test check_attempt with attempts over limit"""
        limiter = SimpleRateLimiter(max_attempts=2, window_minutes=5, block_minutes=10)
        key = "test_key"

        # Add attempts over limit
        for i in range(3):
            limiter.record_attempt(key)

        allowed, remaining = limiter.check_attempt(key)

        assert allowed is False
        assert remaining is not None
        assert remaining > 0

    def test_multiple_keys_independent(self):
        """Test that different keys are handled independently"""
        limiter = SimpleRateLimiter(max_attempts=2)

        # Add attempts to different keys
        limiter.record_attempt("key1")
        limiter.record_attempt("key1")
        limiter.record_attempt("key2")

        # Check attempts using check_attempt method
        allowed1, _ = limiter.check_attempt("key1")
        allowed2, _ = limiter.check_attempt("key2")

        # key1 should be blocked, key2 should not
        assert allowed1 is False
        assert allowed2 is True

    @patch('src.services.rate_limiter.datetime')
    def test_with_mocked_datetime(self, mock_datetime):
        """Test with mocked datetime for consistent testing"""
        # Setup mock
        fixed_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = fixed_time
        mock_datetime.timezone.utc = UTC

        limiter = SimpleRateLimiter(max_attempts=2, window_minutes=5)
        key = "test_key"

        # Add attempts at fixed times
        attempt_time1 = fixed_time - timedelta(minutes=1)
        attempt_time2 = fixed_time - timedelta(minutes=2)
        limiter.attempts[key] = [attempt_time1, attempt_time2]

        # Test cleanup with mocked time
        limiter._cleanup_old_attempts(key)

        # Both attempts should be kept (within 5-minute window)
        assert len(limiter.attempts[key]) == 2

    def test_cleanup_removes_expired_blocks(self):
        """Test that expired blocks are removed during is_blocked check"""
        limiter = SimpleRateLimiter(block_minutes=5)
        key = "test_key"

        # Set expired block and also have attempts
        block_time = datetime.now(UTC) - timedelta(minutes=10)
        limiter.blocks[key] = block_time
        limiter.attempts[key] = [datetime.now(UTC)]

        # Check is_blocked - should remove expired block and also attempts
        is_blocked, remaining = limiter.is_blocked(key)

        assert is_blocked is False
        assert remaining is None
        assert key not in limiter.blocks
        assert key not in limiter.attempts

    def test_check_attempt_blocked(self):
        """Test check_attempt returns False and remaining time if blocked"""
        limiter = SimpleRateLimiter(block_minutes=10)
        key = "test_key"

        block_time = datetime.now(UTC) + timedelta(minutes=5)
        limiter.blocks[key] = block_time

        allowed, remaining = limiter.check_attempt(key)
        assert allowed is False
        assert remaining is not None
        assert remaining > 0

    def test_record_success_cleans_attempts_and_blocks(self):
        """Test record_success deletes key from attempts and blocks if present"""
        limiter = SimpleRateLimiter()
        key = "test_key"

        limiter.attempts[key] = [datetime.now(UTC)]
        limiter.blocks[key] = datetime.now(UTC) + timedelta(minutes=10)

        limiter.record_success(key)

        assert key not in limiter.attempts
        assert key not in limiter.blocks

    def test_get_remaining_attempts_blocked(self):
        """Test get_remaining_attempts returns 0 if blocked"""
        limiter = SimpleRateLimiter()
        key = "test_key"
        limiter.blocks[key] = datetime.now(UTC) + timedelta(minutes=10)

        assert limiter.get_remaining_attempts(key) == 0

    def test_get_remaining_attempts_under_limit(self):
        """Test get_remaining_attempts returns max_attempts minus current attempts"""
        limiter = SimpleRateLimiter(max_attempts=5)
        key = "test_key"
        limiter.attempts[key] = [datetime.now(UTC)]

        assert limiter.get_remaining_attempts(key) == 4

