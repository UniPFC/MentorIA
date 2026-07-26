"""User service for business logic operations."""

from uuid import UUID

from sqlalchemy.orm import Session

from config.logger import logger
from config.settings import settings
from shared.database.models.user import User, UserLevel
from src.repositories.user import UserRepository


class UserService:
    """Service for user-related business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

    def deduct_tokens(
        self,
        user_id: UUID,
        input_tokens: int,
        output_tokens: int,
        input_multiplier: float = 1.0,
        output_multiplier: float = 1.0,
    ) -> User | None:
        """
        Deduct tokens from user budget with separate cost multipliers for input/output.

        Args:
            user_id: User ID to deduct tokens from
            input_tokens: Number of input tokens to deduct
            output_tokens: Number of output tokens to deduct
            input_multiplier: Cost multiplier for input tokens
            output_multiplier: Cost multiplier for output tokens

        Returns:
            Updated user object
        """
        actual_tokens = int(
            (input_tokens * input_multiplier) + (output_tokens * output_multiplier)
        )
        user = self.user_repo.deduct_tokens(user_id, actual_tokens)
        if user:
            logger.info(
                f"Tokens deducted: user_id={user_id} input_tokens={input_tokens} input_mult={input_multiplier} output_tokens={output_tokens} output_mult={output_multiplier} actual_tokens={actual_tokens} remaining={user.token_budget}"
            )
        return user

    def can_afford_tokens(
        self,
        user: User,
        input_tokens: int,
        output_tokens: int,
        reserve: int = 0,
        input_multiplier: float = 1.0,
        output_multiplier: float = 1.0,
    ) -> bool:
        """
        Check if user can afford tokens with optional reserve and separate cost multipliers.

        Args:
            user: User object
            input_tokens: Input tokens required
            output_tokens: Output tokens required
            reserve: Additional tokens to reserve (e.g., for output)
            input_multiplier: Cost multiplier for input tokens
            output_multiplier: Cost multiplier for output tokens

        Returns:
            True if user can afford the tokens, False otherwise
        """
        if user.has_unlimited_budget:
            return True

        if user.token_budget is None:
            return False

        actual_input_tokens = int(input_tokens * input_multiplier)
        actual_output_tokens = int(output_tokens * output_multiplier)
        return user.token_budget >= (
            actual_input_tokens + actual_output_tokens + reserve
        )

    def get_budget_for_level(self, level: UserLevel) -> int:
        """
        Get the token budget for a given level.

        Args:
            level: User level

        Returns:
            Token budget for the level, or 0 for unlimited (LEVEL_05)
        """
        budget_map = {
            UserLevel.LEVEL_01: settings.TOKEN_BUDGET_LEVEL_01,
            UserLevel.LEVEL_02: settings.TOKEN_BUDGET_LEVEL_02,
            UserLevel.LEVEL_03: settings.TOKEN_BUDGET_LEVEL_03,
            UserLevel.LEVEL_04: settings.TOKEN_BUDGET_LEVEL_04,
            UserLevel.LEVEL_05: None,  # Unlimited
        }
        return budget_map.get(level, 0) or 0

    def upgrade_user_level(self, user_id: UUID, new_level: UserLevel) -> User | None:
        """
        Upgrade user to a new level with corresponding budget.

        Args:
            user_id: User ID to upgrade
            new_level: Target level

        Returns:
            Updated user object
        """
        budget = self.get_budget_for_level(new_level)
        user = self.user_repo.set_user_level(
            user_id, new_level, budget if new_level != UserLevel.LEVEL_05 else None
        )
        if user:
            logger.info(
                f"User level upgraded: user_id={user_id} new_level={new_level} budget={budget}"
            )
        return user
