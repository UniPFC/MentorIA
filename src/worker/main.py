import asyncio
import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from config.logger import logger
from shared.database.models.chat_type import ChatType
from shared.database.models.ingestion_job import IngestionJob, IngestionStatus
from shared.database.session import SessionLocal
from shared.qdrant.client import QdrantManager
from src.api.schemas.worker import WorkerGenerateRequest, WorkerGenerateResponse
from src.rag.pipeline import RAGPipeline

# Global semaphore for limiting concurrent RAG pipeline executions
semaphore = asyncio.Semaphore(3)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events for the worker app."""
    logger.info("Starting AI Worker...")
    # Initialize the RAGPipeline which loads models into memory
    try:
        pipeline = RAGPipeline()
        logger.info("RAG Pipeline initialized in worker.")

        from src.ai.stt_loader import get_stt_loader

        stt_loader = get_stt_loader()
        # Force initialization/loading
        stt_loader.get_provider()
        logger.info("STT Pipeline initialized in worker.")

        # Cleanup zombie jobs

        logger.info("Cleaning up zombie ingestion jobs...")
        db_session = SessionLocal()
        try:
            stale_jobs = (
                db_session.query(IngestionJob)
                .filter(
                    IngestionJob.status.in_(
                        [IngestionStatus.PENDING, IngestionStatus.PROCESSING]
                    )
                )
                .all()
            )

            if stale_jobs:
                qdrant = QdrantManager()

                for job in stale_jobs:
                    logger.info(
                        f"Deleting zombie job {job.id} and its ChatType {job.chat_type_id}"
                    )
                    # Try to delete ChatType and Qdrant collection
                    chat_type = (
                        db_session.query(ChatType)
                        .filter(ChatType.id == job.chat_type_id)
                        .first()
                    )
                    if chat_type:
                        try:
                            qdrant.delete_collection(chat_type.id)
                        except Exception as e:
                            logger.warning(
                                f"Failed to delete Qdrant collection for {chat_type.id}: {e}"
                            )
                        db_session.delete(chat_type)

                    db_session.delete(job)

                db_session.commit()
                logger.info(
                    f"Deleted {len(stale_jobs)} stale jobs and their chat types."
                )
        except Exception as cleanup_err:
            logger.error(f"Failed to cleanup zombie jobs: {cleanup_err}")
        finally:
            db_session.close()

        from config.settings import settings

        if settings.AUTO_RUN_SEEDER:
            logger.info("Running background seeder in worker...")
            from src.services.seeder import seed_default_knowledge

            await asyncio.to_thread(seed_default_knowledge)

    except Exception as e:
        logger.error(f"Failed to initialize RAG Pipeline: {e}")
        raise

    yield
    logger.info("Shutting down AI Worker...")


app = FastAPI(title="MentorIA AI Worker", lifespan=lifespan)


@app.post("/internal/generate", response_model=WorkerGenerateResponse)
async def generate_response(request: WorkerGenerateRequest):
    """
    Generate an answer using the RAG Pipeline.
    Protected by a Semaphore to prevent 429 Too Many Requests and memory exhaustion.
    """
    logger.info(
        f"Received generation request for chat_type {request.chat_type_id}. Waiting for semaphore..."
    )

    # Wait for the semaphore to be available (max 3 concurrent)
    async with semaphore:
        logger.info("Semaphore acquired. Processing RAG pipeline...")
        try:
            pipeline = RAGPipeline()
            # Run the synchronous RAG pipeline in a thread to not block other worker endpoints
            result = await asyncio.to_thread(
                pipeline.run,
                chat_type_id=request.chat_type_id,
                query=request.query,
                chat_history=request.chat_history,
                k_retrieval=request.k_retrieval,
                top_k=request.top_k,
                threshold=request.threshold,
                llm_model=request.llm_model,
                llm_provider=request.llm_provider,
            )
            return WorkerGenerateResponse(
                answer=result["answer"], chunks=result["chunks"]
            )
        except Exception as e:
            logger.error(f"Error during RAG generation: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@app.post("/internal/generate_stream")
async def generate_stream_response(request: WorkerGenerateRequest):
    """
    Generate a streaming answer using the RAG Pipeline.
    Protected by a Semaphore to prevent 429 Too Many Requests and memory exhaustion.
    """
    logger.info(
        f"Received stream generation request for chat_type {request.chat_type_id}. Waiting for semaphore..."
    )

    # Fast check before acquiring semaphore (though technically stream response generation happens in a thread)
    async def stream_generator() -> AsyncGenerator[str, None]:
        async with semaphore:
            logger.info("Semaphore acquired for stream. Processing RAG pipeline...")
            try:
                pipeline = RAGPipeline()

                # The pipeline.run_stream is a sync generator, so we must run it in a thread.
                # However, yielding from a thread is tricky. We'll use a thread with a queue or
                # run it via a simple async wrapper around the sync generator.

                # To properly handle sync generators asynchronously:
                def run_sync_stream():
                    return pipeline.run_stream(
                        chat_type_id=request.chat_type_id,
                        query=request.query,
                        chat_history=request.chat_history,
                        k_retrieval=request.k_retrieval,
                        top_k=request.top_k,
                        threshold=request.threshold,
                        llm_model=request.llm_model,
                        llm_provider=request.llm_provider,
                    )

                # Create the generator in a thread
                sync_gen = await asyncio.to_thread(run_sync_stream)

                # Consume it by running `next()` in a thread with a sentinel value
                while True:
                    # Provide None as default to avoid StopIteration being raised inside the thread future
                    chunk = await asyncio.to_thread(next, sync_gen, None)
                    if chunk is None:
                        break
                    yield f"data: {json.dumps(chunk)}\n\n"

            except Exception as e:
                logger.error(f"Error during RAG stream generation: {e}")
                error_event = {"type": "error", "content": f"Erro interno: {str(e)}"}
                yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(stream_generator(), media_type="text/event-stream")


import os
import tempfile

from fastapi import File, Form, UploadFile

from src.ai.stt_loader import get_stt_loader


@app.post("/internal/transcribe")
async def transcribe_audio_internal(
    audio: UploadFile = File(...), language: str | None = Form(None)
):
    """
    Internal endpoint to transcribe audio using the STT model.
    Protected by a Semaphore to prevent API blocking.
    """
    logger.info("Received audio transcription request. Waiting for semaphore...")

    # Wait for the semaphore to be available (max 3 concurrent)
    async with semaphore:
        logger.info(
            f"Semaphore acquired. Processing audio transcription for {audio.filename}..."
        )

        file_ext = (
            os.path.splitext(audio.filename)[1].lower() if audio.filename else ".webm"
        )
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=file_ext
            ) as temp_file:
                temp_path = temp_file.name
                content = await audio.read()
                temp_file.write(content)
                temp_file.flush()

            def run_stt_sync():
                stt_loader = get_stt_loader()
                provider = stt_loader.get_provider()
                return provider.transcribe(temp_path, language=language, beam_size=5)

            # Run the synchronous STT model in a thread
            result = await asyncio.to_thread(run_stt_sync)

            return {
                "text": result["text"],
                "detected_language": result["detected_language"],
                "language_probability": result["language_probability"],
            }
        except Exception as e:
            logger.error(f"Error during STT processing in worker: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    logger.warning(f"Failed to clean up temp file {temp_path}: {e}")


from fastapi import BackgroundTasks

from src.services.background import process_ingestion_job


def run_ingestion_worker(
    job_id: str,
    chat_type_id: str,
    temp_path: str,
    filename: str,
    question_col: str,
    answer_col: str,
):
    logger.info(f"Worker starting background ingestion for job {job_id}")
    try:
        with open(temp_path, "rb") as f:
            file_content = f.read()

        from src.api.routes.upload import get_ingestion_service

        ingestion_service = get_ingestion_service()

        # We need a new db session for the background thread
        db = SessionLocal()
        try:
            process_ingestion_job(
                job_id=UUID(job_id),
                chat_type_id=UUID(chat_type_id),
                file_content=file_content,
                filename=filename,
                question_col=question_col,
                answer_col=answer_col,
                ingestion_service=ingestion_service,
                db=db,
            )
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed worker background ingestion: {e}")
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


@app.post("/internal/ingest")
async def ingest_spreadsheet_internal(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    job_id: str = Form(...),
    chat_type_id: str = Form(...),
    question_col: str = Form("question"),
    answer_col: str = Form("answer"),
):
    """
    Internal endpoint to process spreadsheet ingestion using the Worker's CPU.
    Saves file to disk and passes it to a background task.
    """
    logger.info(f"Received ingestion request for job {job_id}, chat {chat_type_id}")

    file_ext = os.path.splitext(file.filename)[1].lower() if file.filename else ".xlsx"
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
        temp_path = temp_file.name
        content = await file.read()
        temp_file.write(content)
        temp_file.flush()

    background_tasks.add_task(
        run_ingestion_worker,
        job_id=job_id,
        chat_type_id=chat_type_id,
        temp_path=temp_path,
        filename=file.filename or "upload.xlsx",
        question_col=question_col,
        answer_col=answer_col,
    )

    return {"status": "accepted", "job_id": job_id}
