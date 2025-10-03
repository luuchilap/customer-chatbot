# Chatbot Server API

A Flask-based REST API server for the MongoDB chatbot, separated from the UI for better architecture.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Copy environment variables:
```bash
cp .env.example .env
```

3. Edit `.env` with your credentials:
- `MONGO_URI`: Your MongoDB connection string
- `OPENAI_API_KEY`: Your OpenAI API key

4. Run the server:
```bash
python app.py
```

## API Endpoints

### Health Check
```
GET /health
```
Returns server status and database info.

### Chat
```
POST /chat
Content-Type: application/json

{
  "message": "Show me all iPhones",
  "customer_name": "John",
  "session_id": "user123"
}
```

### Reset Conversation
```
POST /chat/reset
Content-Type: application/json

{
  "session_id": "user123"
}
```

### Search Products
```
GET /products/search?q=iphone&limit=10
```

### Get Product by ID
```
GET /products/{product_id}
```

## Frontend Integration

The server includes CORS support and accepts JSON requests. You can build any frontend (React, Vue, plain HTML/JS) that communicates with these endpoints.

Example frontend code:
```javascript
// Chat with the bot
const response = await fetch('http://localhost:5000/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: 'Show me laptops under $500',
    customer_name: 'Alice',
    session_id: 'session123'
  })
});

const data = await response.json();
console.log(data.response);
```