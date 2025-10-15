"""
Tool definitions for the MongoDB chatbot service.
"""
from typing import Dict, Any


class ToolDefinitions:
    """Centralized tool definitions for the chatbot service."""
    
    @staticmethod
    def get_product_tools(service_instance) -> Dict[str, Dict[str, Any]]:
        """Get product and category inquiry tools."""
        return {
            "get_product_count": {
                "function": service_instance.get_product_count,
                "schema": {
                    "name": "get_product_count",
                    "description": "Get the total number of products in the database.",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            "search_products_by_name": {
                "function": service_instance.search_products_by_name,
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
                "function": service_instance.get_product_by_id,
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
                "function": service_instance.get_product_categories,
                "schema": {
                    "name": "get_product_categories",
                    "description": "Get a list of all available product categories.",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            "get_available_categories_from_products": {
                "function": service_instance.get_available_categories_from_products,
                "schema": {
                    "name": "get_available_categories_from_products",
                    "description": "Get a list of all unique categories that actually exist in the products collection.",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            "find_semantic_category_match": {
                "function": service_instance.find_semantic_category_match,
                "schema": {
                    "name": "find_semantic_category_match",
                    "description": "Find the most semantically similar category to a user's input using AI embeddings. Use this when the user mentions a category that might not exist exactly in the database.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_category": {"type": "string", "description": "The category name the user mentioned (e.g., 'phones', 'toys', 'electronics')"},
                            "threshold": {"type": "number", "description": "Minimum similarity score (0-1) to consider a match", "default": 0.7}
                        },
                        "required": ["user_category"]
                    }
                }
            },
            "find_semantic_order_match": {
                "function": service_instance.find_semantic_order_match,
                "schema": {
                    "name": "find_semantic_order_match",
                    "description": "Find the most semantically similar order term using AI embeddings. Use this when the user mentions ordering terms that might not be exact matches.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_order": {"type": "string", "description": "The order term the user mentioned (e.g., 'most expensive', 'cheapest', 'biggest discount')"},
                            "order_type": {"type": "string", "description": "Type of ordering: 'price' or 'discount'", "default": "price"}
                        },
                        "required": ["user_order"]
                    }
                }
            }
        }

    @staticmethod
    def get_pricing_tools(service_instance) -> Dict[str, Dict[str, Any]]:
        """Get pricing and comparison tools."""
        return {
            "get_top_k_products_by_price": {
                "function": service_instance.get_top_k_products_by_price,
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
                "function": service_instance.find_product_by_price_rank,
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
                "function": service_instance.find_product_by_discount_rank,
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
                "function": service_instance.find_products_by_price_comparison,
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
                "function": service_instance.calculate_order_total,
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
                "function": service_instance.get_product_prices_for_chart,
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
            },
            "find_products_within_budget": {
                "function": service_instance.find_products_within_budget,
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

    @staticmethod
    def get_user_order_tools(service_instance) -> Dict[str, Dict[str, Any]]:
        """Get user and order management tools."""
        return {
            "get_user_by_name": {
                "function": service_instance.get_user_by_name,
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
                "function": service_instance.get_user_order_history,
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

    @staticmethod
    def get_rag_tools(service_instance) -> Dict[str, Dict[str, Any]]:
        """Get policy PDF RAG tools."""
        return {
            "answer_policy_pdf": {
                "function": service_instance.answer_policy_pdf,
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

    @classmethod
    def get_all_tools(cls, service_instance) -> Dict[str, Dict[str, Any]]:
        """Get all tools merged into a single dictionary."""
        product_tools = cls.get_product_tools(service_instance)
        pricing_tools = cls.get_pricing_tools(service_instance)
        user_order_tools = cls.get_user_order_tools(service_instance)
        rag_tools = cls.get_rag_tools(service_instance)
        
        return {**product_tools, **pricing_tools, **user_order_tools, **rag_tools}

