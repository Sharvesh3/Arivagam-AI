"""
Embedding generation service using Google Gemini.
Includes batching, retry logic, and local fallback.
"""
from typing import List, Dict, Any, Optional
import google.generativeai as genai
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger
import numpy as np

from app.core.config import settings


class EmbeddingService:
    """
    Service for generating embeddings with Google Gemini API.
    Falls back to local model if API fails.
    """
    
    def __init__(self):
        if settings.gemini_api_key:
            genai.configure(api_key=settings.gemini_api_key)
        else:
            logger.warning("GEMINI_API_KEY is missing!")
            
        self.model_name = settings.gemini_embedding_model
        if not self.model_name.startswith("models/"):
            self.model_name = "models/" + self.model_name
            
        self.dimensions = settings.gemini_embedding_dimensions
        self.batch_size = 100
        
        logger.info(f"Embedding service initialized: Gemini {self.model_name} ({self.dimensions}D)")
    

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=10, max=60)
    )
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text using Gemini."""
        return await self._generate_embedding_gemini(text)
    
    async def _generate_embedding_gemini(self, text: str) -> List[float]:
        """Generate embedding using Google Generative AI API."""
        loop = asyncio.get_event_loop()
        
        # Run blocking call in executor
        def _get_embedding():
            result = genai.embed_content(
                model=self.model_name,
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']
            
        embedding = await loop.run_in_executor(None, _get_embedding)
        
        # Adjust dimensions if needed
        embedding = self._adjust_dimensions(embedding)
        
        logger.debug(f"Generated Gemini embedding for text (length: {len(text)})")
        return embedding
    
    async def _generate_embedding_local(self, text: str) -> List[float]:
        """Generate embedding using local model."""
        if self.local_model is None:
            self._init_local_model()
        
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None,
            lambda: self.local_model.encode(text, convert_to_numpy=True).tolist()
        )
        
        embedding = self._adjust_dimensions(embedding)
        logger.debug(f"Generated local embedding for text (length: {len(text)})")
        return embedding
    
    def _adjust_dimensions(self, embedding: List[float]) -> List[float]:
        """Adjust embedding dimensions to match expected size."""
        current_dim = len(embedding)
        target_dim = self.dimensions
        
        if current_dim == target_dim:
            return embedding
        elif current_dim < target_dim:
            return embedding + [0.0] * (target_dim - current_dim)
        else:
            return embedding[:target_dim]
    
    async def generate_embeddings_batch(
        self,
        texts: List[str],
        show_progress: bool = False
    ) -> List[List[float]]:
        """Generate embeddings for multiple texts using Gemini."""
        if not texts:
            return []
        return await self._generate_embeddings_batch_gemini(texts, show_progress)
    
    async def _generate_embeddings_batch_gemini(
        self,
        texts: List[str],
        show_progress: bool = False
    ) -> List[List[float]]:
        """Generate embeddings using Gemini API in batches."""
        all_embeddings = []
        total_batches = (len(texts) + self.batch_size - 1) // self.batch_size
        
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            
            if show_progress:
                logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} texts) [Gemini]")
            
            try:
                loop = asyncio.get_event_loop()
                
                # Run blocking call in executor
                def _get_batch_embeddings():
                    result = genai.embed_content(
                        model=self.model_name,
                        content=batch,
                        task_type="retrieval_document"
                    )
                    return result['embedding']
                
                result = await loop.run_in_executor(None, _get_batch_embeddings)
                
                # Extract embeddings
                batch_embeddings = [self._adjust_dimensions(emb) for emb in result]
                
                logger.info(f"✅ Batch {batch_num} completed: {len(batch_embeddings)} embeddings")
                all_embeddings.extend(batch_embeddings)
                
                # Optimized delay for Billing Account
                await asyncio.sleep(2.0)
                
            except asyncio.TimeoutError as e:
                logger.error(f"Timeout in batch {batch_num}: {str(e)}")
                logger.warning("Switching to local embeddings due to timeout")
                self.use_local_fallback = True
                return await self._generate_embeddings_batch_local(texts, show_progress)
                
            except Exception as e:
                logger.error(f"Error in batch {batch_num}: {str(e)}")
                error_str = str(e).lower()
                if any(err in error_str for err in ['quota', 'rate limit', 'authentication', '429', '401', '403']):
                    logger.warning(f"Gemini batch error, switching to local: {str(e)}")
                    self.use_local_fallback = True
                    return await self._generate_embeddings_batch_local(texts, show_progress)
                raise
        
        logger.info(f"✅ Generated {len(all_embeddings)} Gemini embeddings successfully")
        return all_embeddings
        

    
    def enhance_text_for_embedding(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Enhance text with contextual information for better embeddings."""
        enhanced_parts = []
        
        if context:
            if 'document_title' in context:
                enhanced_parts.append(f"Document: {context['document_title']}")
            if 'section' in context:
                enhanced_parts.append(f"Section: {context['section']}")
            if 'page' in context:
                enhanced_parts.append(f"Page: {context['page']}")
            if 'chunk_type' in context and context['chunk_type'] != 'text':
                enhanced_parts.append(f"Type: {context['chunk_type']}")
        
        if enhanced_parts:
            context_str = " | ".join(enhanced_parts)
            return f"{context_str}\n\n{text}"
        
        return text
    
    async def embed_chunks_with_context(
        self,
        chunks: List[Dict[str, Any]],
        document_title: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Generate embeddings for chunks with contextual enhancement."""
        enhanced_texts = []
        for chunk in chunks:
            context = {
                'document_title': document_title,
                'section': chunk.get('section_title'),
                'page': chunk.get('page_numbers', [None])[0],
                'chunk_type': chunk.get('chunk_type', 'text')
            }
            
            enhanced_text = self.enhance_text_for_embedding(chunk['content'], context)
            enhanced_texts.append(enhanced_text)
        
        logger.info(f"Generating embeddings for {len(chunks)} chunks")
        embeddings = await self.generate_embeddings_batch(enhanced_texts, show_progress=True)
        
        for chunk, embedding in zip(chunks, embeddings):
            chunk['embedding'] = embedding
        
        return chunks
    
    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        vec1_np = np.array(vec1)
        vec2_np = np.array(vec2)
        
        dot_product = np.dot(vec1_np, vec2_np)
        norm1 = np.linalg.norm(vec1_np)
        norm2 = np.linalg.norm(vec2_np)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    async def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a search query using Gemini."""
        enhanced_query = f"Query: {query}"
        
        try:
            loop = asyncio.get_event_loop()
            
            def _get_query_embedding():
                result = genai.embed_content(
                    model=self.model_name,
                    content=enhanced_query,
                    task_type="retrieval_query"
                )
                return result['embedding']
                
            embedding = await loop.run_in_executor(None, _get_query_embedding)
            return self._adjust_dimensions(embedding)
        except Exception as e:
            logger.error(f"Query embedding failed: {str(e)}")
            raise


# Global instance
embedding_service = EmbeddingService()

__all__ = ['EmbeddingService', 'embedding_service']