"""Unit tests for token budget system."""

from shared.database.models.user import User, UserLevel


class TestUserModel:
    """Tests for User model budget-related properties."""

    def test_has_unlimited_budget_true_for_level_05(self):
        """Test that LEVEL_05 users have unlimited budget."""
        user = User(
            username="admin",
            email="admin@example.com",
            password_hash="hashed",
            level=UserLevel.LEVEL_05,
        )
        assert user.has_unlimited_budget is True

    def test_has_unlimited_budget_false_for_other_levels(self):
        """Test that non-LEVEL_05 users don't have unlimited budget."""
        for level in [
            UserLevel.LEVEL_01,
            UserLevel.LEVEL_02,
            UserLevel.LEVEL_03,
            UserLevel.LEVEL_04,
        ]:
            user = User(
                username="user",
                email="user@example.com",
                password_hash="hashed",
                level=level,
                token_budget=1000,
            )
            assert user.has_unlimited_budget is False

    def test_can_afford_tokens_true_unlimited(self):
        """Test that unlimited users can afford any amount."""
        user = User(
            username="admin",
            email="admin@example.com",
            password_hash="hashed",
            level=UserLevel.LEVEL_05,
        )
        assert user.can_afford_tokens(1000000) is True

    def test_can_afford_tokens_true_sufficient_budget(self):
        """Test that users can afford tokens if budget is sufficient."""
        user = User(
            username="user",
            email="user@example.com",
            password_hash="hashed",
            level=UserLevel.LEVEL_01,
            token_budget=1000,
        )
        assert user.can_afford_tokens(500) is True

    def test_can_afford_tokens_false_insufficient_budget(self):
        """Test that users cannot afford tokens if budget is insufficient."""
        user = User(
            username="user",
            email="user@example.com",
            password_hash="hashed",
            level=UserLevel.LEVEL_01,
            token_budget=100,
        )
        assert user.can_afford_tokens(500) is False

    def test_can_afford_tokens_false_no_budget(self):
        """Test that users cannot afford tokens if budget is None."""
        user = User(
            username="user",
            email="user@example.com",
            password_hash="hashed",
            level=UserLevel.LEVEL_01,
            token_budget=None,
        )
        assert user.can_afford_tokens(100) is False

    def test_can_afford_tokens_zero_needed(self):
        """Test that users can always afford zero tokens."""
        user = User(
            username="user",
            email="user@example.com",
            password_hash="hashed",
            level=UserLevel.LEVEL_01,
            token_budget=0,
        )
        assert user.can_afford_tokens(0) is True


class TestUserLevelEnum:
    """Tests for UserLevel enum."""

    def test_level_values(self):
        """Test that all expected levels exist."""
        assert UserLevel.LEVEL_01.value == "LEVEL_01"
        assert UserLevel.LEVEL_02.value == "LEVEL_02"
        assert UserLevel.LEVEL_03.value == "LEVEL_03"
        assert UserLevel.LEVEL_04.value == "LEVEL_04"
        assert UserLevel.LEVEL_05.value == "LEVEL_05"

    def test_level_order(self):
        """Test that levels are comparable for ordering."""
        levels = [
            UserLevel.LEVEL_01,
            UserLevel.LEVEL_02,
            UserLevel.LEVEL_03,
            UserLevel.LEVEL_04,
            UserLevel.LEVEL_05,
        ]
        assert levels == sorted(levels)
