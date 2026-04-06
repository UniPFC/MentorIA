"""
Seeder service to initialize default data and knowledge bases.
"""
import os
import logging
from sqlalchemy.orm import Session
from shared.database.session import SessionLocal
from shared.database.models.user import User
from shared.database.models.chat_type import ChatType
from shared.database.models.knowledge_chunk import KnowledgeChunk
from src.services.ingestion import ChunkIngestionService
from shared.qdrant.client import QdrantManager
from src.ai.loader import ModelLoader
from src.ai.provider.embedding import HFEmbeddingProvider
from src.ai.embedding import EmbeddingEngine
from config.settings import settings
from src.services.auth import auth_service

logger = logging.getLogger(__name__)

DATA_DIR = settings.DATA_DIR

def seed_default_knowledge():
    """
    Scans the data directory and ingests all found spreadsheets as public ChatTypes.
    The ChatType name is derived from the filename (e.g., 'Financial_Report.xlsx' -> 'Financial Report').
    """
    if not os.path.exists(DATA_DIR):
        logger.warning(f"Data directory not found at {DATA_DIR}. Skipping seeding.")
        return

    db = SessionLocal()
    try:
        logger.info(f"Scanning {DATA_DIR} for knowledge base initialization...")
        
        # 1. Create/Get System User 'MentorIA' (Owner of default chats)
        system_email = settings.SYSTEM_USER_EMAIL
        system_username = "MentorIA"
        
        # Try to find by email or username
        system_user = db.query(User).filter(
            (User.email == system_email) | (User.username == system_username)
        ).first()
        
        if not system_user:
            logger.info("Creating MentorIA system user...")
            system_user = User(
                email=system_email,
                password_hash=auth_service.get_password_hash(settings.SYSTEM_USER_PASSWORD),
                username=system_username,
                is_active=True
            )
            db.add(system_user)
            db.commit()
            db.refresh(system_user)
            logger.info(f"MentorIA system user created with ID: {system_user.id}")
        else:
            # Ensure username is 'MentorIA' if found by email
            if system_user.username != system_username:
                logger.info(f"Updating system user username to '{system_username}'...")
                system_user.username = system_username
                db.commit()
                db.refresh(system_user)
            
        # Services initialization (lazy loading)
        models_loaded = False
        ingestion_service = None
        qdrant_manager = None
        
        # 2. Iterate through all files in data directory
        for filename in os.listdir(DATA_DIR):
            if not filename.endswith(('.xlsx', '.xls', '.csv')):
                continue
                
            file_path = os.path.join(DATA_DIR, filename)
            
            # Derive name and description from filename
            # Format: "Title --- Description.xlsx"
            base_name = os.path.splitext(filename)[0]
            
            if "---" in base_name:
                parts = base_name.split("---")
                chat_title = parts[0].strip().replace("_", " ")
                chat_desc = parts[1].strip().replace("_", " ")
            else:
                # Fallback: Convert "my_file_name" to "My File Name"
                chat_title = base_name.replace("_", " ").replace("-", " ").title()
                chat_desc = f"Base de conhecimento gerada automaticamente a partir do arquivo {filename}"
            
            # Unique collection name (must be safe for Qdrant/URLs)
            safe_name = base_name.lower().replace(" ", "_").replace("-", "_")
            safe_name = "".join(c for c in safe_name if c.isalnum() or c == "_")
            collection_name = f"chat_type_auto_{safe_name}"
            
            # Check if ChatType already exists by name
            chat_type = db.query(ChatType).filter(ChatType.name == chat_title).first()
            
            if not chat_type:
                logger.info(f"Creating ChatType: {chat_title}")
                
                chat_type = ChatType(
                    name=chat_title,
                    description=chat_desc,
                    is_public=True,  # Available to all users
                    owner_id=system_user.id,
                    collection_name=collection_name
                )
                db.add(chat_type)
                db.commit()
                db.refresh(chat_type)
                
            # Ensure Qdrant collection exists and has correct dimension
                if not qdrant_manager:
                    qdrant_manager = QdrantManager()
                qdrant_manager.create_collection(chat_type.id)
            
            # 3. Check data and Ingest if needed
            chunk_count = db.query(KnowledgeChunk).filter(KnowledgeChunk.chat_type_id == chat_type.id).count()
            
            if chunk_count == 0:
                logger.info(f"Ingesting data for '{chat_title}' from {filename}...")
                
                # Load models only if we actually need to ingest something
                if not models_loaded:
                    logger.info("Loading embedding models for seeding...")
                    loader = ModelLoader()
                    emb_model, emb_tokenizer = loader.load_embedding(settings.EMBEDDING_MODEL_ID)
                    emb_provider = HFEmbeddingProvider(emb_model, emb_tokenizer)
                    embedding_engine = EmbeddingEngine(emb_provider)
                    
                    if not qdrant_manager:
                        qdrant_manager = QdrantManager()
                    
                    ingestion_service = ChunkIngestionService(embedding_engine, qdrant_manager)
                    models_loaded = True
                
                try:
                    with open(file_path, "rb") as f:
                        file_content = f.read()
                        
                    ingestion_service.ingest_from_file(
                        chat_type_id=chat_type.id,
                        file_content=file_content,
                        filename=filename,
                        db_session=db
                    )
                    logger.info(f"Ingestion for '{chat_title}' completed successfully.")
                except Exception as e:
                    logger.error(f"Failed to ingest {filename}: {e}")
            else:
                logger.info(f"ChatType '{chat_title}' already has data ({chunk_count} chunks). Skipping ingestion.")
                
    except Exception as e:
        logger.error(f"Seeding process failed: {e}")
        db.rollback()
    finally:
        db.close()
