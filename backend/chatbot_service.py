import os
import logging
from typing import List, Dict, Any, Optional
from bson import ObjectId

try:
    from openai import OpenAI
    OPENAI_V1 = True
except ImportError:
    import openai
    OPENAI_V1 = False

from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferWindowMemory

from .agent import build_agent
from .tooling import build_langchain_tools
from .db import initialize_mongodb
from .utils.products import detect_product_name_field
from .semantic_matching import SemanticMatcher
from .tool_definitions import ToolDefinitions
from .conversation_manager import ConversationManager
from .sequential_pipeline import SequentialPipeline
from .error_handler import ErrorHandler
from . import tools_product as product_ops
from . import tools_pricing as pricing_ops
from . import tools_user as user_ops
from . import tools_rag as rag_ops


logger = logging.getLogger(__name__)


class MongoDBChatbotService:
    def __init__(self, mongo_uri: str, openai_api_key: str, database_name: str = "product-management"):
        # Initialize core components
        self._initialize_mongodb(mongo_uri, database_name)
        self._initialize_openai(openai_api_key)
        
        # Initialize modular components
        self.semantic_matcher = SemanticMatcher(openai_api_key)
        self.conversation_manager = ConversationManager(self.db)
        self.error_handler = ErrorHandler()
        self._session_agents: Dict[str, Any] = {}

        # Initialize tools using the tool definitions module
        self.tools = ToolDefinitions.get_all_tools(self)
        self.lc_tools = build_langchain_tools(self.tools)

        # Initialize sequential pipeline
        self.sequential_pipeline = SequentialPipeline(self.lc_llm, self.tools)


    def _get_or_create_agent(self, session_id: str):
        if session_id in self._session_agents:
            return self._session_agents[session_id]
        memory = ConversationBufferWindowMemory(
            k=6,
            memory_key="chat_history",
            return_messages=True,
            ai_prefix="assistant",
            human_prefix="user",
        )
        agent = build_agent(self.lc_llm, self.lc_tools, memory=memory)
        self._session_agents[session_id] = agent
        return agent

    def _initialize_mongodb(self, mongo_uri: str, database_name: str):
        try:
            self.client, self.db = initialize_mongodb(mongo_uri, database_name)
        except Exception as e:
            logger.error(f"MongoDB connection failed: {str(e)}")
            raise

    def _initialize_openai(self, api_key: str):
        try:
            os.environ.setdefault("OPENAI_API_KEY", api_key)
            self.lc_llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
            if OPENAI_V1:
                self.openai_client = OpenAI(api_key=api_key)
            else:
                openai.api_key = api_key
                self.openai_client = None
            logger.info("OpenAI (LangChain) client initialized")
        except Exception as e:
            logger.error(f"OpenAI initialization failed: {str(e)}")
            raise

    # --- Tool Implementation Methods ---
    def _get_product_name_field(self) -> str:
        if hasattr(self, '_product_name_field'):
            return self._product_name_field
        self._product_name_field = detect_product_name_field(self.db)
        return self._product_name_field

    def get_available_collections(self) -> List[str]:
        return product_ops.get_available_collections(self.db)

    def get_product_count(self) -> Dict[str, int]:
        return product_ops.get_product_count(self.db)

    def search_products_by_name(self, name: str, limit: int = 10) -> List[Dict]:
        name_field = self._get_product_name_field()
        return product_ops.search_products_by_name(self.db, name_field, name, limit)

    def get_product_by_id(self, product_id: str) -> Dict:
        try:
            return product_ops.get_product_by_id(self.db, ObjectId(product_id))
        except Exception as e:
            return {"error": f"Invalid product ID: {str(e)}"}

    def get_product_categories(self) -> List[Dict]:
        try:
            return product_ops.get_product_categories(self.db)
        except Exception as e:
            logger.error(f"Error fetching product categories: {e}")
            return [{"error": "Could not retrieve product categories."}]

    def get_available_categories_from_products(self) -> List[str]:
        """Get unique categories that actually exist in the products collection."""
        try:
            pipeline = [
                {"$group": {"_id": "$category"}},
                {"$match": {"_id": {"$ne": None}}},
                {"$sort": {"_id": 1}}
            ]
            results = list(self.db.products.aggregate(pipeline))
            categories = [result["_id"] for result in results if result["_id"]]
            return categories
        except Exception as e:
            logger.error(f"Error fetching available categories: {e}")
            return []

    def find_semantic_category_match(self, user_category: str, threshold: float = 0.7) -> Optional[str]:
        """Find the most semantically similar category using OpenAI embeddings."""
        available_categories = self.get_available_categories_from_products()
        return self.semantic_matcher.find_semantic_category_match(user_category, available_categories, threshold)

    def find_semantic_order_match(self, user_order: str, order_type: str = "price") -> Optional[str]:
        """Find the most semantically similar order term using OpenAI embeddings."""
        return self.semantic_matcher.find_semantic_order_match(user_order, order_type)

    def get_top_k_products_by_price(self, k: int, order: str, category: str = None) -> List[Dict]:
        # Normalize arguments semantically instead of relying on strict keywords
        k = int(k) if str(k).isdigit() and int(k) > 0 else 1
        
        # Use semantic order matching
        order_normalized = self.find_semantic_order_match(order, "price")
        if not order_normalized:
            return [{"error": f"Could not understand order term '{order}'. Please use terms like 'highest', 'cheapest', 'most expensive', 'lowest', etc."}]

        # Handle semantic category matching
        matched_category = None
        if category:
            matched_category = self.find_semantic_category_match(category)

        name_field = self._get_product_name_field()
        return pricing_ops.get_top_k_products_by_price(self.db, name_field, k, order_normalized, matched_category)

    def find_product_by_price_rank(self, rank: int, order: str, category: str = None) -> Dict:
        # Normalize arguments semantically instead of relying on strict keywords
        try:
            rank = int(rank)
            if rank < 1:
                rank = 1
        except Exception:
            rank = 1
        
        # Use semantic order matching
        order_normalized = self.find_semantic_order_match(order, "price")
        if not order_normalized:
            return {"error": f"Could not understand order term '{order}'. Please use terms like 'highest', 'cheapest', 'most expensive', 'lowest', etc."}
        
        # Handle semantic category matching
        matched_category = None
        if category:
            matched_category = self.find_semantic_category_match(category)
        
        name_field = self._get_product_name_field()
        return pricing_ops.find_product_by_price_rank(self.db, name_field, rank, order_normalized, matched_category)

    def find_product_by_discount_rank(self, rank: int, order: str, category: str = None) -> Dict:
        # Normalize arguments semantically instead of relying on strict keywords
        try:
            rank = int(rank)
            if rank < 1:
                rank = 1
        except Exception:
            rank = 1
        
        # Use semantic order matching for discount terms
        order_normalized = self.find_semantic_order_match(order, "discount")
        if not order_normalized:
            return {"error": f"Could not understand order term '{order}'. Please use terms like 'highest', 'lowest', 'most', 'least', 'biggest', 'smallest', etc."}
        
        # Handle semantic category matching
        matched_category = None
        if category:
            matched_category = self.find_semantic_category_match(category)
        
        name_field = self._get_product_name_field()
        try:
            return pricing_ops.find_product_by_discount_rank(self.db, name_field, rank, order_normalized, matched_category)
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
        # Use semantic matching for comparison type
        matched_comparison = self.find_semantic_order_match(comparison_type, "comparison")
        if not matched_comparison:
            return {"error": f"Could not understand comparison type '{comparison_type}'. Please use terms like 'same', 'lower', 'higher', 'cheaper', 'more expensive', etc."}
        comparison_type = matched_comparison
        return pricing_ops.find_products_by_price_comparison(self.db, name_field, reference_product, comparison_type, limit)

    def calculate_order_total(self, product_names: List[str]) -> Dict:
        name_field = self._get_product_name_field()
        return pricing_ops.calculate_order_total(self.db, name_field, product_names)

    def get_product_prices_for_chart(self, product_names: List[str]) -> Dict:
        name_field = self._get_product_name_field()
        return pricing_ops.get_product_prices_for_chart(self.db, name_field, product_names)

    def find_products_within_budget(self, budget: float, category: str = None, limit: int = 5) -> Dict:
        try:
            try:
                max_price = float(budget)
            except Exception:
                return {"error": "Invalid budget amount."}
            if limit is None or not isinstance(limit, int) or limit < 1:
                limit = 5
            
            # Handle semantic category matching
            matched_category = None
            if category:
                matched_category = self.find_semantic_category_match(category)
                if not matched_category:
                    # If no semantic match found, try without category but inform user
                    logger.info(f"No semantic match found for category '{category}', trying without category filter")
                    name_field = self._get_product_name_field()
                    result = pricing_ops.find_products_within_budget(self.db, name_field, max_price, None, limit)
                    if "message" in result:
                        result["message"] += f" (Note: No products found in category '{category}')"
                    return result
            
            name_field = self._get_product_name_field()
            return pricing_ops.find_products_within_budget(self.db, name_field, max_price, matched_category, limit)
        except Exception as e:
            logger.error(f"Error finding products within budget: {e}")
            return {"error": "An error occurred while searching by budget."}

    def get_user_by_name(self, customer_name: str) -> Dict:
        try:
            return user_ops.get_user_by_name(self.db, customer_name)
        except Exception as e:
            logger.error(f"Error fetching user {customer_name}: {e}")
            return {"error": f"Could not retrieve user data for {customer_name}."}

    def get_user_order_history(self, user_id: str) -> List[Dict]:
        try:
            return user_ops.get_user_order_history(self.db, user_id)
        except Exception as e:
            logger.error(f"Error fetching order history for user ID {user_id}: {e}")
            return [{"error": f"Could not retrieve order history for user ID {user_id}."}]

    # --- RAG tool implementation ---
    def answer_policy_pdf(self, question: str, k: int = 4) -> Dict:
        try:
            return rag_ops.answer_policy_pdf(question, k)
        except Exception as e:
            logger.error(f"RAG error: {e}")
            return {"error": "Failed to retrieve from policy PDF."}

    def add_customer_inquiry(self, customer_name: str, inquiry: str, response: str, session_id: str = "default"):
        self.conversation_manager.add_customer_inquiry(customer_name, inquiry, response, session_id)

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


    def chat(self, user_message: str, customer_name: str = "Guest", session_id: str = "default", include_reasoning: bool = False) -> str | dict:
        # Use LangChain memory per session instead of manually passing chat_history
        agent_executor = self._get_or_create_agent(session_id)

        try:
            result = agent_executor.invoke({
                "input": user_message
            })
            final_message: str = result.get("output", "")
            reasoning_trace = []
            if include_reasoning:
                intermediate_steps = result.get("intermediate_steps") or []
                reasoning_trace = self.conversation_manager.build_reasoning_trace(intermediate_steps)

            # Check if agent hit max iterations
            if not final_message or "Agent stopped due to max iterations" in str(result):
                final_message = self.error_handler.handle_max_iterations(user_message, result)

            # Update conversation history
            self.conversation_manager.add_to_history(session_id, user_message, final_message)
            self.add_customer_inquiry(customer_name, user_message, final_message, session_id)
            
            if include_reasoning:
                return {"answer": final_message, "reasoning": reasoning_trace}
            return final_message
        except Exception as e:
            logger.error(f"Chat error: {str(e)}")
            return "I'm sorry, I encountered an error. Please try again."

    def chat_sequential(self, user_message: str, customer_name: str = "Guest", session_id: str = "default", include_reasoning: bool = False) -> str | dict:
        """Sequential pipeline inspired by LangChain SequentialChain examples.

        Steps:
          1) Classify and normalize the user query into a {function_name, arguments} JSON.
          2) Execute the selected tool if available; otherwise fall back to the agent chat.
          3) Summarize the raw result and propose a follow-up question.
        """
        question = user_message.strip()
        if not question:
            return "Please provide a message."

        try:
            # Step 1: route to a tool
            intent_result = self.sequential_pipeline.route_intent(question)
            function_name = intent_result["function_name"]
            arguments = intent_result["arguments"]

            # Step 2: execute or fallback
            raw_result: Any
            used_tool = False
            if function_name in self.tools:
                try:
                    raw_result = self.execute_function(function_name, arguments)
                    used_tool = True
                except Exception:
                    raw_result = {"error": "Tool execution failed; falling back to general chat."}
                    used_tool = False
            else:
                # fallback to existing agent flow
                agent_executor = self._get_or_create_agent(session_id)
                agent_resp = agent_executor.invoke({"input": question})
                raw_result = {"answer": agent_resp.get("output", "")}
                function_name = "agent_fallback"

            # Step 3: summarize + follow-up
            summary_result = self.sequential_pipeline.summarize_result(
                question, function_name, arguments, 
                self.conversation_manager.to_jsonable(raw_result)
            )

            final_message = summary_result["answer"]
            if summary_result["follow_up"]:
                final_message = f"{final_message}\n\nFollow-up: {summary_result['follow_up']}"

            # persist history and inquiry
            self.conversation_manager.add_to_history(session_id, question, final_message)
            self.add_customer_inquiry(customer_name, question, final_message, session_id)

            if include_reasoning:
                trace = []
                if used_tool:
                    trace.append({
                        "tool": function_name,
                        "input": self.conversation_manager.to_jsonable(arguments),
                        "observation": self.conversation_manager.to_jsonable(raw_result),
                    })
                return {"answer": final_message, "reasoning": trace}
            return final_message
        except Exception as e:
            logger.error(f"Sequential chat error: {str(e)}")
            return "I'm sorry, I encountered an error. Please try again."

    def reset_conversation(self, session_id: str = "default"):
        self.conversation_manager.reset_conversation(session_id)

    def close(self):
        self.client.close()


