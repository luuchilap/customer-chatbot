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

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from langchain_core.messages import HumanMessage, AIMessage
from langchain.memory import ConversationBufferWindowMemory
from .agent import build_agent
from .tooling import build_langchain_tools
from .db import initialize_mongodb
from .utils.products import detect_product_name_field
from . import tools_product as product_ops
from . import tools_pricing as pricing_ops
from . import tools_user as user_ops
from . import tools_rag as rag_ops


logger = logging.getLogger(__name__)


class MongoDBChatbotService:
    def __init__(self, mongo_uri: str, openai_api_key: str, database_name: str = "product-management"):
        self._initialize_mongodb(mongo_uri, database_name)
        self._initialize_openai(openai_api_key)
        self.conversations = {}
        self._session_agents: Dict[str, Any] = {}

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
            "get_top_k_products_by_price": {
                "function": self.get_top_k_products_by_price,
                "schema": {
                    "name": "get_top_k_products_by_price",
                    "description": "Gets a list or table of the top 'k' products sorted by price. Use this for queries like 'show me the top 5 most expensive phones'.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "k": {"type": "integer", "description": "The number of products to return."},
                            "order": {"type": "string", "description": "Either 'highest' (for most expensive) or 'cheapest'.", "enum": ["highest", "cheapest"]},
                            "category": {"type": "string", "description": "Optional category to filter by."}
                        },
                        "required": ["k", "order"]
                    }
                }
            },
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
            },
            "calculate_order_total": {
                "function": self.calculate_order_total,
                "schema": {
                    "name": "calculate_order_total",
                    "description": "Calculates the final, discounted total cost for a list of products. Use this when a user asks for the total price of buying multiple items.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "product_names": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "A list of the names of products to include in the calculation."
                            }
                        },
                        "required": ["product_names"]
                    }
                }
            },
            "get_product_prices_for_chart": {
                "function": self.get_product_prices_for_chart,
                "schema": {
                    "name": "get_product_prices_for_chart",
                    "description": "Get product prices for a list of product names to generate a comparison chart.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "product_names": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "A list of product names to fetch prices for."
                            }
                        },
                        "required": ["product_names"]
                    }
                }
            }
            ,
            "find_products_within_budget": {
                "function": self.find_products_within_budget,
                "schema": {
                    "name": "find_products_within_budget",
                    "description": "Find up to 'limit' products priced at or under a budget, optionally filtered by category.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "budget": {"type": "number", "description": "Maximum budget in the same currency as product prices."},
                            "category": {"type": "string", "description": "Optional category to filter by."},
                            "limit": {"type": "integer", "description": "Max number of results", "default": 5}
                        },
                        "required": ["budget"]
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

        # Category 4: Policy PDF RAG Tools
        rag_tools = {
            "answer_policy_pdf": {
                "function": self.answer_policy_pdf,
                "schema": {
                    "name": "answer_policy_pdf",
                    "description": "Answer questions about the ecommerce policy PDF using retrieval-augmented snippets. Returns contexts and sources.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {"type": "string", "description": "User question about the policy document."},
                            "k": {"type": "integer", "description": "How many chunks to retrieve", "default": 4}
                        },
                        "required": ["question"]
                    }
                }
            }
        }

        # Merge all toolsets into a single dictionary
        self.tools = {**product_tools, **pricing_tools, **user_order_tools, **rag_tools}

        # Build LangChain tools (agent is built per-session to attach memory)
        self.lc_tools = build_langchain_tools(self.tools)

        # Build prompts/chains for sequential pipeline
        self._sequential_initialized = False

    def _ensure_sequential(self):
        if self._sequential_initialized:
            return
        # Use the same lc_llm instance for deterministic control
        llm = self.lc_llm

        # Chain 1: Normalize and classify intent into a tool call JSON
        tool_list = "\n".join(sorted(self.tools.keys()))
        intent_router_template = (
            "You are an assistant that maps a user's question to one of the available tools.\n"
            "Return ONLY a JSON object with fields: \n"
            "  function_name: string (one of the tools below or 'none')\n"
            "  arguments: object (JSON with named args)\n\n"
            "Available tools (function_name only):\n{tool_names}\n\n"
            "Notes:\n"
            "- If the query is about the policy PDF, use 'answer_policy_pdf' and pass the original question as 'question'.\n"
            "- If comparing prices, ranking, budget, or categories, choose the best-matching product/pricing tool.\n"
            "- If no suitable function exists, set function_name to 'none'.\n\n"
            "User question: {user_question}\n\n"
            "Output JSON:"
        )
        self._intent_router = LLMChain(
            llm=llm,
            prompt=ChatPromptTemplate.from_template(intent_router_template),
        )

        # Chain 2: Summarize tool result into a user-facing answer and propose a follow-up
        summarizer_template = (
            "You are a helpful product assistant.\n"
            "Summarize the tool result for the user question clearly and concisely.\n"
            "Include concrete details (names, prices, categories) when available.\n"
            "If sources are provided, mention them briefly.\n"
            "At the end, suggest a short follow-up question to continue the task.\n\n"
            "User question:\n{user_question}\n\n"
            "Tool used: {function_name}\n"
            "Tool arguments: {arguments}\n\n"
            "Raw tool result (JSON):\n{tool_result}\n\n"
            "Return a JSON object with fields:\n"
            "  answer: string\n"
            "  follow_up: string\n"
        )
        self._summarizer = LLMChain(
            llm=llm,
            prompt=ChatPromptTemplate.from_template(summarizer_template),
        )

        self._sequential_initialized = True

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

    def get_top_k_products_by_price(self, k: int, order: str, category: str = None) -> List[Dict]:
        # Normalize arguments semantically instead of relying on strict keywords
        k = int(k) if str(k).isdigit() and int(k) > 0 else 1
        order_normalized = str(order).strip().lower()
        if order_normalized in {"desc", "descending", "most", "top", "max", "expensive", "most expensive"}:
            order_normalized = "highest"
        elif order_normalized in {"asc", "ascending", "least", "min", "lowest", "cheapest", "cheap", "least expensive"}:
            order_normalized = "cheapest"
        if order_normalized not in ["highest", "cheapest"]:
            return [{"error": "Order must be either 'highest' or 'cheapest'."}]

        name_field = self._get_product_name_field()
        return pricing_ops.get_top_k_products_by_price(self.db, name_field, k, order_normalized, category)

    def find_product_by_price_rank(self, rank: int, order: str, category: str = None) -> Dict:
        # Normalize arguments semantically instead of relying on strict keywords
        try:
            rank = int(rank)
            if rank < 1:
                rank = 1
        except Exception:
            rank = 1
        order_normalized = str(order).strip().lower()
        if order_normalized in {"desc", "descending", "most", "top", "max", "expensive", "most expensive"}:
            order_normalized = "highest"
        elif order_normalized in {"asc", "ascending", "least", "min", "lowest", "cheapest", "cheap", "least expensive"}:
            order_normalized = "cheapest"
        if order_normalized not in ["highest", "cheapest"]:
            return {"error": "Order must be either 'highest' or 'cheapest'."}
        name_field = self._get_product_name_field()
        return pricing_ops.find_product_by_price_rank(self.db, name_field, rank, order_normalized, category)

    def find_product_by_discount_rank(self, rank: int, order: str, category: str = None) -> Dict:
        # Normalize arguments semantically instead of relying on strict keywords
        try:
            rank = int(rank)
            if rank < 1:
                rank = 1
        except Exception:
            rank = 1
        order_normalized = str(order).strip().lower()
        if order_normalized in {"desc", "descending", "most", "top", "max", "highest"}:
            order_normalized = "highest"
        elif order_normalized in {"asc", "ascending", "least", "min", "lowest"}:
            order_normalized = "lowest"
        if order_normalized not in ["highest", "lowest"]:
            return {"error": "Order must be 'highest' or 'lowest'."}
        name_field = self._get_product_name_field()
        try:
            return pricing_ops.find_product_by_discount_rank(self.db, name_field, rank, order_normalized, category)
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
        if comparison_type not in {"same", "lower", "higher"}:
            return {"error": "Invalid comparison type provided."}
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
            name_field = self._get_product_name_field()
            return pricing_ops.find_products_within_budget(self.db, name_field, max_price, category, limit)
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
        inquiry_doc = {"customer_name": customer_name, "inquiry": inquiry, "response": response, "session_id": session_id, "timestamp": datetime.utcnow()}
        self.db.customer_inquiries.insert_one(inquiry_doc)

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

    def _build_reasoning_trace(self, intermediate_steps) -> list:
        """Convert LangChain intermediate steps to a simple serializable trace.

        LangChain returns a list of (AgentAction, observation) tuples. We extract
        the tool name and inputs from AgentAction, and attach the observation.
        """
        reasoning_trace = []
        try:
            for step in intermediate_steps or []:
                action = None
                observation = None

                # Expected shape: tuple (AgentAction, observation)
                if isinstance(step, (tuple, list)) and len(step) == 2:
                    action, observation = step
                else:
                    # Fallback for unexpected shapes
                    action = getattr(step, "action", None) or step
                    observation = getattr(step, "observation", None)

                tool_name = None
                tool_input = None

                if action is not None:
                    tool_name = getattr(action, "tool", None) or getattr(action, "tool_name", None)
                    tool_input = getattr(action, "tool_input", None)
                    if hasattr(tool_input, "dict"):
                        tool_input = tool_input.dict()

                # Normalize observation to serializable
                if hasattr(observation, "dict"):
                    observation = observation.dict()

                # Convert any Mongo types (e.g., ObjectId) into JSON-safe forms
                tool_input = self._to_jsonable(tool_input)
                observation = self._to_jsonable(observation)

                # Only include valid tool invocations
                if tool_name:
                    reasoning_trace.append({
                        "tool": str(tool_name),
                        "input": tool_input,
                        "observation": observation,
                    })
        except Exception:
            # Best effort: never fail chat due to trace issues
            return []
        return reasoning_trace

    def _to_jsonable(self, value):
        """Best-effort conversion of Mongo/complex values to JSON-safe Python types.

        Uses bson.json_util to properly handle ObjectId, datetime, Decimal128, etc.
        If conversion fails, returns a string representation as a last resort.
        """
        try:
            if value is None:
                return None
            # Shortcut for simple primitives
            if isinstance(value, (str, int, float, bool)):
                return value
            # Use BSON util to convert any nested structure
            return json.loads(bson_dumps(value))
        except Exception:
            try:
                return str(value)
            except Exception:
                return None

    def chat(self, user_message: str, customer_name: str = "Guest", session_id: str = "default", include_reasoning: bool = False) -> str | dict:
        conversation_history = self._get_conversation_history(session_id)
        # Avoid keyword-based rewriting; rely on LLM prompt and tool schemas for semantics
        user_message_to_process = user_message

        # Use LangChain memory per session instead of manually passing chat_history
        agent_executor = self._get_or_create_agent(session_id)

        try:
            result = agent_executor.invoke({
                "input": user_message_to_process
            })
            final_message: str = result.get("output", "")
            reasoning_trace = []
            if include_reasoning:
                intermediate_steps = result.get("intermediate_steps") or []
                reasoning_trace = self._build_reasoning_trace(intermediate_steps)

            conversation_history.append({"role": "user", "content": user_message_to_process})
            conversation_history.append({"role": "assistant", "content": final_message})
            if len(conversation_history) > 20:
                self.conversations[session_id]["history"] = conversation_history[-20:]
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
        self._ensure_sequential()
        conversation_history = self._get_conversation_history(session_id)
        question = user_message.strip()
        if not question:
            return "Please provide a message."

        try:
            # Step 1: route to a tool
            intent_json = self._intent_router.run({
                "tool_names": "\n".join(sorted(self.tools.keys())),
                "user_question": question,
            }).strip()

            # Be defensive: parse JSON best-effort
            import json as _json
            function_name = "none"
            arguments = {}
            try:
                intent_obj = _json.loads(intent_json)
                function_name = str(intent_obj.get("function_name") or intent_obj.get("destination") or "none").strip()
                arguments = intent_obj.get("arguments") or intent_obj.get("next_inputs") or {}
                if isinstance(arguments, str):
                    try:
                        arguments = _json.loads(arguments)
                    except Exception:
                        arguments = {"input": arguments}
            except Exception:
                # If LLM returned non-JSON, fallback to agent
                function_name = "none"
                arguments = {}

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
            import json as _json2
            tool_result_str = _json2.dumps(self._to_jsonable(raw_result), ensure_ascii=False)
            summarizer_json = self._summarizer.run({
                "user_question": question,
                "function_name": function_name,
                "arguments": _json2.dumps(self._to_jsonable(arguments), ensure_ascii=False),
                "tool_result": tool_result_str,
            }).strip()

            summary_answer = None
            follow_up = None
            try:
                summary_obj = _json2.loads(summarizer_json)
                summary_answer = summary_obj.get("answer")
                follow_up = summary_obj.get("follow_up")
            except Exception:
                # If parsing fails, just return the raw text
                summary_answer = summarizer_json

            final_message = summary_answer or ""
            if follow_up:
                final_message = f"{final_message}\n\nFollow-up: {follow_up}"

            # persist history and inquiry
            conversation_history.append({"role": "user", "content": question})
            conversation_history.append({"role": "assistant", "content": final_message})
            if len(conversation_history) > 20:
                self.conversations[session_id]["history"] = conversation_history[-20:]
            self.add_customer_inquiry(customer_name, question, final_message, session_id)

            if include_reasoning:
                trace = []
                if used_tool:
                    trace.append({
                        "tool": function_name,
                        "input": self._to_jsonable(arguments),
                        "observation": self._to_jsonable(raw_result),
                    })
                return {"answer": final_message, "reasoning": trace}
            return final_message
        except Exception as e:
            logger.error(f"Sequential chat error: {str(e)}")
            return "I'm sorry, I encountered an error. Please try again."

    def reset_conversation(self, session_id: str = "default"):
        if session_id in self.conversations:
            del self.conversations[session_id]

    def close(self):
        self.client.close()


