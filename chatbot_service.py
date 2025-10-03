import os
import json
try:
    from openai import OpenAI
    OPENAI_V1 = True
except ImportError:
    import openai
    OPENAI_V1 = False
from pymongo import MongoClient
from datetime import datetime
from typing import List, Dict, Any, Optional
from bson import ObjectId
from bson.json_util import dumps as bson_dumps
import logging

logger = logging.getLogger(__name__)


class MongoDBChatbotService:
    def __init__(self, mongo_uri: str, openai_api_key: str, database_name: str = "product-management"):
        self._initialize_mongodb(mongo_uri, database_name)
        self._initialize_openai(openai_api_key)
        # Conversations are no longer stored in memory
        # self.conversations = {}

    def _initialize_mongodb(self, mongo_uri: str, database_name: str):
        try:
            self.client = MongoClient(
                mongo_uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000
            )
            self.db = self.client[database_name]
            self.conversations_collection = self.db.conversations
            self.client.admin.command('ping')
            logger.info("MongoDB connection successful")
        except Exception as e:
            logger.error(f"MongoDB connection failed: {str(e)}")
            raise Exception(f"MongoDB connection failed: {str(e)}")

    def _initialize_openai(self, api_key: str):
        try:
            if OPENAI_V1:
                self.openai_client = OpenAI(api_key=api_key)
            else:
                openai.api_key = api_key
                self.openai_client = None
            logger.info("OpenAI client initialized")
        except Exception as e:
            logger.error(f"OpenAI initialization failed: {str(e)}")
            raise Exception(f"OpenAI initialization failed: {str(e)}")

    def _get_product_name_field(self) -> str:
        if hasattr(self, '_product_name_field'):
            return self._product_name_field

        sample_product = self.db.products.find_one(projection={"name": 1, "title": 1})
        if sample_product and "name" in sample_product:
            self._product_name_field = "name"
        else:
            self._product_name_field = "title"

        return self._product_name_field

    def get_available_collections(self) -> List[str]:
        return self.db.list_collection_names()

    def get_product_count(self) -> int:
        return self.db.products.count_documents({})

    def query_products(self, filters: Dict[str, Any] = None, limit: int = 10) -> List[Dict]:
        collection = self.db.products
        results = list(collection.find(filters or {}).limit(limit))
        return results

    def search_products_by_name(self, name: str, limit: int = 10) -> List[Dict]:
        name_field = self._get_product_name_field()
        query = {name_field: {"$regex": name, "$options": "i"}}
        return list(self.db.products.find(query).limit(limit))

    def get_product_by_id(self, product_id: str) -> Dict:
        try:
            collection = self.db.products
            result = collection.find_one({"_id": ObjectId(product_id)})
            if result:
                return result
            return {"error": f"Product with ID {product_id} not found"}
        except Exception as e:
            return {"error": f"Invalid product ID: {str(e)}"}

    def find_product_by_rank(self, rank: int, order: str, category: str = None) -> Dict:
        if not isinstance(rank, int) or rank < 1:
            return {"error": "Rank must be a positive integer."}
        if order not in ['highest', 'cheapest']:
            return {"error": "Order must be either 'highest' or 'cheapest'."}

        name_field = self._get_product_name_field()
        query_filter = {}
        if category:
            query_filter[name_field] = {"$regex": category, "$options": "i"}

        sort_direction = -1 if order == 'highest' else 1
        items_to_skip = rank - 1

        pipeline = [
            {"$match": query_filter},
            {"$addFields": {"numeric_price": {"$toDouble": "$price"}}},
            {"$sort": {"numeric_price": sort_direction}},
            {"$skip": items_to_skip},
            {"$limit": 1}
        ]

        results = list(self.db.products.aggregate(pipeline))

        if results:
            return results[0]
        else:
            return {"message": f"Sorry, I couldn't find a product at rank {rank} within the category '{category}'."}

    def find_products_by_price_comparison(self, reference_product_name: str = None,
                                          reference_product_id: str = None,
                                          comparison_type: str = None, limit: int = 5) -> Dict:
        name_field = self._get_product_name_field()
        reference_product = None

        if reference_product_id:
            try:
                reference_product = self.db.products.find_one(
                    {"_id": ObjectId(reference_product_id)})
            except Exception:
                return {"message": f"Sorry, the provided product ID '{reference_product_id}' is invalid."}
        elif reference_product_name:
            reference_product = self.db.products.find_one(
                {name_field: {"$regex": reference_product_name, "$options": "i"}})

        if not reference_product or "price" not in reference_product:
            product_identifier = reference_product_id or reference_product_name
            return {"message": f"Sorry, I could not find '{product_identifier}' or it has no price information."}

        reference_price = reference_product["price"]
        reference_name = reference_product[name_field]

        query_filter, sort_order = {}, None
        if comparison_type == 'same':
            query_filter = {"price": reference_price, name_field: {"$ne": reference_name}}
        elif comparison_type == 'lower':
            query_filter, sort_order = {"price": {"$lt": reference_price}}, [("price", -1)]
        elif comparison_type == 'higher':
            query_filter, sort_order = {"price": {"$gt": reference_price}}, [("price", 1)]
        else:
            return {"error": "Invalid comparison type provided for the query."}

        cursor = self.db.products.find(query_filter).limit(limit)
        if sort_order:
            cursor = cursor.sort(sort_order)
        results = list(cursor)

        return {
            "reference_product": {"name": reference_name, "price": reference_price},
            "comparison_type": comparison_type,
            "matching_products": results
        }

    def add_customer_inquiry(self, customer_name: str, inquiry: str, response: str, session_id: str = "default"):
        collection = self.db.customer_inquiries
        inquiry_doc = {
            "customer_name": customer_name,
            "inquiry": inquiry,
            "response": response,
            "session_id": session_id,
            "timestamp": datetime.utcnow()
        }
        collection.insert_one(inquiry_doc)

    def get_function_definitions(self) -> List[Dict]:
        return [
            {
                "name": "get_product_count",
                "description": "Get the total number of products in the database",
                "parameters": {"type": "object", "properties": {}}
            },
            {
                "name": "query_products",
                "description": "Query products from the database with optional filters",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filters": {"type": "object", "description": "MongoDB query filters"},
                        "limit": {"type": "integer", "description": "Maximum number of results", "default": 10}
                    }
                }
            },
            {
                "name": "search_products_by_name",
                "description": "Search for products by name",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Product name to search for"},
                        "limit": {"type": "integer", "description": "Maximum number of results", "default": 10}
                    },
                    "required": ["name"]
                }
            },
            {
                "name": "get_product_by_id",
                "description": "Get detailed information about a specific product by its ID",
                "parameters": {
                    "type": "object",
                    "properties": {"product_id": {"type": "string", "description": "The MongoDB ObjectId of the product"}},
                    "required": ["product_id"]
                }
            },
            {
                "name": "find_product_by_rank",
                "description": "Find a product at a specific price rank, optionally within a category",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "rank": {"type": "integer", "description": "The numerical rank to find"},
                        "order": {"type": "string", "description": "Either 'highest' or 'cheapest'", "enum": ["highest", "cheapest"]},
                        "category": {"type": "string", "description": "Optional category to limit search"}
                    },
                    "required": ["rank", "order"]
                }
            },
            {
                "name": "find_products_by_price_comparison",
                "description": "Find products by price comparison to a reference product",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reference_product_name": {"type": "string", "description": "Name of reference product"},
                        "reference_product_id": {"type": "string", "description": "ID of reference product"},
                        "comparison_type": {"type": "string", "description": "Type of comparison", "enum": ["same", "lower", "higher"]},
                        "limit": {"type": "integer", "description": "Maximum results", "default": 5}
                    },
                    "required": ["comparison_type"]
                }
            }
        ]

    def execute_function(self, function_name: str, arguments: Dict) -> Any:
        try:
            if function_name == "get_product_count":
                return {"total_products": self.get_product_count()}
            elif function_name == "query_products":
                return self.query_products(filters=arguments.get("filters"), limit=arguments.get("limit", 10))
            elif function_name == "search_products_by_name":
                return self.search_products_by_name(name=arguments["name"], limit=arguments.get("limit", 10))
            elif function_name == "get_product_by_id":
                return self.get_product_by_id(arguments["product_id"])
            elif function_name == "find_product_by_rank":
                return self.find_product_by_rank(
                    rank=arguments.get("rank"),
                    order=arguments.get("order"),
                    category=arguments.get("category")
                )
            elif function_name == "find_products_by_price_comparison":
                return self.find_products_by_price_comparison(
                    reference_product_name=arguments.get("reference_product_name"),
                    reference_product_id=arguments.get("reference_product_id"),
                    comparison_type=arguments.get("comparison_type"),
                    limit=arguments.get("limit", 5)
                )
            else:
                return {"error": f"Unknown function: {function_name}"}
        except Exception as e:
            logger.error(f"Function execution error: {str(e)}")
            return {"error": f"Function execution failed: {str(e)}"}

    def _get_conversation_history(self, session_id: str) -> List[Dict]:
        conversation = self.conversations_collection.find_one({"session_id": session_id})
        if conversation:
            return conversation.get("history", [])
        return []

    def _save_conversation_history(self, session_id: str, history: List[Dict], last_subject: Optional[str]):
        self.conversations_collection.update_one(
            {"session_id": session_id},
            {"$set": {"history": history, "last_conversation_subject": last_subject,
                      "updated_at": datetime.utcnow()}},
            upsert=True
        )

    def get_all_sessions(self) -> List[Dict]:
        """Gets all conversation sessions, returning only essential info."""
        sessions = self.conversations_collection.find(
            {},
            {
                "session_id": 1,
                "history": {"$slice": 1},  # Get only the first message for context
                "updated_at": 1,
                "_id": 0
            }
        ).sort("updated_at", -1)
        return list(sessions)

    def _get_last_subject(self, session_id: str) -> Optional[str]:
        conversation = self.conversations_collection.find_one({"session_id": session_id})
        if conversation:
            return conversation.get("last_conversation_subject")
        return None

    def _update_conversation_subject(self, session_id: str, function_result: Any):
        name_field = self._get_product_name_field()
        last_subject = None

        if isinstance(function_result, dict):
            if name_field in function_result:
                last_subject = function_result.get(name_field)
            elif "reference_product" in function_result and "name" in function_result["reference_product"]:
                last_subject = function_result["reference_product"].get("name")
        elif isinstance(function_result, list) and len(function_result) == 1 and name_field in function_result[0]:
            last_subject = function_result[0].get(name_field)

        if last_subject:
            self.conversations_collection.update_one(
                {"session_id": session_id},
                {"$set": {"last_conversation_subject": last_subject}}
            )

    def chat(self, user_message: str, customer_name: str = "Guest", session_id: str = "default") -> str:
        conversation_history = self._get_conversation_history(session_id)
        last_subject = self._get_last_subject(session_id)

        # --- FIX START: Smarter history trimming ---
        # This function ensures that we don't separate tool calls from their results
        def trim_history(history, max_length=10):
            if len(history) <= max_length:
                return history

            trimmed_history = history[-max_length:]

            # Ensure the first message is not a tool response without its call
            if trimmed_history and trimmed_history[0].get("role") == "tool":
                # If the first message is a tool response, we need to find its call
                # and include it, even if it exceeds the max length slightly.

                # The message right before the tool response should be the tool call
                potential_tool_call_index = len(history) - max_length - 1
                if potential_tool_call_index >= 0:
                    previous_message = history[potential_tool_call_index]
                    if previous_message.get("role") == "assistant" and previous_message.get("tool_calls"):
                        # Prepend the tool call message to our trimmed history
                        trimmed_history.insert(0, previous_message)

            return trimmed_history

        conversation_history = trim_history(conversation_history)
        # --- FIX END ---

        # Handle follow-up context
        follow_up_keywords = ['price', 'lower', 'higher', 'same', 'cost', 'cheaper', 'expensive']
        is_short_follow_up = len(user_message.split()) <= 3 and any(
            key in user_message.lower() for key in follow_up_keywords)

        if last_subject and is_short_follow_up:
            user_message_to_process = f"Regarding the '{last_subject}', {user_message}"
        else:
            user_message_to_process = user_message

        conversation_history.append({
            "role": "user",
            "content": user_message_to_process
        })

        system_message = {
            "role": "system",
            "content": """You are a helpful customer service chatbot with access to a product database.
            
            CRITICAL INSTRUCTIONS:
            1. Use IDs for Follow-ups: When you list products, ALWAYS include their name/title and their unique `_id`.
            2. DILIGENT LIST PROCESSING: When a tool returns multiple products, iterate through EVERY item and display name/title and price.
            3. MAINTAINING CONTEXT: Apply context for ranking questions after listing categories.
            """
        }

        messages = [system_message] + conversation_history

        try:
            if OPENAI_V1:
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    tools=[{"type": "function", "function": func}
                           for func in self.get_function_definitions()],
                    tool_choice="auto"
                )

                response_message = response.choices[0].message

                if response_message.tool_calls:
                    tool_calls_list = []
                    for tc in response_message.tool_calls:
                        tool_calls_list.append(tc.model_dump())

                    conversation_history.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": tool_calls_list
                    })

                    for tool_call in response_message.tool_calls:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)

                        function_response = self.execute_function(function_name, function_args)
                        self._update_conversation_subject(session_id, function_response)

                        conversation_history.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": bson_dumps(function_response)
                        })

                    second_response = self.openai_client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[system_message] + conversation_history
                    )
                    final_message = second_response.choices[0].message.content
                else:
                    final_message = response_message.content
            else:
                # Legacy OpenAI API
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    functions=self.get_function_definitions(),
                    function_call="auto"
                )
                response_message = response.choices[0].message

                if hasattr(response_message, 'function_call') and response_message.function_call:
                    function_name = response_message.function_call.name
                    function_args = json.loads(response_message.function_call.arguments)

                    function_response = self.execute_function(function_name, function_args)
                    self._update_conversation_subject(session_id, function_response)

                    conversation_history.append({
                        "role": "assistant",
                        "content": None,
                        "function_call": {"name": function_name, "arguments": response_message.function_call.arguments}
                    })
                    conversation_history.append({
                        "role": "function", "name": function_name, "content": bson_dumps(function_response)
                    })

                    second_response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[system_message] + conversation_history
                    )
                    final_message = second_response.choices[0].message.content
                else:
                    final_message = response_message.content

            conversation_history[-1]['content'] = user_message
            conversation_history.append({"role": "assistant", "content": final_message})

            self._save_conversation_history(session_id, conversation_history, last_subject)
            self.add_customer_inquiry(customer_name, user_message, final_message, session_id)

            return final_message

        except Exception as e:
            logger.error(f"Chat error: {str(e)}")
            return "I'm sorry, I encountered an error processing your request. Please try again."

    def reset_conversation(self, session_id: str = "default"):
        self.conversations_collection.delete_one({"session_id": session_id})

    def close(self):
        self.client.close()
