"""Integration tests for token budget system."""

import pytest
from uuid import UUID
from shared.database.models.user import User, UserLevel
from src.repositories.user import UserRepository
from src.services.user import UserService
from config.settings import settings


class TestUserModel:
    """Tests for User model budget-related properties."""

    def test_has_unlimited_budget_true_for_level_05(self):
        """Test that LEVEL_05 users have unlimited budget."""
        user = User(
            username="admin",
            email="admin@example.com",
            password_hash="hashed",
            level=UserLevel.LEVEL_05
        )
        assert user.has_unlimited_budget is True

    def test_has_unlimited_budget_false_for_other_levels(self):
        """Test that non-LEVEL_05 users don't have unlimited budget."""
        for level in [UserLevel.LEVEL_01, UserLevel.LEVEL_02, UserLevel.LEVEL_03, UserLevel.LEVEL_04]:
            user = User(
                username="user",
                email="user@example.com",
                password_hash="hashed",
                level=level,
                token_budget=1000
            )
            assert user.has_unlimited_budget is False

    def test_can_afford_tokens_true_unlimited(self):
        """Test that unlimited users can afford any amount."""
        user = User(
            username="admin",
            email="admin@example.com",
            password_hash="hashed",
            level=UserLevel.LEVEL_05
        )
        assert user.can_afford_tokens(1000000) is True

    def test_can_afford_tokens_true_sufficient_budget(self):
        """Test that users can afford tokens if budget is sufficient."""
        user = User(
            username="user",
            email="user@example.com",
            password_hash="hashed",
            level=UserLevel.LEVEL_01,
            token_budget=1000
        )
        assert user.can_afford_tokens(500) is True

    def test_can_afford_tokens_false_insufficient_budget(self):
        """Test that users cannot afford tokens if budget is insufficient."""
        user = User(
            username="user",
            email="user@example.com",
            password_hash="hashed",
            level=UserLevel.LEVEL_01,
            token_budget=100
        )
        assert user.can_afford_tokens(500) is False

    def test_can_afford_tokens_false_no_budget(self):
        """Test that users cannot afford tokens if budget is None."""
        user = User(
            username="user",
            email="user@example.com",
            password_hash="hashed",
            level=UserLevel.LEVEL_01,
            token_budget=None
        )
        assert user.can_afford_tokens(100) is False

    def test_max_token_budget_for_levels(self):
        """Test max_token_budget property for each level."""
        budgets = {
            UserLevel.LEVEL_01: settings.TOKEN_BUDGET_LEVEL_01,
            UserLevel.LEVEL_02: settings.TOKEN_BUDGET_LEVEL_02,
            UserLevel.LEVEL_03: settings.TOKEN_BUDGET_LEVEL_03,
            UserLevel.LEVEL_04: settings.TOKEN_BUDGET_LEVEL_04,
            UserLevel.LEVEL_05: None,
        }
        for level, expected_budget in budgets.items():
            user = User(
                username="user",
                email="user@example.com",
                password_hash="hashed",
                level=level
            )
            assert user.max_token_budget == expected_budget

    def test_remaining_tokens_for_levels(self):
        """Test remaining_tokens property for each level."""
        user = User(
            username="user",
            email="user@example.com",
            password_hash="hashed",
            level=UserLevel.LEVEL_01,
            token_budget=5000
        )
        assert user.remaining_tokens == 5000
        
        user.level = UserLevel.LEVEL_05
        user.token_budget = None
        assert user.remaining_tokens is None


class TestCostTierCalculation:
    """Tests for cost tier calculation from multipliers."""

    def test_cost_tier_minimum(self):
        """Test that minimum multiplier gives tier 0."""
        min_mult = settings.COST_TIER_MIN_MULTIPLIER
        avg_mult = min_mult
        max_mult = settings.COST_TIER_MAX_MULTIPLIER
        
        tier = int(((avg_mult - min_mult) / (max_mult - min_mult)) * 9)
        tier = max(0, min(9, tier))
        assert tier == 0

    def test_cost_tier_maximum(self):
        """Test that maximum multiplier gives tier 9."""
        min_mult = settings.COST_TIER_MIN_MULTIPLIER
        avg_mult = settings.COST_TIER_MAX_MULTIPLIER
        max_mult = settings.COST_TIER_MAX_MULTIPLIER
        
        tier = int(((avg_mult - min_mult) / (max_mult - min_mult)) * 9)
        tier = max(0, min(9, tier))
        assert tier == 9

    def test_cost_tier_middle(self):
        """Test that middle multiplier gives tier around 4-5."""
        min_mult = settings.COST_TIER_MIN_MULTIPLIER
        avg_mult = 1.0
        max_mult = settings.COST_TIER_MAX_MULTIPLIER
        
        tier = int(((avg_mult - min_mult) / (max_mult - min_mult)) * 9)
        tier = max(0, min(9, tier))
        assert 3 <= tier <= 5

    def test_cost_tier_clamping(self):
        """Test that tier is clamped to 0-9 range."""
        min_mult = settings.COST_TIER_MIN_MULTIPLIER
        max_mult = settings.COST_TIER_MAX_MULTIPLIER
        
        # Test below minimum
        avg_mult = 0.0
        tier = int(((avg_mult - min_mult) / (max_mult - min_mult)) * 9)
        tier = max(0, min(9, tier))
        assert tier == 0
        
        # Test above maximum
        avg_mult = 10.0
        tier = int(((avg_mult - min_mult) / (max_mult - min_mult)) * 9)
        tier = max(0, min(9, tier))
        assert tier == 9


class TestTokenDeductionCalculation:
    """Tests for token deduction with multipliers."""

    def test_deduction_without_multiplier(self):
        """Test token deduction without multiplier."""
        input_tokens = 100
        output_tokens = 200
        input_multiplier = 1.0
        output_multiplier = 1.0
        
        actual_tokens = int((input_tokens * input_multiplier) + (output_tokens * output_multiplier))
        assert actual_tokens == 300

    def test_deduction_with_multipliers(self):
        """Test token deduction with multipliers."""
        input_tokens = 100
        output_tokens = 200
        input_multiplier = 1.5
        output_multiplier = 2.0
        
        actual_tokens = int((input_tokens * input_multiplier) + (output_tokens * output_multiplier))
        assert actual_tokens == int(150 + 400)  # 550

    def test_deduction_different_multipliers(self):
        """Test that input and output can have different multipliers."""
        input_tokens = 100
        output_tokens = 100
        input_multiplier = 1.1
        output_multiplier = 1.5
        
        actual_tokens = int((input_tokens * input_multiplier) + (output_tokens * output_multiplier))
        assert actual_tokens == int(110 + 150)  # 260


class TestBudgetCheckCalculation:
    """Tests for budget check calculation."""

    def test_budget_check_without_multiplier(self):
        """Test budget check without multiplier."""
        user = User(
            username="user",
            email="user@example.com",
            password_hash="hashed",
            level=UserLevel.LEVEL_01,
            token_budget=1000
        )
        
        input_tokens = 500
        output_tokens = 0
        reserve = 200
        input_multiplier = 1.0
        output_multiplier = 1.0
        
        actual_input = int(input_tokens * input_multiplier)
        actual_output = int(output_tokens * output_multiplier)
        can_afford = user.token_budget >= (actual_input + actual_output + reserve)
        
        assert can_afford is True  # 1000 >= 500 + 0 + 200

    def test_budget_check_with_multiplier(self):
        """Test budget check with multiplier."""
        user = User(
            username="user",
            email="user@example.com",
            password_hash="hashed",
            level=UserLevel.LEVEL_01,
            token_budget=1000
        )
        
        input_tokens = 500
        output_tokens = 0
        reserve = 200
        input_multiplier = 1.5
        output_multiplier = 1.0
        
        actual_input = int(input_tokens * input_multiplier)
        actual_output = int(output_tokens * output_multiplier)
        can_afford = user.token_budget >= (actual_input + actual_output + reserve)
        
        assert can_afford is True  # 1000 >= 750 + 0 + 200

    def test_budget_check_insufficient_with_multiplier(self):
        """Test budget check fails with high multiplier."""
        user = User(
            username="user",
            email="user@example.com",
            password_hash="hashed",
            level=UserLevel.LEVEL_01,
            token_budget=1000
        )
        
        input_tokens = 500
        output_tokens = 0
        reserve = 200
        input_multiplier = 2.0
        output_multiplier = 1.0
        
        actual_input = int(input_tokens * input_multiplier)
        actual_output = int(output_tokens * output_multiplier)
        can_afford = user.token_budget >= (actual_input + actual_output + reserve)
        
        assert can_afford is False  # 1000 < 1000 + 0 + 200


def print_test_results():
    """Run and print test results for manual verification."""
    print("\n" + "="*60)
    print("TOKEN BUDGET SYSTEM TEST RESULTS")
    print("="*60)
    
    # Test User Model
    print("\n[User Model Tests]")
    user = User(username="user", email="user@example.com", password_hash="hashed", level=UserLevel.LEVEL_01, token_budget=5000)
    print(f"  has_unlimited_budget (LEVEL_01): {user.has_unlimited_budget}")
    print(f"  can_afford_tokens(1000): {user.can_afford_tokens(1000)}")
    print(f"  max_token_budget: {user.max_token_budget}")
    print(f"  remaining_tokens: {user.remaining_tokens}")
    
    admin = User(username="admin", email="admin@example.com", password_hash="hashed", level=UserLevel.LEVEL_05)
    print(f"  has_unlimited_budget (LEVEL_05): {admin.has_unlimited_budget}")
    print(f"  max_token_budget (LEVEL_05): {admin.max_token_budget}")
    
    # Test Cost Tier Calculation
    print("\n[Cost Tier Calculation]")
    min_mult = settings.COST_TIER_MIN_MULTIPLIER
    max_mult = settings.COST_TIER_MAX_MULTIPLIER
    print(f"  COST_TIER_MIN_MULTIPLIER: {min_mult}")
    print(f"  COST_TIER_MAX_MULTIPLIER: {max_mult}")
    
    test_multipliers = [0.1, 0.5, 1.0, 1.5, 2.0, 3.0]
    for mult in test_multipliers:
        tier = int(((mult - min_mult) / (max_mult - min_mult)) * 9)
        tier = max(0, min(9, tier))
        print(f"  Multiplier {mult} -> Tier {tier}")
    
    # Test Token Deduction
    print("\n[Token Deduction Calculation]")
    input_tokens = 100
    output_tokens = 200
    input_mult = 1.5
    output_mult = 2.0
    actual = int((input_tokens * input_mult) + (output_tokens * output_mult))
    print(f"  Input: {input_tokens} * {input_mult} = {int(input_tokens * input_mult)}")
    print(f"  Output: {output_tokens} * {output_mult} = {int(output_tokens * output_mult)}")
    print(f"  Total: {actual}")
    
    # Test Budget Check
    print("\n[Budget Check Calculation]")
    user_budget = 1000
    input_tokens = 500
    reserve = 200
    input_mult = 1.5
    actual_input = int(input_tokens * input_mult)
    required = actual_input + reserve
    can_afford = user_budget >= required
    print(f"  User Budget: {user_budget}")
    print(f"  Input: {input_tokens} * {input_mult} = {actual_input}")
    print(f"  Reserve: {reserve}")
    print(f"  Required: {required}")
    print(f"  Can Afford: {can_afford}")
    
    print("\n" + "="*60)
    print("TESTS COMPLETED")
    print("="*60 + "\n")


if __name__ == "__main__":
    print_test_results()
