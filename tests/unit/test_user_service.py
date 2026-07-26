from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from shared.database.models.user import User, UserLevel
from src.services.user import UserService


@pytest.mark.unit
class TestUserService:
    """Testes unitários para UserService"""

    def test_init(self):
        """Testa inicialização do UserService"""
        db = Mock()
        service = UserService(db)
        assert service.db == db
        assert service.user_repo is not None

    def test_deduct_tokens_success(self):
        """Testa dedução de tokens com sucesso"""
        db = Mock()
        user_id = uuid4()
        user = Mock(spec=User)
        user.token_budget = 500

        service = UserService(db)
        with patch.object(
            service.user_repo, "deduct_tokens", return_value=user
        ) as mock_deduct:
            result = service.deduct_tokens(
                user_id=user_id,
                input_tokens=100,
                output_tokens=50,
                input_multiplier=1.5,
                output_multiplier=2.0,
            )

            # (100 * 1.5) + (50 * 2.0) = 150 + 100 = 250
            mock_deduct.assert_called_once_with(user_id, 250)
            assert result == user

    def test_deduct_tokens_user_not_found(self):
        """Testa dedução de tokens quando usuário não é retornado"""
        db = Mock()
        user_id = uuid4()

        service = UserService(db)
        with patch.object(service.user_repo, "deduct_tokens", return_value=None):
            result = service.deduct_tokens(user_id, 10, 10)
            assert result is None

    def test_can_afford_tokens_unlimited(self):
        """Testa can_afford_tokens para usuário com orçamento ilimitado"""
        service = UserService(Mock())
        user = Mock(spec=User)
        user.has_unlimited_budget = True

        assert service.can_afford_tokens(user, 100, 100) is True

    def test_can_afford_tokens_none_budget(self):
        """Testa can_afford_tokens quando orçamento do usuário é None"""
        service = UserService(Mock())
        user = Mock(spec=User)
        user.has_unlimited_budget = False
        user.token_budget = None

        assert service.can_afford_tokens(user, 10, 10) is False

    def test_can_afford_tokens_with_reserve_and_multipliers(self):
        """Testa can_afford_tokens considerando reserve e multipliers"""
        service = UserService(Mock())
        user = Mock(spec=User)
        user.has_unlimited_budget = False

        # Caso 1: Orçamento suficiente
        # (10 * 2.0) + (20 * 1.5) + 10 = 20 + 30 + 10 = 60
        user.token_budget = 60
        assert (
            service.can_afford_tokens(
                user=user,
                input_tokens=10,
                output_tokens=20,
                reserve=10,
                input_multiplier=2.0,
                output_multiplier=1.5,
            )
            is True
        )

        # Caso 2: Orçamento insuficiente
        user.token_budget = 59
        assert (
            service.can_afford_tokens(
                user=user,
                input_tokens=10,
                output_tokens=20,
                reserve=10,
                input_multiplier=2.0,
                output_multiplier=1.5,
            )
            is False
        )

    def test_get_budget_for_level(self):
        """Testa obtenção do orçamento padrão por nível"""
        service = UserService(Mock())
        with patch("src.services.user.settings") as mock_settings:
            mock_settings.TOKEN_BUDGET_LEVEL_01 = 1000
            mock_settings.TOKEN_BUDGET_LEVEL_02 = 2000
            mock_settings.TOKEN_BUDGET_LEVEL_03 = 3000
            mock_settings.TOKEN_BUDGET_LEVEL_04 = 4000

            assert service.get_budget_for_level(UserLevel.LEVEL_01) == 1000
            assert service.get_budget_for_level(UserLevel.LEVEL_02) == 2000
            assert service.get_budget_for_level(UserLevel.LEVEL_03) == 3000
            assert service.get_budget_for_level(UserLevel.LEVEL_04) == 4000
            assert (
                service.get_budget_for_level(UserLevel.LEVEL_05) == 0
            )  # None/Unlimited gets fallback to 0
            assert service.get_budget_for_level("NON_EXISTENT_LEVEL") == 0

    def test_upgrade_user_level_success(self):
        """Testa upgrade de nível com sucesso"""
        db = Mock()
        user_id = uuid4()
        user = Mock(spec=User)

        service = UserService(db)
        with (
            patch.object(
                service, "get_budget_for_level", return_value=3000
            ) as mock_get_budget,
            patch.object(
                service.user_repo, "set_user_level", return_value=user
            ) as mock_set_level,
        ):
            result = service.upgrade_user_level(user_id, UserLevel.LEVEL_03)

            mock_get_budget.assert_called_once_with(UserLevel.LEVEL_03)
            mock_set_level.assert_called_once_with(user_id, UserLevel.LEVEL_03, 3000)
            assert result == user

    def test_upgrade_user_level_level_05_unlimited(self):
        """Testa upgrade de nível para LEVEL_05 (ilimitado, orçamento nulo)"""
        db = Mock()
        user_id = uuid4()
        user = Mock(spec=User)

        service = UserService(db)
        with (
            patch.object(service, "get_budget_for_level", return_value=0),
            patch.object(
                service.user_repo, "set_user_level", return_value=user
            ) as mock_set_level,
        ):
            result = service.upgrade_user_level(user_id, UserLevel.LEVEL_05)
            mock_set_level.assert_called_once_with(user_id, UserLevel.LEVEL_05, None)
            assert result == user

    def test_upgrade_user_level_user_not_found(self):
        """Testa upgrade de nível quando set_user_level retorna None"""
        db = Mock()
        user_id = uuid4()

        service = UserService(db)
        with (
            patch.object(service, "get_budget_for_level", return_value=1000),
            patch.object(service.user_repo, "set_user_level", return_value=None),
        ):
            result = service.upgrade_user_level(user_id, UserLevel.LEVEL_01)
            assert result is None
