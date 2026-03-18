"""
Model loader for HuggingFace models with quantization support.
Adapted from SoulsborneRAG for multi-tenant RAG chat system.
"""

import os
import torch
from transformers import (
    AutoModel, 
    AutoTokenizer, 
    AutoModelForSequenceClassification,
    AutoModelForCausalLM,
    BitsAndBytesConfig
)
from typing import Tuple, Optional, Literal
from config.logger import logger
from config.settings import settings


class ModelLoader:
    """
    Utility for loading HuggingFace models with device management and quantization.
    """
    
    def __init__(self):
        """Initialize model loader with device detection."""
        self.cache_dir = os.path.join(settings.BASE_DIR, ".cache", "models")
        self.token = getattr(settings, "HUGGINGFACE_TOKEN", None)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        os.makedirs(self.cache_dir, exist_ok=True)
        logger.info(f"ModelLoader initialized. Device: {self.device}")
    
    def _get_quantization_config(
        self, 
        quantization: Optional[Literal["4bit", "8bit"]] = None
    ) -> Optional[BitsAndBytesConfig]:
        """
        Create quantization config for memory optimization.
        
        Args:
            quantization: "4bit", "8bit", or None
            
        Returns:
            BitsAndBytesConfig or None
        """
        if quantization == "4bit":
            return BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True
            )
        elif quantization == "8bit":
            return BitsAndBytesConfig(load_in_8bit=True)
        return None
    
    def load_embedding(
        self, 
        model_id: str,
        trust_remote_code: bool = True
    ) -> Tuple[AutoModel, AutoTokenizer]:
        """
        Load an embedding model from HuggingFace.
        
        Args:
            model_id: HuggingFace model identifier
            trust_remote_code: Whether to trust remote code
            
        Returns:
            Tuple of (model, tokenizer)
        """
        try:
            logger.info(f"Loading embedding model: {model_id}")
            
            tokenizer = AutoTokenizer.from_pretrained(
                model_id,
                cache_dir=self.cache_dir,
                token=self.token,
                trust_remote_code=trust_remote_code
            )
            
            model = AutoModel.from_pretrained(
                model_id,
                cache_dir=self.cache_dir,
                token=self.token,
                trust_remote_code=trust_remote_code,
                dtype=torch.float16 if self.device == "cuda" else torch.float32
            ).to(self.device)
            
            model.eval()
            
            logger.info(f"Successfully loaded embedding model: {model_id}")
            return model, tokenizer
            
        except Exception as e:
            logger.error(f"Failed to load embedding model {model_id}: {e}")
            raise
    
    def load_reranker(
        self,
        model_id: str,
        trust_remote_code: bool = True
    ) -> Tuple[AutoModelForSequenceClassification, AutoTokenizer]:
        """
        Load a cross-encoder reranker model.
        
        Args:
            model_id: HuggingFace model identifier
            trust_remote_code: Whether to trust remote code
            
        Returns:
            Tuple of (model, tokenizer)
        """
        try:
            logger.info(f"Loading reranker model: {model_id}")
            
            tokenizer = AutoTokenizer.from_pretrained(
                model_id,
                cache_dir=self.cache_dir,
                token=self.token,
                trust_remote_code=trust_remote_code
            )
            
            model = AutoModelForSequenceClassification.from_pretrained(
                model_id,
                cache_dir=self.cache_dir,
                token=self.token,
                trust_remote_code=trust_remote_code,
                dtype=torch.float16 if self.device == "cuda" else torch.float32
            ).to(self.device)
            
            model.eval()
            
            logger.info(f"Successfully loaded reranker model: {model_id}")
            return model, tokenizer
            
        except Exception as e:
            logger.error(f"Failed to load reranker model {model_id}: {e}")
            raise
    
    def load_llm(
        self,
        model_id: str,
        quantization: Optional[Literal["4bit", "8bit"]] = None
    ) -> Tuple[AutoModelForCausalLM, AutoTokenizer]:
        """
        Load a causal language model.
        
        Args:
            model_id: HuggingFace model identifier
            quantization: Quantization level
            
        Returns:
            Tuple of (model, tokenizer)
        """
        try:
            logger.info(f"Loading LLM: {model_id} with quantization: {quantization}")
            
            quant_config = self._get_quantization_config(quantization) if self.device == "cuda" else None
            
            tokenizer = AutoTokenizer.from_pretrained(
                model_id,
                cache_dir=self.cache_dir,
                token=self.token,
                trust_remote_code=True
            )
            
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            
            model = AutoModelForCausalLM.from_pretrained(
                model_id,
                cache_dir=self.cache_dir,
                token=self.token,
                quantization_config=quant_config,
                device_map="auto" if quantization else self.device,
                trust_remote_code=True,
                dtype=torch.float16 if self.device == "cuda" else torch.float32
            )
            
            logger.info(f"Successfully loaded LLM: {model_id}")
            return model, tokenizer
            
        except Exception as e:
            logger.error(f"Failed to load LLM {model_id}: {e}")
            raise
    
    def unload_memory(self):
        """Clear GPU/CPU memory."""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            logger.info("Cleared CUDA cache")
