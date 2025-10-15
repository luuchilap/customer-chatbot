# MongoDB Product Chatbot - Technical Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Technology Stack](#technology-stack)
4. [API Documentation](#api-documentation)
5. [Database Schema](#database-schema)
6. [AI Agent Implementation](#ai-agent-implementation)
7. [Deployment Guide](#deployment-guide)
8. [Development Setup](#development-setup)
9. [Security Considerations](#security-considerations)
10. [Performance & Monitoring](#performance--monitoring)
11. [Troubleshooting](#troubleshooting)

## System Overview

The MongoDB Product Chatbot is an AI-powered customer service assistant designed for e-commerce platforms. It combines natural language processing with structured database queries to provide intelligent product recommendations, pricing information, and policy guidance.

### Key Features
- **Intelligent Product Search**: Semantic search across product catalogs
- **Price Analysis**: Ranking, comparison, and budget-based filtering
- **Order Management**: User lookup and purchase history
- **Policy Q&A**: RAG-based document retrieval for policy questions
- **Session Management**: Persistent conversation context
- **Real-time Chat**: WebSocket-like experience via REST API

## Architecture

### High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   FastAPI       │    │   MongoDB       │
│   (Port 4000)   │◄──►│   (Port 8000)   │◄──►│   Atlas         │
│   HTML/CSS/JS   │    │   LangChain     │    │   Cloud DB      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   OpenAI API    │
                       │   GPT-3.5-turbo │
                       └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   FAISS Vector  │
                       │   Store (RAG)   │
                       └─────────────────┘
```

### Component Details

#### Frontend Layer
- **Technology**: Vanilla HTML/CSS/JavaScript
- **Purpose**: User interface for chat interactions
- **Features**: Real-time messaging, session management, status indicators
- **Deployment**: Static files served via Nginx

#### API Layer
- **Framework**: FastAPI with async support
- **AI Integration**: LangChain for agent orchestration
- **Tool System**: Structured tools for database operations
- **Memory**: ConversationBufferWindowMemory for context retention

#### Data Layer
- **Primary Database**: MongoDB Atlas (cloud-hosted)
- **Vector Store**: FAISS for document embeddings
- **Collections**: products, users, orders, customer_inquiries

## Technology Stack

### Backend Technologies
```python
# Core Framework
fastapi>=0.115.0          # Web framework
uvicorn[standard]>=0.37.0 # ASGI server

# AI & ML
langchain>=0.2.0          # Agent framework
langchain-openai>=0.2.0  # OpenAI integration
langchain-community>=0.2.0 # Community tools
openai>=1.0.0            # OpenAI client

# Database
pymongo==4.6.0           # MongoDB driver
faiss-cpu>=1.8.0         # Vector similarity search

# Utilities
pydantic>=2.6.0          # Data validation
python-dotenv>=1.0.0     # Environment management
pypdf>=4.0.0             # PDF processing
```

### Frontend Technologies
- **HTML5**: Semantic markup
- **CSS3**: Modern styling with Flexbox/Grid
- **JavaScript ES6+**: Async/await, fetch API
- **Fonts**: Google Fonts (Inter)

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Web Server**: Nginx (frontend)
- **Process Manager**: Uvicorn (backend)
- **Cloud Database**: MongoDB Atlas

## API Documentation

### Base URL
```
http://localhost:8000
```

### Authentication
No authentication required for demo purposes. In production, implement JWT or API key authentication.

### Endpoints

#### Health Check
```http
GET /health
```
**Response:**
```json
{
  "status": "healthy",
  "collections": ["products", "users", "orders"],
  "product_count": {"total_products": 1250}
}
```

#### Chat Interface
```http
POST /chat
Content-Type: application/json

{
  "message": "Show me all iPhones",
  "customer_name": "John",
  "session_id": "user123",
  "include_reasoning": false,
  "use_chain": false
}
```

**Parameters:**
- `message` (string, required): User's question or request
- `customer_name` (string, optional): Customer identifier
- `session_id` (string, optional): Session identifier for context
- `include_reasoning` (boolean, optional): Include tool execution trace
- `use_chain` (boolean, optional): Use sequential pipeline vs agent

**Response:**
```json
{
  "response": "Here are the iPhones I found:\n\n**iPhone 15 Pro** - $999\n**iPhone 15** - $799\n...",
  "reasoning": [
    {
      "tool": "search_products_by_name",
      "input": {"name": "iPhone", "limit": 10},
      "observation": [{"_id": "...", "name": "iPhone 15 Pro", "price": 999}]
    }
  ],
  "session_id": "user123",
  "customer_name": "John"
}
```

#### Product Search
```http
GET /products/search?q=iphone&limit=10
```

#### Product Details
```http
GET /products/{product_id}
```

#### Reset Conversation
```http
POST /chat/reset
Content-Type: application/json

{
  "session_id": "user123"
}
```

#### Chat History
```http
GET /chat/history/{session_id}
GET /chat/history/all
```

## Database Schema

### Collections

#### Products Collection
```javascript
{
  "_id": ObjectId("..."),
  "name": "iPhone 15 Pro",
  "title": "Apple iPhone 15 Pro 128GB",
  "price": 999.99,
  "discountPercentage": 5.0,
  "category": "Electronics",
  "description": "Latest iPhone with A17 Pro chip",
  "thumbnail": "https://example.com/image.jpg",
  "inStock": true,
  "createdAt": ISODate("2024-01-15T10:30:00Z")
}
```

#### Users Collection
```javascript
{
  "_id": ObjectId("..."),
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "+1234567890",
  "address": {
    "street": "123 Main St",
    "city": "New York",
    "state": "NY",
    "zipCode": "10001"
  },
  "createdAt": ISODate("2024-01-10T08:00:00Z")
}
```

#### Orders Collection
```javascript
{
  "_id": ObjectId("..."),
  "userId": ObjectId("..."),
  "products": [
    {
      "productId": ObjectId("..."),
      "quantity": 2,
      "price": 999.99
    }
  ],
  "totalAmount": 1999.98,
  "status": "completed",
  "orderDate": ISODate("2024-01-20T14:30:00Z")
}
```

#### Customer Inquiries Collection
```javascript
{
  "_id": ObjectId("..."),
  "customer_name": "John",
  "inquiry": "Show me laptops under $500",
  "response": "Here are some laptops under $500...",
  "session_id": "user123",
  "timestamp": ISODate("2024-01-20T15:45:00Z")
}
```

## AI Agent Implementation

### Tool Categories

#### 1. Product & Category Tools
- `get_product_count()`: Total product count
- `search_products_by_name()`: Name-based search
- `get_product_by_id()`: Detailed product info
- `get_product_categories()`: Available categories

#### 2. Pricing & Comparison Tools
- `get_top_k_products_by_price()`: Price ranking
- `find_product_by_price_rank()`: Specific rank lookup
- `find_product_by_discount_rank()`: Discount ranking
- `find_products_by_price_comparison()`: Price comparison
- `calculate_order_total()`: Order cost calculation
- `get_product_prices_for_chart()`: Chart data generation
- `find_products_within_budget()`: Budget filtering

#### 3. User & Order Management Tools
- `get_user_by_name()`: User lookup
- `get_user_order_history()`: Purchase history

#### 4. RAG Tools
- `answer_policy_pdf()`: Policy document Q&A

### Agent Architecture

#### LangChain Agent (Default)
```python
# Agent creation with memory
agent = create_openai_tools_agent(llm, tools, prompt)
executor = AgentExecutor(
    agent=agent,
    tools=tools,
    memory=ConversationBufferWindowMemory(k=6),
    return_intermediate_steps=True
)
```

#### Sequential Pipeline (Alternative)
```python
# Three-step pipeline
1. Intent Router: Classify query → tool selection
2. Tool Executor: Execute selected tool
3. Summarizer: Format response + suggest follow-up
```

### Prompt Engineering

#### System Instructions
```python
SYSTEM_PROMPT = """
You are a helpful customer service chatbot with access to a product database.
CRITICAL INSTRUCTIONS: 
1. Answer questions about products, categories, pricing, discounts, user accounts, order history, and policy PDF
2. When listing products, ALWAYS include name/title and their _id
3. If a tool returns multiple products, iterate them ALL and show name/title and price
4. For totals, you MUST use calculate_order_total and show per-item breakdown
5. For policy questions, FIRST call answer_policy_pdf with the user's question
...
"""
```

## Deployment Guide

### Docker Deployment

#### Prerequisites
- Docker & Docker Compose installed
- MongoDB Atlas cluster
- OpenAI API key

#### Environment Setup
```bash
# Create .env file
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/database
OPENAI_API_KEY=sk-proj-...
PORT=8000
DEBUG=false
```

#### Docker Commands
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild
docker-compose up --build
```

#### Service Configuration
```yaml
# docker-compose.yml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MONGO_URI=${MONGO_URI}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      
  frontend:
    image: nginx:alpine
    ports:
      - "4000:80"
    volumes:
      - ./frontend:/usr/share/nginx/html:ro
```

### Local Development

#### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export MONGO_URI="your_mongo_uri"
export OPENAI_API_KEY="your_api_key"

# Run backend
python app.py

# Run frontend (separate terminal)
python frontend_server.py
```

#### Development Features
- Hot reload enabled
- Debug logging
- CORS enabled for frontend
- Volume mounting for live code changes

## Security Considerations

### Current Security Measures
- **Input Validation**: Pydantic models for request validation
- **SQL Injection Prevention**: MongoDB driver handles sanitization
- **CORS Configuration**: Restricted origins in production
- **Environment Variables**: Sensitive data in .env files

### Production Security Checklist
- [ ] Implement JWT authentication
- [ ] Add rate limiting (Redis + FastAPI-limiter)
- [ ] Enable HTTPS with SSL certificates
- [ ] Implement API key authentication
- [ ] Add request logging and monitoring
- [ ] Use secrets management (AWS Secrets Manager, etc.)
- [ ] Configure firewall rules
- [ ] Regular security updates
- [ ] Input sanitization for user queries
- [ ] MongoDB authentication enabled

### Security Headers
```python
# Add to FastAPI app
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["yourdomain.com", "*.yourdomain.com"]
)
```

## Performance & Monitoring

### Performance Optimizations

#### Database
- **Indexing**: Ensure proper indexes on frequently queried fields
- **Connection Pooling**: MongoDB connection reuse
- **Query Optimization**: Use aggregation pipelines efficiently

#### Caching
- **Vector Store**: FAISS index cached on disk
- **Session Memory**: ConversationBufferWindowMemory with limited window
- **Tool Results**: Consider Redis caching for expensive operations

#### API Performance
- **Async Operations**: FastAPI async/await support
- **Response Compression**: Gzip compression enabled
- **Connection Limits**: Configure appropriate timeouts

### Monitoring Setup

#### Health Checks
```python
@app.get('/health')
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": "1.0.0",
        "database": "connected",
        "openai": "available"
    }
```

#### Logging Configuration
```python
import logging
from pythonjsonlogger import jsonlogger

# Structured logging
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger = logging.getLogger()
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)
```

#### Metrics Collection
- **Response Times**: Track API endpoint performance
- **Error Rates**: Monitor 4xx/5xx responses
- **Database Queries**: Track query execution times
- **Memory Usage**: Monitor agent memory consumption
- **Tool Usage**: Track which tools are used most frequently

## Troubleshooting

### Common Issues

#### 1. MongoDB Connection Issues
```bash
# Check connection string
echo $MONGO_URI

# Test connection
python -c "from pymongo import MongoClient; MongoClient('$MONGO_URI').admin.command('ping')"

# Check network connectivity
telnet cluster0.432k5df.mongodb.net 27017
```

#### 2. OpenAI API Issues
```bash
# Verify API key
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models

# Check rate limits
# Monitor usage in OpenAI dashboard
```

#### 3. Docker Issues
```bash
# Check container logs
docker-compose logs api

# Restart specific service
docker-compose restart api

# Clean rebuild
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

#### 4. Frontend Issues
```bash
# Check if frontend server is running
curl http://localhost:4000

# Check browser console for errors
# Verify API endpoint accessibility
curl http://localhost:8000/health
```

### Debug Mode
```bash
# Enable debug logging
export DEBUG=true
python app.py

# Or in Docker
docker-compose -f docker-compose.yml -f docker-compose.override.yml up
```

### Performance Debugging
```python
# Add timing decorator
import time
from functools import wraps

def timing_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        logger.info(f"{func.__name__} took {end - start:.2f} seconds")
        return result
    return wrapper

# Apply to critical functions
@timing_decorator
def search_products_by_name(self, name: str, limit: int = 10):
    # ... implementation
```

### Error Handling
```python
# Comprehensive error handling
try:
    result = agent_executor.invoke({"input": user_message})
except Exception as e:
    logger.error(f"Agent execution failed: {str(e)}")
    return {
        "error": "I encountered an issue processing your request. Please try again.",
        "details": str(e) if DEBUG else None
    }
```

---

## Conclusion

This MongoDB Product Chatbot represents a modern approach to AI-powered customer service, combining structured data access with natural language understanding. The modular architecture allows for easy extension and maintenance, while the comprehensive tool system provides rich functionality for e-commerce interactions.

For questions or contributions, please refer to the project repository or contact the development team.
