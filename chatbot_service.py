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
        self.conversations = {}

        # --- Tool Categorization ---

        # Category 1: Product & Category Inquiry Tools
        product_tools = {
            "get_product_count": {
                "function": self.get_product_count,
                "schema": {
                    "name": "get_product_count",
                    "description": "Get the total number of products in the database.",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            "search_products_by_name": {
                "function": self.search_products_by_name,
                "schema": {
                    "name": "search_products_by_name",
                    "description": "Search for products by name.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Product name to search for"},
                            "limit": {"type": "integer", "description": "Maximum number of results", "default": 10}
                        },
                        "required": ["name"]
                    }
                }
            },
            "get_product_by_id": {
                "function": self.get_product_by_id,
                "schema": {
                    "name": "get_product_by_id",
                    "description": "Get detailed information about a specific product by its ID.",
                    "parameters": {
                        "type": "object",
                        "properties": {"product_id": {"type": "string", "description": "The MongoDB ObjectId of the product"}},
                        "required": ["product_id"]
                    }
                }
            },
            "get_product_categories": {
                "function": self.get_product_categories,
                "schema": {
                    "name": "get_product_categories",
                    "description": "Get a list of all available product categories.",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        }

        # Category 2: Pricing & Comparison Tools
        pricing_tools = {
            "find_product_by_price_rank": {
                "function": self.find_product_by_price_rank,
                "schema": {
                    "name": "find_product_by_price_rank",
                    "description": "Use ONLY for price-related rankings. Finds a product at a specific price rank (e.g., cheapest, most expensive), optionally within a category.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "rank": {"type": "integer", "description": "The numerical rank to find (e.g., 1 for the top)"},
                            "order": {"type": "string", "description": "Either 'highest' or 'cheapest'", "enum": ["highest", "cheapest"]},
                            "category": {"type": "string", "description": "Optional category to limit the search"}
                        },
                        "required": ["rank", "order"]
                    }
                }
            },
            "find_product_by_discount_rank": {
                "function": self.find_product_by_discount_rank,
                "schema": {
                    "name": "find_product_by_discount_rank",
                    "description": "Use ONLY for discount-related rankings. Finds a product based on its discount ranking (e.g., 'most discounted', 'biggest sale'). 'Most' implies rank=1 and order='highest'. 'Least' implies rank=1 and order='lowest'.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "rank": {"type": "integer", "description": "The numerical rank of the discount to find (e.g., 1 for the most discounted)."},
                            "order": {"type": "string", "description": "Either 'highest' (most discount) or 'lowest' (least discount).", "enum": ["highest", "lowest"]},
                            "category": {"type": "string", "description": "Optional category to limit the search."}
                        },
                        "required": ["rank", "order"]
                    }
                }
            },
            "find_products_by_price_comparison": {
                "function": self.find_products_by_price_comparison,
                "schema": {
                    "name": "find_products_by_price_comparison",
                    "description": "Find products with a similar, lower, or higher price than a reference product.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reference_product_name": {"type": "string", "description": "Name of the reference product"},
                            "reference_product_id": {"type": "string", "description": "ID of the reference product"},
                            "comparison_type": {"type": "string", "description": "Type of comparison", "enum": ["same", "lower", "higher"]},
                            "limit": {"type": "integer", "description": "Maximum number of results to return", "default": 5}
                        },
                        "required": ["comparison_type"]
                    }
                }
            }
        }

        # Category 3: User & Order Management Tools
        user_order_tools = {
            "get_user_by_name": {
                "function": self.get_user_by_name,
                "schema": {
                    "name": "get_user_by_name",
                    "description": "Find a user's details by their name to get their ID for other operations.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "customer_name": {"type": "string", "description": "The name of the customer to find."}
                        },
                        "required": ["customer_name"]
                    }
                }
            },
            "get_user_order_history": {
                "function": self.get_user_order_history,
                "schema": {
                    "name": "get_user_order_history",
                    "description": "Get the order history for a specific user using their user ID.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string", "description": "The ID of the user, likely obtained from get_user_by_name."}
                        },
                        "required": ["user_id"]
                    }
                }
            }
        }

        # Merge all toolsets into a single dictionary
        self.tools = {**product_tools, **pricing_tools, **user_order_tools}

    def _initialize_mongodb(self, mongo_uri: str, database_name: str):
        try:
            self.client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000)
            self.db = self.client[database_name]
            self.client.admin.command('ping')
            logger.info("MongoDB connection successful")
        except Exception as e:
            logger.error(f"MongoDB connection failed: {str(e)}")
            raise

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
            raise

    # --- Tool Implementation Methods ---

    # Product & Category Inquiry Methods
    def _get_product_name_field(self) -> str:
        if hasattr(self, '_product_name_field'):
            return self._product_name_field
        sample_product = self.db.products.find_one(projection={"name": 1, "title": 1})
        self._product_name_field = "name" if sample_product and "name" in sample_product else "title"
        return self._product_name_field
        
    def get_available_collections(self) -> List[str]:
        return self.db.list_collection_names()

    def get_product_count(self) -> Dict[str, int]:
        return {"total_products": self.db.products.count_documents({})}

    def search_products_by_name(self, name: str, limit: int = 10) -> List[Dict]:
        name_field = self._get_product_name_field()
        return list(self.db.products.find({name_field: {"$regex": name, "$options": "i"}}).limit(limit))

    def get_product_by_id(self, product_id: str) -> Dict:
        try:
            result = self.db.products.find_one({"_id": ObjectId(product_id)})
            return result if result else {"error": f"Product with ID {product_id} not found"}
        except Exception as e:
            return {"error": f"Invalid product ID: {str(e)}"}

    def get_product_categories(self) -> List[Dict]:
        try:
            return list(self.db['product-category'].find({}, {"_id": 0}))
        except Exception as e:
            logger.error(f"Error fetching product categories: {e}")
            return [{"error": "Could not retrieve product categories."}]

    # Pricing & Comparison Methods
    def find_product_by_price_rank(self, rank: int, order: str, category: str = None) -> Dict:
        if not isinstance(rank, int) or rank < 1:
            return {"error": "Rank must be a positive integer."}
        if order not in ['highest', 'cheapest']:
            return {"error": "Order must be either 'highest' or 'cheapest'."}
        name_field = self._get_product_name_field()
        query_filter = {}
        if category:
            query_filter[name_field] = {"$regex": category, "$options": "i"}
        sort_direction = -1 if order == 'highest' else 1
        pipeline = [
            {"$match": query_filter},
            {"$addFields": {"numeric_price": {"$toDouble": "$price"}}},
            {"$sort": {"numeric_price": sort_direction}},
            {"$skip": rank - 1},
            {"$limit": 1}
        ]
        results = list(self.db.products.aggregate(pipeline))
        return results[0] if results else {"message": f"Sorry, couldn't find a product at rank {rank}."}

    def find_product_by_discount_rank(self, rank: int, order: str, category: str = None) -> Dict:
        if not isinstance(rank, int) or rank < 1:
            return {"error": "Rank must be a positive integer."}
        if order not in ['highest', 'lowest']:
            return {"error": "Order must be 'highest' or 'lowest'."}
        name_field = self._get_product_name_field()
        query_filter = {}
        if category:
            query_filter[name_field] = {"$regex": category, "$options": "i"}
        sort_direction = -1 if order == 'highest' else 1
        pipeline = [
            {"$match": query_filter},
            {"$sort": {"discountPercentage": sort_direction}},
            {"$skip": rank - 1},
            {"$limit": 1}
        ]
        try:
            results = list(self.db.products.aggregate(pipeline))
            return results[0] if results else {"message": f"Could not find a product at rank {rank} for discounts."}
        except Exception as e:
            logger.error(f"Error finding product by discount rank: {e}")
            return {"error": "An error occurred while finding the product by discount."}

    def find_products_by_price_comparison(self, reference_product_name: str = None, reference_product_id: str = None, comparison_type: str = None, limit: int = 5) -> Dict:
        name_field = self._get_product_name_field()
        reference_product = None
        if reference_product_id:
            try:
                reference_product = self.db.products.find_one({"_id": ObjectId(reference_product_id)})
            except Exception:
                return {"message": f"Invalid product ID '{reference_product_id}'."}
        elif reference_product_name:
            reference_product = self.db.products.find_one({name_field: {"$regex": reference_product_name, "$options": "i"}})
        if not reference_product or "price" not in reference_product:
            return {"message": f"Could not find '{reference_product_id or reference_product_name}' or it has no price."}
        reference_price, reference_name = reference_product["price"], reference_product[name_field]
        query_filter, sort_order = {}, None
        if comparison_type == 'same':
            query_filter = {"price": reference_price, name_field: {"$ne": reference_name}}
        elif comparison_type == 'lower':
            query_filter, sort_order = {"price": {"$lt": reference_price}}, [("price", -1)]
        elif comparison_type == 'higher':
            query_filter, sort_order = {"price": {"$gt": reference_price}}, [("price", 1)]
        else:
            return {"error": "Invalid comparison type provided."}
        cursor = self.db.products.find(query_filter).limit(limit)
        if sort_order:
            cursor = cursor.sort(sort_order)
        return {"reference_product": {"name": reference_name, "price": reference_price}, "comparison_type": comparison_type, "matching_products": list(cursor)}

    # User & Order Management Methods
    def get_user_by_name(self, customer_name: str) -> Dict:
        try:
            user_data = self.db.users.find_one({"name": {"$regex": customer_name, "$options": "i"}}, {"password": 0})
            return user_data if user_data else {"error": f"User '{customer_name}' not found."}
        except Exception as e:
            logger.error(f"Error fetching user {customer_name}: {e}")
            return {"error": f"Could not retrieve user data for {customer_name}."}
            
    def get_user_order_history(self, user_id: str) -> List[Dict]:
        try:
            return list(self.db.orders.find({"userId": ObjectId(user_id)}))
        except Exception as e:
            logger.error(f"Error fetching order history for user ID {user_id}: {e}")
            return [{"error": f"Could not retrieve order history for user ID {user_id}."}]

    def add_customer_inquiry(self, customer_name: str, inquiry: str, response: str, session_id: str = "default"):
        inquiry_doc = {"customer_name": customer_name, "inquiry": inquiry, "response": response, "session_id": session_id, "timestamp": datetime.utcnow()}
        self.db.customer_inquiries.insert_one(inquiry_doc)

    # --- Core Chatbot Logic ---
    def get_function_definitions(self) -> List[Dict]:
        return [tool["schema"] for tool in self.tools.values()]

    def execute_function(self, function_name: str, arguments: Dict) -> Any:
        if function_name in self.tools:
            try:
                return self.tools[function_name]["function"](**arguments)
            except Exception as e:
                logger.error(f"Function execution error for '{function_name}': {e}")
                return {"error": f"Function execution failed: {str(e)}"}
        else:
            return {"error": f"Unknown function: {function_name}"}

    def _get_conversation_history(self, session_id: str) -> List[Dict]:
        if session_id not in self.conversations:
            self.conversations[session_id] = {"history": [], "last_conversation_subject": None}
        return self.conversations[session_id]["history"]

    def _update_conversation_subject(self, session_id: str, function_result: Any):
        name_field = self._get_product_name_field()
        if isinstance(function_result, dict):
            if name_field in function_result:
                self.conversations[session_id]["last_conversation_subject"] = function_result.get(name_field)
            elif "reference_product" in function_result and "name" in function_result["reference_product"]:
                self.conversations[session_id]["last_conversation_subject"] = function_result["reference_product"].get("name")
        elif isinstance(function_result, list) and len(function_result) == 1 and name_field in function_result[0]:
            self.conversations[session_id]["last_conversation_subject"] = function_result[0].get(name_field)

    def chat(self, user_message: str, customer_name: str = "Guest", session_id: str = "default") -> str:
        conversation_history = self._get_conversation_history(session_id)
        last_subject = self.conversations[session_id].get("last_conversation_subject")
        follow_up_keywords = ['price', 'lower', 'higher', 'same', 'cost', 'cheaper', 'expensive']
        is_short_follow_up = len(user_message.split()) <= 3 and any(key in user_message.lower() for key in follow_up_keywords)
        user_message_to_process = f"Regarding '{last_subject}', {user_message}" if last_subject and is_short_follow_up else user_message
        conversation_history.append({"role": "user", "content": user_message_to_process})
        system_message = {
            "role": "system",
            "content": """You are a helpful customer service chatbot with access to a product database.
            
            CRITICAL INSTRUCTIONS:
            1. Use IDs for Follow-ups: When you list products, ALWAYS include their name/title and their unique `_id`.
            2. DILIGENT LIST PROCESSING: When a tool returns multiple products, iterate through EVERY item and display name/title and price.
            3. MAINTAINING CONTEXT: Apply context for ranking questions after listing categories.
            4. DISPLAY IMAGES: If a product has a 'thumbnail' URL, you MUST display it. The markdown for the image, `![Product Image](URL)`, MUST be on its own separate line and NOT part of a list (no leading `-` or `*`).
            5. RESPONSE FORMATTING: Do not use Markdown headings (e.g., '#', '##', '###'). Use bold text (`**text**`) for titles or emphasis instead.
            6. AVOID GENERIC RESPONSES: Do not use phrases like "As an AI language model...". Always provide a direct answer.
            7. HANDLING NO RESULTS: If a tool returns no results, respond with "Sorry, I couldn't find any products matching your criteria."
            8. ERROR HANDLING: If a tool returns an error, include the error message in your response.
            9. CLARIFYING AMBIGUITIES: If a user query is ambiguous, ask for clarification instead of guessing.
            10. TOOL USAGE: Use the provided tools to fetch data. Do not make up information.

            CRITICAL INSTRUCTIONS FOR RANKING QUERIES:
            - For price queries like "cheapest" or "most expensive", use the `find_product_by_price_rank` tool.
            - For discount queries like "most discount" or "biggest discount", use the `find_product_by_discount_rank` tool with `rank=1` and `order='highest'`.
            """
        }
        messages = [system_message] + conversation_history
        try:
            if OPENAI_V1:
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    tools=[{"type": "function", "function": func} for func in self.get_function_definitions()],
                    tool_choice="auto"
                )
                response_message = response.choices[0].message
                if response_message.tool_calls:
                    conversation_history.append({"role": "assistant", "content": None, "tool_calls": response_message.tool_calls})
                    for tool_call in response_message.tool_calls:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)
                        function_response = self.execute_function(function_name, function_args)
                        self._update_conversation_subject(session_id, function_response)
                        conversation_history.append({"role": "tool", "tool_call_id": tool_call.id, "content": bson_dumps(function_response)})
                    second_response = self.openai_client.chat.completions.create(model="gpt-3.5-turbo", messages=[system_message] + conversation_history)
                    final_message = second_response.choices[0].message.content
                else:
                    final_message = response_message.content
            else:
                pass # Legacy implementation
            conversation_history.append({"role": "assistant", "content": final_message})
            if len(conversation_history) > 20:
                self.conversations[session_id]["history"] = conversation_history[-20:]
            self.add_customer_inquiry(customer_name, user_message, final_message, session_id)
            return final_message
        except Exception as e:
            logger.error(f"Chat error: {str(e)}")
            return "I'm sorry, I encountered an error. Please try again."

    def reset_conversation(self, session_id: str = "default"):
        if session_id in self.conversations:
            del self.conversations[session_id]

    def close(self):
        self.client.close()

