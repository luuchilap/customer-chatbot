from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import logging
from chatbot_service import MongoDBChatbotService

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize chatbot service
chatbot_service = None

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

@app.route('/health', methods=['GET'])
def health_check():
    try:
        service = get_chatbot_service()
        return jsonify({
            "status": "healthy",
            "collections": service.get_available_collections(),
            "product_count": service.get_product_count()
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({"error": "Missing 'message' in request body"}), 400
        
        message = data['message'].strip()
        if not message:
            return jsonify({"error": "Message cannot be empty"}), 400
        
        customer_name = data.get('customer_name', 'Guest')
        session_id = data.get('session_id', 'default')
        
        service = get_chatbot_service()
        response = service.chat(message, customer_name, session_id)
        
        return jsonify({
            "response": response,
            "session_id": session_id,
            "customer_name": customer_name
        }), 200
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/chat/reset', methods=['POST'])
def reset_conversation():
    try:
        data = request.get_json() or {}
        session_id = data.get('session_id', 'default')
        
        service = get_chatbot_service()
        service.reset_conversation(session_id)
        
        return jsonify({"message": "Conversation reset successfully"}), 200
        
    except Exception as e:
        logger.error(f"Reset error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/products/search', methods=['GET'])
def search_products():
    try:
        query = request.args.get('q', '').strip()
        limit = int(request.args.get('limit', 10))
        
        if not query:
            return jsonify({"error": "Missing search query parameter 'q'"}), 400
        
        if limit > 50:
            limit = 50
            
        service = get_chatbot_service()
        results = service.search_products_by_name(query, limit)
        
        return jsonify({
            "query": query,
            "results": results,
            "count": len(results)
        }), 200
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/products/<product_id>', methods=['GET'])
def get_product(product_id):
    try:
        service = get_chatbot_service()
        result = service.get_product_by_id(product_id)
        
        if "error" in result:
            return jsonify(result), 404
            
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Get product error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    app.run(host='0.0.0.0', port=port, debug=debug)