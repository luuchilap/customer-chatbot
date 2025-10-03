#!/usr/bin/env python3
"""
Simple FastMCP server for MongoDB Product Chatbot
Exposes MongoDB product database functions as MCP tools for AI assistants
"""
import os
import logging
from typing import List, Dict, Any, Optional
from fastmcp import FastMCP
from dotenv import load_dotenv
from chatbot_service import MongoDBChatbotService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("MongoDB Product Chatbot 🛍️")

# Initialize MongoDB chatbot service
def get_chatbot_service():
    mongo_uri = os.environ.get("MONGO_URI")
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    
    if not mongo_uri or not openai_api_key:
        raise ValueError("Missing required environment variables: MONGO_URI and/or OPENAI_API_KEY")
    
    return MongoDBChatbotService(
        mongo_uri=mongo_uri,
        openai_api_key=openai_api_key
    )

# Global service instance
chatbot_service = None

def get_service():
    global chatbot_service
    if chatbot_service is None:
        chatbot_service = get_chatbot_service()
    return chatbot_service

@mcp.tool
def get_product_count() -> Dict[str, int]:
    """Get the total number of products in the database"""
    try:
        service = get_service()
        count = service.get_product_count()
        return {"total_products": count}
    except Exception as e:
        logger.error(f"Error getting product count: {str(e)}")
        return {"error": str(e)}

@mcp.tool
def search_products_by_name(name: str, limit: int = 10) -> List[Dict]:
    """Search for products by name using regex matching"""
    try:
        service = get_service()
        results = service.search_products_by_name(name, limit)
        return results
    except Exception as e:
        logger.error(f"Error searching products: {str(e)}")
        return [{"error": str(e)}]

@mcp.tool
def get_product_by_id(product_id: str) -> Dict:
    """Get detailed information about a specific product by its MongoDB ObjectId"""
    try:
        service = get_service()
        result = service.get_product_by_id(product_id)
        return result
    except Exception as e:
        logger.error(f"Error getting product by ID: {str(e)}")
        return {"error": str(e)}

@mcp.tool
def find_product_by_rank(rank: int, order: str, category: Optional[str] = None) -> Dict:
    """
    Find a product at a specific price rank
    
    Args:
        rank: The numerical rank to find (1-based)
        order: Either 'highest' or 'cheapest'
        category: Optional category to limit search within
    """
    try:
        service = get_service()
        result = service.find_product_by_rank(rank, order, category)
        return result
    except Exception as e:
        logger.error(f"Error finding product by rank: {str(e)}")
        return {"error": str(e)}

@mcp.tool
def find_products_by_price_comparison(
    comparison_type: str,
    reference_product_name: Optional[str] = None,
    reference_product_id: Optional[str] = None,
    limit: int = 5
) -> Dict:
    """
    Find products by price comparison to a reference product
    
    Args:
        comparison_type: Type of comparison ('same', 'lower', 'higher')
        reference_product_name: Name of reference product (optional)
        reference_product_id: ID of reference product (optional)
        limit: Maximum number of results to return
    """
    try:
        service = get_service()
        result = service.find_products_by_price_comparison(
            reference_product_name=reference_product_name,
            reference_product_id=reference_product_id,
            comparison_type=comparison_type,
            limit=limit
        )
        return result
    except Exception as e:
        logger.error(f"Error finding products by price comparison: {str(e)}")
        return {"error": str(e)}

@mcp.tool
def query_products(filters: Optional[Dict[str, Any]] = None, limit: int = 10) -> List[Dict]:
    """
    Query products from the database with optional MongoDB filters
    
    Args:
        filters: MongoDB query filters (optional)
        limit: Maximum number of results to return
    """
    try:
        service = get_service()
        results = service.query_products(filters, limit)
        return results
    except Exception as e:
        logger.error(f"Error querying products: {str(e)}")
        return [{"error": str(e)}]

@mcp.tool
def get_available_collections() -> List[str]:
    """Get list of available MongoDB collections"""
    try:
        service = get_service()
        collections = service.get_available_collections()
        return collections
    except Exception as e:
        logger.error(f"Error getting collections: {str(e)}")
        return [f"error: {str(e)}"]

@mcp.resource("mongodb://product_database_info")
def product_database_info() -> str:
    """Information about the product database structure and capabilities"""
    return """
    # MongoDB Product Database
    
    This MCP server provides access to a MongoDB product database with the following capabilities:
    
    ## Available Tools:
    - **get_product_count**: Get total number of products
    - **search_products_by_name**: Search products by name (regex)
    - **get_product_by_id**: Get product details by MongoDB ObjectId
    - **find_product_by_rank**: Find products by price ranking
    - **find_products_by_price_comparison**: Compare products by price
    - **query_products**: Advanced MongoDB queries with filters
    - **get_available_collections**: List database collections
    
    ## Database Schema:
    Products typically contain fields like:
    - `_id`: MongoDB ObjectId
    - `name` or `title`: Product name
    - `price`: Product price
    - Additional product-specific fields
    
    ## Usage Examples:
    1. Search for laptops: `search_products_by_name("laptop", 5)`
    2. Find cheapest product: `find_product_by_rank(1, "cheapest")`
    3. Get products cheaper than reference: `find_products_by_price_comparison("lower", reference_product_name="iPhone")`
    """

if __name__ == "__main__":
    # Run the MCP server
    mcp.run()