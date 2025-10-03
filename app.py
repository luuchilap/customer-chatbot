from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
import logging
from dotenv import load_dotenv
from chatbot_service import MongoDBChatbotService

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="MongoDB Chatbot API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize chatbot service
chatbot_service = None

# Pydantic models
class ChatRequest(BaseModel):
    message: str
    customer_name: Optional[str] = "Guest"
    session_id: Optional[str] = "default"

class ResetRequest(BaseModel):
    session_id: Optional[str] = "default"

def get_chatbot_service():
    global chatbot_service
    if chatbot_service is None:
        mongo_uri = os.environ.get("MONGO_URI")
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        
        if not mongo_uri or not openai_api_key:
            raise ValueError("Missing required environment variables: MONGO_URI and/or OPENAI_API_KEY")
        
        chatbot_service = MongoDBChatbotService(
            mongo_uri=mongo_uri,
            openai_api_key=openai_api_key
        )
    return chatbot_service

@app.get('/health')
def health_check():
    try:
        service = get_chatbot_service()
        return {
            "status": "healthy",
            "collections": service.get_available_collections(),
            "product_count": service.get_product_count()
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.post('/chat')
def chat(request: ChatRequest):
    try:
        message = request.message.strip()
        if not message:
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        service = get_chatbot_service()
        response = service.chat(message, request.customer_name, request.session_id)
        
        return {
            "response": response,
            "session_id": request.session_id,
            "customer_name": request.customer_name
        }
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post('/chat/reset')
def reset_conversation(request: ResetRequest):
    try:
        service = get_chatbot_service()
        service.reset_conversation(request.session_id)
        
        return {"message": "Conversation reset successfully"}
        
    except Exception as e:
        logger.error(f"Reset error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get('/products/search')
def search_products(q: str, limit: int = 10):
    try:
        query = q.strip()
        if not query:
            raise HTTPException(status_code=400, detail="Missing search query parameter 'q'")
        
        if limit > 50:
            limit = 50
            
        service = get_chatbot_service()
        results = service.search_products_by_name(query, limit)
        
        return {
            "query": query,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get('/products/{product_id}')
def get_product(product_id: str):
    try:
        service = get_chatbot_service()
        result = service.get_product_by_id(product_id)
        
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
            
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get product error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get('PORT', 8000))
    
    uvicorn.run(
        "app:app",
        host='0.0.0.0',
        port=port,
        reload=os.environ.get('DEBUG', 'False').lower() == 'true'
    )