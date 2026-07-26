from datetime import UTC, datetime
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from shared.database.models.chat_type import ChatType
from shared.database.models.user import User
from src.api.routes.chat_types import enrich_chat_type_with_owner


@pytest.mark.unit
class TestChatTypesRoutes:
    """Testes unitários para rotas de chat types"""

    def test_enrich_chat_type_with_owner(self):
        """Testa enriquecimento de chat type com owner"""
        chat_type_id = uuid4()
        user_id = uuid4()

        owner = Mock()
        owner.username = "testuser"

        chat_type = Mock()
        chat_type.id = chat_type_id
        chat_type.name = "Test Chat Type"
        chat_type.description = "A test chat type"
        chat_type.is_public = True
        chat_type.owner_id = user_id
        chat_type.collection_name = "chat_type_test"
        chat_type.created_at = datetime.now(UTC)
        chat_type.owner = owner
        chat_type.tags = []

        result = enrich_chat_type_with_owner(chat_type)

        assert result["id"] == chat_type_id
        assert result["name"] == "Test Chat Type"
        assert result["owner_name"] == "testuser"
        assert result["is_favorited"] is False
        assert result["tags"] == []

    def test_enrich_chat_type_with_owner_no_owner(self):
        """Testa enriquecimento quando chat type não tem owner"""
        chat_type_id = uuid4()

        chat_type = Mock()
        chat_type.id = chat_type_id
        chat_type.name = "Test Chat Type"
        chat_type.description = "A test chat type"
        chat_type.is_public = True
        chat_type.owner_id = None
        chat_type.collection_name = "chat_type_test"
        chat_type.created_at = datetime.now(UTC)
        chat_type.owner = None
        chat_type.tags = []

        result = enrich_chat_type_with_owner(chat_type)

        assert result["owner_name"] is None

    def test_enrich_chat_type_with_favorite(self):
        """Testa enriquecimento com verificação de favorito"""
        chat_type_id = uuid4()
        user_id = uuid4()

        owner = Mock()
        owner.username = "testuser"

        chat_type = Mock()
        chat_type.id = chat_type_id
        chat_type.name = "Test Chat Type"
        chat_type.description = "A test chat type"
        chat_type.is_public = True
        chat_type.owner_id = user_id
        chat_type.collection_name = "chat_type_test"
        chat_type.created_at = datetime.now(UTC)
        chat_type.owner = owner
        chat_type.tags = []

        favorite_repo = Mock()
        favorite_repo.is_favorited.return_value = True

        result = enrich_chat_type_with_owner(chat_type, favorite_repo, user_id)

        assert result["is_favorited"] is True
        favorite_repo.is_favorited.assert_called_once_with(user_id, chat_type_id)

    def test_enrich_chat_type_with_tags(self):
        """Testa enriquecimento com tags"""
        chat_type_id = uuid4()
        user_id = uuid4()

        owner = Mock()
        owner.username = "testuser"

        tag1 = Mock()
        tag1.tag = "python"
        tag2 = Mock()
        tag2.tag = "testing"

        chat_type = Mock()
        chat_type.id = chat_type_id
        chat_type.name = "Test Chat Type"
        chat_type.description = "A test chat type"
        chat_type.is_public = True
        chat_type.owner_id = user_id
        chat_type.collection_name = "chat_type_test"
        chat_type.created_at = datetime.now(UTC)
        chat_type.owner = owner
        chat_type.tags = [tag1, tag2]

        result = enrich_chat_type_with_owner(chat_type)

        assert result["tags"] == ["python", "testing"]

    def test_enrich_chat_type_without_favorite_repo(self):
        """Testa enriquecimento sem favorite_repo"""
        chat_type_id = uuid4()

        chat_type = Mock()
        chat_type.id = chat_type_id
        chat_type.name = "Test Chat Type"
        chat_type.description = "A test chat type"
        chat_type.is_public = True
        chat_type.owner_id = None
        chat_type.collection_name = "chat_type_test"
        chat_type.created_at = datetime.now(UTC)
        chat_type.owner = None
        chat_type.tags = []

        result = enrich_chat_type_with_owner(chat_type, favorite_repo=None, user_id=None)

        assert result["is_favorited"] is False

    def test_enrich_chat_type_without_user_id(self):
        """Testa enriquecimento sem user_id"""
        chat_type_id = uuid4()

        chat_type = Mock()
        chat_type.id = chat_type_id
        chat_type.name = "Test Chat Type"
        chat_type.description = "A test chat type"
        chat_type.is_public = True
        chat_type.owner_id = None
        chat_type.collection_name = "chat_type_test"
        chat_type.created_at = datetime.now(UTC)
        chat_type.owner = None
        chat_type.tags = []

        favorite_repo = Mock()

        result = enrich_chat_type_with_owner(chat_type, favorite_repo, user_id=None)

        assert result["is_favorited"] is False
        favorite_repo.is_favorited.assert_not_called()


@pytest.mark.unit
class TestChatTypesEndpoints:
    """Testes unitários para endpoints de chat types"""

    def test_search_chat_types(self):
        """Testa search endpoint com dados reais"""
        from src.api.routes.chat_types import search_chat_types

        chat_type_repo = Mock()
        favorite_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()

        owner = User(id=current_user.id, username="testuser", email="test@example.com",
                     password_hash="hash", is_active=True)
        chat_type = ChatType(
            id=uuid4(),
            name="Test Chat Type",
            description="A test chat type",
            is_public=True,
            owner_id=current_user.id,
            collection_name="test_collection",
            created_at=datetime.now(UTC)
        )
        chat_type.owner = owner
        chat_type.tags = []

        chat_type_repo.search.return_value = ([chat_type], 1)
        favorite_repo.is_favorited.return_value = False

        result = search_chat_types(
            query="test",
            is_public=None,
            owner_id=None,
            skip=0,
            limit=100,
            current_user=current_user,
            chat_type_repo=chat_type_repo,
            favorite_repo=favorite_repo
        )

        chat_type_repo.search.assert_called_once_with(
            query="test",
            is_public=None,
            owner_id=None,
            user_id=current_user.id,
            skip=0,
            limit=100
        )
        assert result.total == 1
        assert len(result.chat_types) == 1
        assert result.chat_types[0].name == "Test Chat Type"

    def test_get_chat_type_private_forbidden(self):
        """Testa acesso a chat type privado de outro usuário"""
        from fastapi import HTTPException

        from src.api.routes.chat_types import get_chat_type

        chat_type_repo = Mock()
        favorite_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()

        other_user_id = uuid4()
        chat_type = Mock()
        chat_type.id = uuid4()
        chat_type.is_public = False
        chat_type.owner_id = other_user_id
        chat_type.owner = Mock()
        chat_type.owner.username = "otheruser"
        chat_type.tags = []

        chat_type_repo.get_by_id.return_value = chat_type

        with pytest.raises(HTTPException) as exc_info:
            get_chat_type(
                chat_type_id=chat_type.id,
                current_user=current_user,
                chat_type_repo=chat_type_repo,
                favorite_repo=favorite_repo
            )

        assert exc_info.value.status_code == 403

    def test_update_chat_type_not_found(self):
        """Testa update de chat type inexistente"""
        from fastapi import HTTPException

        from src.api.routes.chat_types import update_chat_type

        chat_type_repo = Mock()
        favorite_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()

        chat_type_repo.get_by_id.return_value = None

        chat_type_data = Mock()
        chat_type_data.name = None
        chat_type_data.description = None
        chat_type_data.is_public = None
        chat_type_data.tags = None

        with pytest.raises(HTTPException) as exc_info:
            update_chat_type(
                chat_type_id=uuid4(),
                chat_type_data=chat_type_data,
                current_user=current_user,
                chat_type_repo=chat_type_repo,
                favorite_repo=favorite_repo
            )

        assert exc_info.value.status_code == 404

    def test_update_chat_type_permission_denied(self):
        """Testa update sem permissão"""
        from fastapi import HTTPException

        from src.api.routes.chat_types import update_chat_type

        chat_type_repo = Mock()
        favorite_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()

        other_user_id = uuid4()
        chat_type = Mock()
        chat_type.id = uuid4()
        chat_type.owner_id = other_user_id
        chat_type.owner = Mock()
        chat_type.owner.username = "otheruser"
        chat_type.tags = []

        chat_type_repo.get_by_id.return_value = chat_type

        chat_type_data = Mock()
        chat_type_data.name = None
        chat_type_data.description = None
        chat_type_data.is_public = None
        chat_type_data.tags = None

        with pytest.raises(HTTPException) as exc_info:
            update_chat_type(
                chat_type_id=chat_type.id,
                chat_type_data=chat_type_data,
                current_user=current_user,
                chat_type_repo=chat_type_repo,
                favorite_repo=favorite_repo
            )

        assert exc_info.value.status_code == 403

    def test_delete_chat_type_not_found(self):
        """Testa delete de chat type inexistente"""
        from fastapi import HTTPException

        from src.api.routes.chat_types import delete_chat_type

        chat_type_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()

        chat_type_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            delete_chat_type(
                chat_type_id=uuid4(),
                current_user=current_user,
                chat_type_repo=chat_type_repo
            )

        assert exc_info.value.status_code == 404

    def test_delete_chat_type_permission_denied(self):
        """Testa delete sem permissão"""
        from fastapi import HTTPException

        from src.api.routes.chat_types import delete_chat_type

        chat_type_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()

        other_user_id = uuid4()
        chat_type = Mock()
        chat_type.id = uuid4()
        chat_type.owner_id = other_user_id
        chat_type.name = "Test"

        chat_type_repo.get_by_id.return_value = chat_type

        with pytest.raises(HTTPException) as exc_info:
            delete_chat_type(
                chat_type_id=chat_type.id,
                current_user=current_user,
                chat_type_repo=chat_type_repo
            )

        assert exc_info.value.status_code == 403

    def test_get_chat_type_info(self):
        """Testa get_chat_type_info endpoint"""
        from src.api.routes.chat_types import get_chat_type_info

        chat_type_repo = Mock()
        favorite_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()

        chat_type = Mock()
        chat_type.id = uuid4()
        chat_type.owner_id = current_user.id
        chat_type.owner = Mock()
        chat_type.owner.username = "testuser"
        chat_type.tags = []

        chat_type_repo.get_by_id.return_value = chat_type

        with patch('src.api.routes.chat_types.QdrantManager') as mock_qdrant, \
             patch('src.api.routes.chat_types.enrich_chat_type_with_owner') as mock_enrich:
            mock_qdrant.return_value.get_collection_info.return_value = {"points_count": 10}
            mock_enrich.return_value = {
                "id": str(chat_type.id),
                "name": "Test Chat Type",
                "description": "A test chat type",
                "is_public": True,
                "owner_id": str(current_user.id),
                "owner_name": "testuser",
                "collection_name": "test_collection",
                "created_at": datetime.now(UTC).isoformat(),
                "tags": [],
                "is_favorited": False
            }

            result = get_chat_type_info(
                chat_type_id=chat_type.id,
                current_user=current_user,
                chat_type_repo=chat_type_repo,
                favorite_repo=favorite_repo
            )

            assert "chat_type" in result
            assert "collection_info" in result
            assert result["collection_info"]["points_count"] == 10

    def test_favorite_chat_type(self):
        """Testa favoritar chat type"""
        from src.api.routes.chat_types import favorite_chat_type

        chat_type_repo = Mock()
        favorite_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()

        chat_type = Mock()
        chat_type.id = uuid4()
        chat_type.is_public = True
        chat_type.owner_id = current_user.id

        chat_type_repo.get_by_id.return_value = chat_type
        favorite_repo.is_favorited.return_value = False

        favorite = Mock()
        favorite.id = uuid4()
        favorite.user_id = current_user.id
        favorite.chat_type_id = chat_type.id
        favorite_repo.create.return_value = favorite

        with patch('src.api.routes.chat_types.ChatTypeFavoriteResponse') as mock_response:
            mock_response.model_validate.return_value = {"id": str(favorite.id)}
            result = favorite_chat_type(
                chat_type_id=chat_type.id,
                current_user=current_user,
                chat_type_repo=chat_type_repo,
                favorite_repo=favorite_repo
            )

            favorite_repo.create.assert_called_once_with(current_user.id, chat_type.id)

    def test_favorite_already_favorited(self):
        """Testa favoritar chat type já favoritado"""
        from fastapi import HTTPException

        from src.api.routes.chat_types import favorite_chat_type

        chat_type_repo = Mock()
        favorite_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()

        chat_type = Mock()
        chat_type.id = uuid4()
        chat_type.is_public = True
        chat_type.owner_id = current_user.id

        chat_type_repo.get_by_id.return_value = chat_type
        favorite_repo.is_favorited.return_value = True

        with pytest.raises(HTTPException) as exc_info:
            favorite_chat_type(
                chat_type_id=chat_type.id,
                current_user=current_user,
                chat_type_repo=chat_type_repo,
                favorite_repo=favorite_repo
            )

        assert exc_info.value.status_code == 400

    def test_unfavorite_chat_type(self):
        """Testa desfavoritar chat type"""
        from src.api.routes.chat_types import unfavorite_chat_type

        favorite_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()

        favorite_repo.delete_by_user_and_chat_type.return_value = True

        result = unfavorite_chat_type(
            chat_type_id=uuid4(),
            current_user=current_user,
            favorite_repo=favorite_repo
        )

        favorite_repo.delete_by_user_and_chat_type.assert_called_once()

    def test_unfavorite_not_in_favorites(self):
        """Testa desfavoritar chat type não favoritado"""
        from fastapi import HTTPException

        from src.api.routes.chat_types import unfavorite_chat_type

        favorite_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()

        favorite_repo.delete_by_user_and_chat_type.return_value = False

        with pytest.raises(HTTPException) as exc_info:
            unfavorite_chat_type(
                chat_type_id=uuid4(),
                current_user=current_user,
                favorite_repo=favorite_repo
            )

        assert exc_info.value.status_code == 404

    def test_create_chat_type_with_tags(self):
        """Testa criação de chat type com tags"""
        from src.api.routes.chat_types import create_chat_type

        chat_type_repo = Mock()
        favorite_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()

        chat_type_data = Mock()
        chat_type_data.name = "Test With Tags"
        chat_type_data.description = "Desc"
        chat_type_data.is_public = False
        chat_type_data.tags = ["python", "test"]

        new_chat_type = Mock()
        new_chat_type.id = uuid4()
        new_chat_type.name = "Test With Tags"
        new_chat_type.owner_id = current_user.id
        new_chat_type.owner = Mock()
        new_chat_type.owner.username = "testuser"
        new_chat_type.tags = []

        chat_type_repo.get_by_name.return_value = None
        chat_type_repo.create.return_value = new_chat_type
        chat_type_repo.get_by_id.return_value = new_chat_type

        with patch('src.api.routes.chat_types.QdrantManager'):
            with patch('src.api.routes.chat_types.ChatTypeResponse') as mock_response:
                mock_response.return_value = {"id": str(new_chat_type.id)}
                result = create_chat_type(
                    chat_type_data=chat_type_data,
                    current_user=current_user,
                    chat_type_repo=chat_type_repo,
                    favorite_repo=favorite_repo
                )

                chat_type_repo.add_tags.assert_called_once_with(new_chat_type.id, ["python", "test"])

    def test_create_chat_type_qdrant_error(self):
        """Testa criação quando Qdrant falha"""
        from fastapi import HTTPException

        from src.api.routes.chat_types import create_chat_type

        chat_type_repo = Mock()
        favorite_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()

        chat_type_data = Mock()
        chat_type_data.name = "Test"
        chat_type_data.description = "Desc"
        chat_type_data.is_public = False
        chat_type_data.tags = []

        new_chat_type = Mock()
        new_chat_type.id = uuid4()
        new_chat_type.name = "Test"

        chat_type_repo.get_by_name.return_value = None
        chat_type_repo.create.return_value = new_chat_type

        with patch('src.api.routes.chat_types.QdrantManager') as mock_qdrant:
            mock_qdrant.return_value.create_collection.side_effect = Exception("Qdrant error")

            with pytest.raises(HTTPException) as exc_info:
                create_chat_type(
                    chat_type_data=chat_type_data,
                    current_user=current_user,
                    chat_type_repo=chat_type_repo,
                    favorite_repo=favorite_repo
                )

            assert exc_info.value.status_code == 500
            chat_type_repo.delete.assert_called_once_with(new_chat_type)

    def test_create_chat_type_exception(self):
        """Testa criação com exceção genérica"""
        from fastapi import HTTPException

        from src.api.routes.chat_types import create_chat_type

        chat_type_repo = Mock()
        favorite_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()

        chat_type_data = Mock()
        chat_type_data.name = "Test"
        chat_type_data.description = "Desc"
        chat_type_data.is_public = False
        chat_type_data.tags = []

        chat_type_repo.get_by_name.side_effect = Exception("DB error")

        with pytest.raises(HTTPException) as exc_info:
            create_chat_type(
                chat_type_data=chat_type_data,
                current_user=current_user,
                chat_type_repo=chat_type_repo,
                favorite_repo=favorite_repo
            )

        assert exc_info.value.status_code == 500

    def test_search_chat_types_exception(self):
        """Testa search com exceção"""
        from fastapi import HTTPException

        from src.api.routes.chat_types import search_chat_types

        chat_type_repo = Mock()
        favorite_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()

        chat_type_repo.search.side_effect = Exception("DB error")

        with pytest.raises(HTTPException) as exc_info:
            search_chat_types(
                query=None,
                is_public=None,
                owner_id=None,
                skip=0,
                limit=100,
                current_user=current_user,
                chat_type_repo=chat_type_repo,
                favorite_repo=favorite_repo
            )

        assert exc_info.value.status_code == 500

    def test_list_chat_types_exception(self):
        """Testa list com exceção"""
        from fastapi import HTTPException

        from src.api.routes.chat_types import list_chat_types

        chat_type_repo = Mock()
        favorite_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()

        chat_type_repo.list_user_available.side_effect = Exception("DB error")

        with pytest.raises(HTTPException) as exc_info:
            list_chat_types(
                is_public=None,
                owner_id=None,
                skip=0,
                limit=100,
                current_user=current_user,
                chat_type_repo=chat_type_repo,
                favorite_repo=favorite_repo
            )

        assert exc_info.value.status_code == 500

    def test_update_chat_type_is_public(self):
        """Testa update de is_public"""
        from src.api.routes.chat_types import update_chat_type

        chat_type_repo = Mock()
        favorite_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()

        chat_type = Mock()
        chat_type.id = uuid4()
        chat_type.owner_id = current_user.id
        chat_type.name = "Test"
        chat_type.description = "Desc"
        chat_type.is_public = False
        chat_type.owner = Mock()
        chat_type.owner.username = "testuser"
        chat_type.tags = []

        chat_type_repo.get_by_id.return_value = chat_type
        chat_type_repo.create.return_value = chat_type

        chat_type_data = Mock()
        chat_type_data.name = None
        chat_type_data.description = None
        chat_type_data.is_public = True
        chat_type_data.tags = None

        with patch('src.api.routes.chat_types.ChatTypeResponse') as mock_response:
            mock_response.return_value = {"id": str(chat_type.id)}
            result = update_chat_type(
                chat_type_id=chat_type.id,
                chat_type_data=chat_type_data,
                current_user=current_user,
                chat_type_repo=chat_type_repo,
                favorite_repo=favorite_repo
            )

            assert chat_type.is_public is True

    def test_update_chat_type_tags(self):
        """Testa update de tags"""
        from src.api.routes.chat_types import update_chat_type

        chat_type_repo = Mock()
        favorite_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()

        chat_type = Mock()
        chat_type.id = uuid4()
        chat_type.owner_id = current_user.id
        chat_type.name = "Test"
        chat_type.description = "Desc"
        chat_type.is_public = False
        chat_type.owner = Mock()
        chat_type.owner.username = "testuser"
        chat_type.tags = []

        chat_type_repo.get_by_id.return_value = chat_type
        chat_type_repo.create.return_value = chat_type

        chat_type_data = Mock()
        chat_type_data.name = None
        chat_type_data.description = None
        chat_type_data.is_public = None
        chat_type_data.tags = ["new", "tags"]

        with patch('src.api.routes.chat_types.ChatTypeResponse') as mock_response:
            mock_response.return_value = {"id": str(chat_type.id)}
            result = update_chat_type(
                chat_type_id=chat_type.id,
                chat_type_data=chat_type_data,
                current_user=current_user,
                chat_type_repo=chat_type_repo,
                favorite_repo=favorite_repo
            )

            chat_type_repo.add_tags.assert_called_once_with(chat_type.id, ["new", "tags"])

    def test_update_chat_type_exception(self):
        """Testa update com exceção"""
        from fastapi import HTTPException

        from src.api.routes.chat_types import update_chat_type

        chat_type_repo = Mock()
        favorite_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()

        chat_type = Mock()
        chat_type.id = uuid4()
        chat_type.owner_id = current_user.id
        chat_type.name = "Test"
        chat_type.description = "Desc"
        chat_type.is_public = False
        chat_type.owner = Mock()
        chat_type.owner.username = "testuser"
        chat_type.tags = []

        chat_type_repo.get_by_id.return_value = chat_type
        chat_type_repo.create.side_effect = Exception("DB error")

        chat_type_data = Mock()
        chat_type_data.name = None
        chat_type_data.description = None
        chat_type_data.is_public = None
        chat_type_data.tags = None

        with pytest.raises(HTTPException) as exc_info:
            update_chat_type(
                chat_type_id=chat_type.id,
                chat_type_data=chat_type_data,
                current_user=current_user,
                chat_type_repo=chat_type_repo,
                favorite_repo=favorite_repo
            )

        assert exc_info.value.status_code == 500

    def test_delete_chat_type_exception(self):
        """Testa delete com exceção"""
        from fastapi import HTTPException

        from src.api.routes.chat_types import delete_chat_type

        chat_type_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()

        chat_type = Mock()
        chat_type.id = uuid4()
        chat_type.owner_id = current_user.id
        chat_type.name = "Test"

        chat_type_repo.get_by_id.return_value = chat_type

        with patch('src.api.routes.chat_types.QdrantManager') as mock_qdrant:
            mock_qdrant.return_value.delete_collection.side_effect = Exception("Qdrant error")

            with pytest.raises(HTTPException) as exc_info:
                delete_chat_type(
                    chat_type_id=chat_type.id,
                    current_user=current_user,
                    chat_type_repo=chat_type_repo
                )

            assert exc_info.value.status_code == 500

    def test_get_chat_type_info_not_found(self):
        """Testa get_chat_type_info com chat type inexistente"""
        from fastapi import HTTPException

        from src.api.routes.chat_types import get_chat_type_info

        chat_type_repo = Mock()
        favorite_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()

        chat_type_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            get_chat_type_info(
                chat_type_id=uuid4(),
                current_user=current_user,
                chat_type_repo=chat_type_repo,
                favorite_repo=favorite_repo
            )

        assert exc_info.value.status_code == 404

    def test_get_chat_type_info_permission_denied(self):
        """Testa get_chat_type_info sem permissão"""
        from fastapi import HTTPException

        from src.api.routes.chat_types import get_chat_type_info

        chat_type_repo = Mock()
        favorite_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()

        other_user_id = uuid4()
        chat_type = Mock()
        chat_type.id = uuid4()
        chat_type.owner_id = other_user_id
        chat_type.owner = Mock()
        chat_type.owner.username = "otheruser"
        chat_type.tags = []

        chat_type_repo.get_by_id.return_value = chat_type

        with pytest.raises(HTTPException) as exc_info:
            get_chat_type_info(
                chat_type_id=chat_type.id,
                current_user=current_user,
                chat_type_repo=chat_type_repo,
                favorite_repo=favorite_repo
            )

        assert exc_info.value.status_code == 403

    def test_get_chat_type_info_exception(self):
        """Testa get_chat_type_info com exceção no Qdrant"""
        from fastapi import HTTPException

        from src.api.routes.chat_types import get_chat_type_info

        chat_type_repo = Mock()
        favorite_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()

        chat_type = Mock()
        chat_type.id = uuid4()
        chat_type.owner_id = current_user.id
        chat_type.owner = Mock()
        chat_type.owner.username = "testuser"
        chat_type.tags = []

        chat_type_repo.get_by_id.return_value = chat_type

        with patch('src.api.routes.chat_types.QdrantManager') as mock_qdrant:
            mock_qdrant.return_value.get_collection_info.side_effect = Exception("Qdrant error")

            with pytest.raises(HTTPException) as exc_info:
                get_chat_type_info(
                    chat_type_id=chat_type.id,
                    current_user=current_user,
                    chat_type_repo=chat_type_repo,
                    favorite_repo=favorite_repo
                )

            assert exc_info.value.status_code == 500

    def test_favorite_chat_type_not_found(self):
        """Testa favoritar chat type inexistente"""
        from fastapi import HTTPException

        from src.api.routes.chat_types import favorite_chat_type

        chat_type_repo = Mock()
        favorite_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()

        chat_type_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            favorite_chat_type(
                chat_type_id=uuid4(),
                current_user=current_user,
                chat_type_repo=chat_type_repo,
                favorite_repo=favorite_repo
            )

        assert exc_info.value.status_code == 404

    def test_favorite_chat_type_permission_denied(self):
        """Testa favoritar chat type sem permissão"""
        from fastapi import HTTPException

        from src.api.routes.chat_types import favorite_chat_type

        chat_type_repo = Mock()
        favorite_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()

        other_user_id = uuid4()
        chat_type = Mock()
        chat_type.id = uuid4()
        chat_type.is_public = False
        chat_type.owner_id = other_user_id

        chat_type_repo.get_by_id.return_value = chat_type

        with pytest.raises(HTTPException) as exc_info:
            favorite_chat_type(
                chat_type_id=chat_type.id,
                current_user=current_user,
                chat_type_repo=chat_type_repo,
                favorite_repo=favorite_repo
            )

        assert exc_info.value.status_code == 403

    def test_favorite_chat_type_exception(self):
        """Testa favoritar com exceção"""
        from fastapi import HTTPException

        from src.api.routes.chat_types import favorite_chat_type

        chat_type_repo = Mock()
        favorite_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()

        chat_type = Mock()
        chat_type.id = uuid4()
        chat_type.is_public = True
        chat_type.owner_id = current_user.id

        chat_type_repo.get_by_id.return_value = chat_type
        favorite_repo.is_favorited.side_effect = Exception("DB error")

        with pytest.raises(HTTPException) as exc_info:
            favorite_chat_type(
                chat_type_id=chat_type.id,
                current_user=current_user,
                chat_type_repo=chat_type_repo,
                favorite_repo=favorite_repo
            )

        assert exc_info.value.status_code == 500

    def test_unfavorite_chat_type_exception(self):
        """Testa desfavoritar com exceção"""
        from fastapi import HTTPException

        from src.api.routes.chat_types import unfavorite_chat_type

        favorite_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()

        favorite_repo.delete_by_user_and_chat_type.side_effect = Exception("DB error")

        with pytest.raises(HTTPException) as exc_info:
            unfavorite_chat_type(
                chat_type_id=uuid4(),
                current_user=current_user,
                favorite_repo=favorite_repo
            )

        assert exc_info.value.status_code == 500


@pytest.mark.unit
class TestChatTypeBaseSchema:
    """Testes unitários para schema ChatTypeBase"""

    def test_validate_tags_none(self):
        """Testa validator com tags=None retorna lista vazia"""
        from src.api.schemas.chat_type import ChatTypeBase

        result = ChatTypeBase(name="Test", description="Desc", tags=None)
        assert result.tags == []

    def test_validate_tags_too_many(self):
        """Testa validator com mais de 15 tags"""
        from src.api.schemas.chat_type import ChatTypeBase

        with pytest.raises(ValueError, match="Maximum 15 tags allowed"):
            ChatTypeBase(name="Test", description="Desc", tags=["tag"] * 16)

    def test_validate_tags_empty_string(self):
        """Testa validator com tag vazia"""
        from src.api.schemas.chat_type import ChatTypeBase

        with pytest.raises(ValueError, match="Each tag must be a non-empty string"):
            ChatTypeBase(name="Test", description="Desc", tags=[""])

    def test_validate_tags_too_long(self):
        """Testa validator com tag maior que 50 caracteres"""
        from src.api.schemas.chat_type import ChatTypeBase

        with pytest.raises(ValueError, match="Each tag must be a non-empty string"):
            ChatTypeBase(name="Test", description="Desc", tags=["a" * 51])

    def test_validate_tags_valid(self):
        """Testa validator com tags válidas"""
        from src.api.schemas.chat_type import ChatTypeBase

        result = ChatTypeBase(name="Test", description="Desc", tags=["python", "testing"])
        assert result.tags == ["python", "testing"]


@pytest.mark.unit
class TestChatTypeUpdateSchema:
    """Testes unitários para schema ChatTypeUpdate"""

    def test_validate_tags_none(self):
        """Testa validator com tags=None"""
        from src.api.schemas.chat_type import ChatTypeUpdate

        result = ChatTypeUpdate(tags=None)
        assert result.tags is None

    def test_validate_tags_too_many(self):
        """Testa validator com mais de 15 tags"""
        from src.api.schemas.chat_type import ChatTypeUpdate

        with pytest.raises(ValueError, match="Maximum 15 tags allowed"):
            ChatTypeUpdate(tags=["tag"] * 16)

    def test_validate_tags_empty_string(self):
        """Testa validator com tag vazia"""
        from src.api.schemas.chat_type import ChatTypeUpdate

        with pytest.raises(ValueError, match="Each tag must be a non-empty string"):
            ChatTypeUpdate(tags=[""])

    def test_validate_tags_too_long(self):
        """Testa validator com tag maior que 50 caracteres"""
        from src.api.schemas.chat_type import ChatTypeUpdate

        with pytest.raises(ValueError, match="Each tag must be a non-empty string"):
            ChatTypeUpdate(tags=["a" * 51])

    def test_validate_tags_valid(self):
        """Testa validator com tags válidas"""
        from src.api.schemas.chat_type import ChatTypeUpdate

        result = ChatTypeUpdate(tags=["python", "testing"])
        assert result.tags == ["python", "testing"]
