# Chatbot Server API (LangChain-powered)

A FastAPI-based REST API server for the MongoDB chatbot, refactored to use LangChain Tools + Agent for tool-augmented reasoning over your MongoDB product database.

## Backend Structure

```
mongodb_mcp/
├── app.py                    # FastAPI app (endpoints)
├── mcp_server.py             # FastMCP server
├── backend/                  # Backend package (LangChain + service)
│   ├── __init__.py
│   ├── agent.py              # Builds AgentExecutor from LLM, tools, and prompt
│   ├── tooling.py            # Builds StructuredTool definitions from service schemas
│   ├── prompt.py             # System instructions for the agent
│   └── chatbot_service.py    # MongoDBChatbotService (business logic + tools)
├── frontend/                 # Static UI (optional)
│   ├── index.html
│   ├── script.js
│   └── style.css
├── frontend_server.py        # Simple static file server (port 4000)
├── run_servers.py            # Convenience runner for both servers
└── requirements.txt
```

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

4. Run the servers:
```bash
py app.py              # start FastAPI backend (port 8000)
python frontend_server.py  # start static frontend (port 4000)
```

Or run both via the helper script:

```bash
py run_servers.py
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
Under the hood, the server uses a LangChain tools agent backed by `gpt-3.5-turbo` and a set of structured tools that query MongoDB (product search, pricing rankings, discount rankings, user lookup, order history, chart data, etc.).

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
const response = await fetch('http://localhost:8000/chat', {
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

## Notes
- Model: configurable via `OPENAI_API_KEY`; default model is `gpt-3.5-turbo` in code.
- Tools: constructed dynamically from service function schemas and exposed to the agent as LangChain `StructuredTool`s.
- Chart output: when `get_product_prices_for_chart` is invoked, the agent returns raw JSON the frontend renders into a chart.