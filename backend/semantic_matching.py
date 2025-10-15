"""
Semantic matching utilities for categories and order terms using OpenAI embeddings.
"""
import os
import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


class SemanticMatcher:
    """Handles semantic matching for categories and order terms using OpenAI embeddings."""
    
    def __init__(self, openai_api_key: str):
        self.openai_api_key = openai_api_key
        os.environ.setdefault("OPENAI_API_KEY", openai_api_key)
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import math
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(a * a for a in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def find_semantic_category_match(self, user_category: str, available_categories: List[str], threshold: float = 0.7) -> Optional[str]:
        """Find the most semantically similar category using OpenAI embeddings."""
        try:
            from openai import OpenAI
            
            if not available_categories:
                return None
            
            # If exact match exists, return it
            user_category_lower = user_category.lower().strip()
            for cat in available_categories:
                if cat.lower() == user_category_lower:
                    return cat
            
            # Use OpenAI embeddings for semantic similarity
            client = OpenAI(api_key=self.openai_api_key)
            
            # Create embeddings for user input and all categories
            user_embedding_response = client.embeddings.create(
                model="text-embedding-3-small",
                input=user_category
            )
            user_embedding = user_embedding_response.data[0].embedding
            
            # Calculate similarities
            similarities = []
            for category in available_categories:
                cat_embedding_response = client.embeddings.create(
                    model="text-embedding-3-small",
                    input=category
                )
                cat_embedding = cat_embedding_response.data[0].embedding
                
                # Calculate cosine similarity
                similarity = self._cosine_similarity(user_embedding, cat_embedding)
                similarities.append((category, similarity))
            
            # Sort by similarity and return best match if above threshold
            similarities.sort(key=lambda x: x[1], reverse=True)
            best_match, best_score = similarities[0]
            
            if best_score >= threshold:
                logger.info(f"Semantic match: '{user_category}' -> '{best_match}' (score: {best_score:.3f})")
                return best_match
            else:
                logger.info(f"No semantic match found for '{user_category}' (best score: {best_score:.3f})")
                return None
                
        except Exception as e:
            logger.error(f"Error in semantic category matching: {e}")
            return None

    def find_semantic_order_match(self, user_order: str, order_type: str = "price") -> Optional[str]:
        """Find the most semantically similar order term using OpenAI embeddings."""
        try:
            from openai import OpenAI
            
            # Define order categories and their semantic meanings
            if order_type == "price":
                order_categories = {
                    "highest": ["highest", "most expensive", "expensive", "top", "maximum", "descending", "desc", "max", "most"],
                    "cheapest": ["cheapest", "lowest", "cheap", "minimum", "ascending", "asc", "min", "least", "least expensive"]
                }
            elif order_type == "discount":
                order_categories = {
                    "highest": ["highest", "most", "biggest", "maximum", "top", "descending", "desc", "max"],
                    "lowest": ["lowest", "least", "smallest", "minimum", "ascending", "asc", "min"]
                }
            elif order_type == "comparison":
                order_categories = {
                    "same": ["same", "equal", "equivalent", "similar", "matching"],
                    "lower": ["lower", "cheaper", "less expensive", "below", "under", "less than"],
                    "higher": ["higher", "more expensive", "above", "over", "more than", "greater"]
                }
            else:
                return None
            
            # If exact match exists, return it
            user_order_lower = user_order.lower().strip()
            for category, terms in order_categories.items():
                if user_order_lower in terms:
                    return category
            
            # Use OpenAI embeddings for semantic similarity
            client = OpenAI(api_key=self.openai_api_key)
            
            # Create embeddings for user input
            user_embedding_response = client.embeddings.create(
                model="text-embedding-3-small",
                input=user_order
            )
            user_embedding = user_embedding_response.data[0].embedding
            
            # Calculate similarities with each category
            similarities = []
            for category, terms in order_categories.items():
                # Create a combined embedding for all terms in the category
                combined_terms = " ".join(terms)
                cat_embedding_response = client.embeddings.create(
                    model="text-embedding-3-small",
                    input=combined_terms
                )
                cat_embedding = cat_embedding_response.data[0].embedding
                
                # Calculate cosine similarity
                similarity = self._cosine_similarity(user_embedding, cat_embedding)
                similarities.append((category, similarity))
            
            # Sort by similarity and return best match if above threshold
            similarities.sort(key=lambda x: x[1], reverse=True)
            best_match, best_score = similarities[0]
            
            if best_score >= 0.6:  # Lower threshold for order terms
                logger.info(f"Semantic order match: '{user_order}' -> '{best_match}' (score: {best_score:.3f})")
                return best_match
            else:
                logger.info(f"No semantic order match found for '{user_order}' (best score: {best_score:.3f})")
                return None
                
        except Exception as e:
            logger.error(f"Error in semantic order matching: {e}")
            return None

