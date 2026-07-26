from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest


@pytest.mark.unit
class TestUploadRoutes:
    """Testes unitários para rotas de upload"""

    @patch("src.api.routes.upload.settings")
    def test_get_ingestion_service_remote_provider(self, mock_settings):
        """Testa obtenção de serviço de ingestão com provider remoto"""
        mock_settings.EMBEDDING_PROVIDER = "remote"
        mock_settings.EMBEDDING_REMOTE_MODEL = "text-embedding-ada-002"
        mock_settings.EMBEDDING_REMOTE_PROVIDER = "openai"

        with (
            patch("src.api.routes.upload.RemoteEmbeddingProvider") as mock_remote,
            patch("src.api.routes.upload.EmbeddingEngine") as mock_engine,
            patch("src.api.routes.upload.QdrantManager") as mock_qdrant,
            patch("src.api.routes.upload.ChunkIngestionService") as mock_service,
        ):
            from src.api.routes.upload import get_ingestion_service

            mock_remote_instance = Mock()
            mock_remote.return_value = mock_remote_instance

            mock_engine_instance = Mock()
            mock_engine.return_value = mock_engine_instance

            mock_qdrant_instance = Mock()
            mock_qdrant.return_value = mock_qdrant_instance

            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance

            service = get_ingestion_service()

            mock_remote.assert_called_once_with(
                model_name="text-embedding-ada-002", provider_alias="openai"
            )
            mock_engine.assert_called_once_with(mock_remote_instance)
            mock_qdrant.assert_called_once()
            mock_service.assert_called_once_with(
                mock_engine_instance, mock_qdrant_instance
            )

    @patch("src.api.routes.upload.settings")
    def test_get_ingestion_service_hf_provider(self, mock_settings):
        """Testa obtenção de serviço de ingestão com provider HuggingFace"""
        mock_settings.EMBEDDING_PROVIDER = "huggingface"
        mock_settings.EMBEDDING_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"

        from src.api.routes.upload import get_ingestion_service

        with (
            patch("src.api.routes.upload.ModelLoader") as mock_loader,
            patch("src.api.routes.upload.HFEmbeddingProvider") as mock_hf,
            patch("src.api.routes.upload.EmbeddingEngine") as mock_engine,
            patch("src.api.routes.upload.QdrantManager") as mock_qdrant,
            patch("src.api.routes.upload.ChunkIngestionService") as mock_service,
        ):
            mock_loader_instance = Mock()
            mock_loader.return_value = mock_loader_instance

            mock_model = Mock()
            mock_tokenizer = Mock()
            mock_loader_instance.load_embedding.return_value = (
                mock_model,
                mock_tokenizer,
            )

            mock_hf_instance = Mock()
            mock_hf.return_value = mock_hf_instance

            mock_engine_instance = Mock()
            mock_engine.return_value = mock_engine_instance

            mock_qdrant_instance = Mock()
            mock_qdrant.return_value = mock_qdrant_instance

            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance

            service = get_ingestion_service()

            mock_loader.assert_called_once()
            mock_loader_instance.load_embedding.assert_called_once_with(
                "sentence-transformers/all-MiniLM-L6-v2"
            )
            mock_hf.assert_called_once_with(mock_model, mock_tokenizer)


@pytest.mark.unit
class TestUploadAddChunks:
    """Testes unitários para add_chunks_to_chat_type"""

    def test_add_chunks_chat_type_not_found(self):
        """Testa adicionar chunks a chat type inexistente"""
        from fastapi import HTTPException

        from src.api.routes.upload import add_chunks_to_chat_type

        chat_type_repo = Mock()
        chat_type_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            import asyncio

            asyncio.run(
                add_chunks_to_chat_type(
                    chat_type_id=uuid4(),
                    file=Mock(),
                    question_column="question",
                    answer_column="answer",
                    db=Mock(),
                    current_user=Mock(),
                    ingestion_service=Mock(),
                    chat_type_repo=chat_type_repo,
                )
            )

        assert exc_info.value.status_code == 404

    def test_add_chunks_permission_denied(self):
        """Testa adicionar chunks sem permissão"""
        from fastapi import HTTPException

        from src.api.routes.upload import add_chunks_to_chat_type

        chat_type_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()

        other_user_id = uuid4()
        chat_type = Mock()
        chat_type.id = uuid4()
        chat_type.owner_id = other_user_id

        chat_type_repo.get_by_id.return_value = chat_type

        with pytest.raises(HTTPException) as exc_info:
            import asyncio

            asyncio.run(
                add_chunks_to_chat_type(
                    chat_type_id=chat_type.id,
                    file=Mock(),
                    question_column="question",
                    answer_column="answer",
                    db=Mock(),
                    current_user=current_user,
                    ingestion_service=Mock(),
                    chat_type_repo=chat_type_repo,
                )
            )

        assert exc_info.value.status_code == 403

    def test_add_chunks_invalid_file(self):
        """Testa adicionar chunks com arquivo inválido"""
        from fastapi import HTTPException

        from src.api.routes.upload import add_chunks_to_chat_type

        chat_type_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()

        chat_type = Mock()
        chat_type.id = uuid4()
        chat_type.owner_id = current_user.id

        chat_type_repo.get_by_id.return_value = chat_type

        mock_file = Mock()
        mock_file.filename = "test.txt"

        with pytest.raises(HTTPException) as exc_info:
            import asyncio

            asyncio.run(
                add_chunks_to_chat_type(
                    chat_type_id=chat_type.id,
                    file=mock_file,
                    question_column="question",
                    answer_column="answer",
                    db=Mock(),
                    current_user=current_user,
                    ingestion_service=Mock(),
                    chat_type_repo=chat_type_repo,
                )
            )

        assert exc_info.value.status_code == 400

    def test_add_chunks_success(self):
        """Testa adicionar chunks com sucesso"""
        import asyncio

        from src.api.routes.upload import add_chunks_to_chat_type

        chat_type_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()

        chat_type = Mock()
        chat_type.id = uuid4()
        chat_type.owner_id = current_user.id
        chat_type.name = "Test"

        chat_type_repo.get_by_id.return_value = chat_type

        mock_file = Mock()
        mock_file.filename = "test.xlsx"
        mock_file.read = AsyncMock(return_value=b"fake excel content")

        ingestion_service = Mock()
        ingestion_service.ingest_from_file.return_value = (["id1", "id2"], 10)

        result = asyncio.run(
            add_chunks_to_chat_type(
                chat_type_id=chat_type.id,
                file=mock_file,
                question_column="question",
                answer_column="answer",
                db=Mock(),
                current_user=current_user,
                ingestion_service=ingestion_service,
                chat_type_repo=chat_type_repo,
            )
        )

        assert result.chunks_ingested == 10
        ingestion_service.ingest_from_file.assert_called_once()

    def test_add_chunks_exception(self):
        """Testa adicionar chunks com exceção"""
        import asyncio

        from fastapi import HTTPException

        from src.api.routes.upload import add_chunks_to_chat_type

        chat_type_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()

        chat_type = Mock()
        chat_type.id = uuid4()
        chat_type.owner_id = current_user.id
        chat_type.name = "Test"

        chat_type_repo.get_by_id.return_value = chat_type

        mock_file = Mock()
        mock_file.filename = "test.xlsx"

        ingestion_service = Mock()
        ingestion_service.ingest_from_file.side_effect = Exception("Ingest error")

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                add_chunks_to_chat_type(
                    chat_type_id=chat_type.id,
                    file=mock_file,
                    question_column="question",
                    answer_column="answer",
                    db=Mock(),
                    current_user=current_user,
                    ingestion_service=ingestion_service,
                    chat_type_repo=chat_type_repo,
                )
            )

        assert exc_info.value.status_code == 500

    def test_create_chat_type_from_file_qdrant_error(self):
        """Testa create_chat_type_from_file quando Qdrant falha"""
        import asyncio

        from fastapi import HTTPException

        from src.api.routes.upload import create_chat_type_from_file

        chat_type_repo = Mock()
        job_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()

        mock_file = Mock()
        mock_file.filename = "test.xlsx"

        chat_type_repo.get_by_name.return_value = None
        chat_type_repo.create.side_effect = Exception("DB error")

        with patch("src.api.routes.upload.settings") as mock_settings:
            mock_settings.ALLOWED_EXTENSIONS = [".xlsx"]
            mock_settings.EMBEDDING_PROVIDER = "remote"
            mock_settings.EMBEDDING_REMOTE_MODEL = "text-embedding-ada-002"
            mock_settings.EMBEDDING_REMOTE_PROVIDER = "openai"

            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(
                    create_chat_type_from_file(
                        name="Test",
                        file=mock_file,
                        db=Mock(),
                        current_user=current_user,
                        ingestion_service=Mock(),
                        chat_type_repo=chat_type_repo,
                        job_repo=job_repo,
                        background_tasks=Mock(),
                    )
                )

            assert exc_info.value.status_code == 500

    def test_create_chat_type_from_file_exception(self):
        """Testa create_chat_type_from_file com exceção genérica"""
        import asyncio

        from fastapi import HTTPException

        from src.api.routes.upload import create_chat_type_from_file

        chat_type_repo = Mock()
        job_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()

        mock_file = Mock()
        mock_file.filename = "test.xlsx"

        chat_type_repo.get_by_name.side_effect = Exception("Unexpected error")

        with patch("src.api.routes.upload.settings") as mock_settings:
            mock_settings.ALLOWED_EXTENSIONS = [".xlsx"]
            mock_settings.EMBEDDING_PROVIDER = "remote"
            mock_settings.EMBEDDING_REMOTE_MODEL = "text-embedding-ada-002"
            mock_settings.EMBEDDING_REMOTE_PROVIDER = "openai"

            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(
                    create_chat_type_from_file(
                        name="Test",
                        file=mock_file,
                        db=Mock(),
                        current_user=current_user,
                        ingestion_service=Mock(),
                        chat_type_repo=chat_type_repo,
                        job_repo=job_repo,
                        background_tasks=Mock(),
                    )
                )

            assert exc_info.value.status_code == 500

    def test_create_chat_type_from_file_success(self):
        """Testa create_chat_type_from_file com sucesso completo"""
        import asyncio

        from shared.database.models.chat_type import ChatType
        from shared.database.models.ingestion_job import IngestionJob
        from src.api.routes.upload import create_chat_type_from_file

        chat_type_repo = Mock()
        job_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()

        mock_file = Mock()
        mock_file.filename = "test.xlsx"
        mock_file.read = AsyncMock(return_value=b"fake excel content")

        new_chat_type = ChatType(
            id=uuid4(),
            name="Test",
            description="Desc",
            is_public=False,
            owner_id=current_user.id,
            collection_name="test_collection",
        )
        new_job = IngestionJob(
            id=uuid4(),
            chat_type_id=new_chat_type.id,
            filename="test.xlsx",
            status="pending",
        )

        chat_type_repo.get_by_name.return_value = None
        chat_type_repo.create.return_value = new_chat_type
        job_repo.create.return_value = new_job

        with (
            patch("src.api.routes.upload.settings") as mock_settings,
            patch("src.api.routes.upload.QdrantManager") as mock_qdrant,
        ):
            mock_settings.ALLOWED_EXTENSIONS = [".xlsx"]
            mock_settings.EMBEDDING_PROVIDER = "remote"
            mock_settings.EMBEDDING_REMOTE_MODEL = "text-embedding-ada-002"
            mock_settings.EMBEDDING_REMOTE_PROVIDER = "openai"

            background_tasks = Mock()

            result = asyncio.run(
                create_chat_type_from_file(
                    name="Test",
                    file=mock_file,
                    db=Mock(),
                    current_user=current_user,
                    ingestion_service=Mock(),
                    chat_type_repo=chat_type_repo,
                    job_repo=job_repo,
                    background_tasks=background_tasks,
                )
            )

            assert result.job_id == new_job.id
            assert result.chat_type_id == new_chat_type.id
            background_tasks.add_task.assert_called_once()

    def test_create_chat_type_from_file_invalid_extension(self):
        """Testa create_chat_type_from_file com extensão inválida"""
        import asyncio

        from fastapi import HTTPException

        from src.api.routes.upload import create_chat_type_from_file

        chat_type_repo = Mock()
        job_repo = Mock()
        current_user = Mock()
        current_user.id = uuid4()

        mock_file = Mock()
        mock_file.filename = "test.txt"

        with patch("src.api.routes.upload.settings") as mock_settings:
            mock_settings.ALLOWED_EXTENSIONS = [".xlsx", ".csv"]

            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(
                    create_chat_type_from_file(
                        name="Test",
                        file=mock_file,
                        db=Mock(),
                        current_user=current_user,
                        ingestion_service=Mock(),
                        chat_type_repo=chat_type_repo,
                        job_repo=job_repo,
                        background_tasks=Mock(),
                    )
                )

            assert exc_info.value.status_code == 400
