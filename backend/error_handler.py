"""
Error handling utilities for the MongoDB chatbot service.
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Handles various error scenarios and provides user-friendly responses."""
    
    @staticmethod
    def handle_max_iterations(user_message: str, result: dict) -> str:
        """Handle cases where the agent hits max iterations limit."""
        intermediate_steps = result.get("intermediate_steps", [])
        
        # Analyze what tools were called repeatedly
        tool_calls = []
        for step in intermediate_steps:
            if isinstance(step, (tuple, list)) and len(step) == 2:
                action, observation = step
                tool_name = getattr(action, "tool", None)
                if tool_name:
                    tool_calls.append(tool_name)
        
        # Check for repeated tool calls
        if len(tool_calls) >= 3:
            last_tool = tool_calls[-1] if tool_calls else None
            
            if last_tool == "find_products_within_budget":
                return ("I apologize, but I'm having trouble finding products within your specified budget. "
                       "This might be because:\n\n"
                       "• There are no products in that price range\n"
                       "• The category filter doesn't match any existing categories\n"
                       "• The category name is incorrect\n\n"
                       "Please try:\n\n"
                       "• Increasing your budget\n"
                       "• Removing the category filter\n"
                       "• Asking me to show you available categories first\n"
                       "• Searching for specific product names instead\n"
                       "• Asking me to show you the cheapest products in a category")
            
            elif last_tool == "search_products_by_name":
                return ("I'm having trouble finding products with that name. Please try:\n\n"
                       "• Using different keywords\n"
                       "• Checking the spelling\n"
                       "• Asking me to show you all available categories\n"
                       "• Asking for products in a specific price range")
        
        # Generic fallback
        return ("I apologize, but I'm having trouble processing your request. "
               "Please try rephrasing your question or asking for something more specific. "
               "I can help you with:\n\n"
               "• Searching for products by name\n"
               "• Finding products within a budget\n"
               "• Comparing prices\n"
               "• Getting product details")
    
    @staticmethod
    def handle_semantic_matching_error(user_input: str, input_type: str) -> str:
        """Handle semantic matching errors with helpful suggestions."""
        if input_type == "category":
            return (f"I couldn't find a matching category for '{user_input}'. "
                   "Please try:\n\n"
                   "• Using different category terms\n"
                   "• Asking me to show you available categories first\n"
                   "• Searching without a category filter")
        
        elif input_type == "order":
            return (f"I couldn't understand the ordering term '{user_input}'. "
                   "Please use terms like:\n\n"
                   "• For prices: 'highest', 'cheapest', 'most expensive', 'lowest'\n"
                   "• For discounts: 'highest', 'lowest', 'most', 'least'\n"
                   "• For comparisons: 'same', 'lower', 'higher', 'cheaper', 'more expensive'")
        
        elif input_type == "comparison":
            return (f"I couldn't understand the comparison type '{user_input}'. "
                   "Please use terms like:\n\n"
                   "• 'same' or 'equal' for similar prices\n"
                   "• 'lower' or 'cheaper' for less expensive\n"
                   "• 'higher' or 'more expensive' for more expensive")
        
        return f"I couldn't understand '{user_input}'. Please try rephrasing your request."
    
    @staticmethod
    def handle_tool_execution_error(function_name: str, error: Exception) -> Dict[str, str]:
        """Handle tool execution errors."""
        logger.error(f"Tool execution error for '{function_name}': {error}")
        
        if "semantic" in function_name.lower():
            return {"error": "I'm having trouble understanding your request. Please try using different terms."}
        elif "budget" in function_name.lower():
            return {"error": "I couldn't process your budget request. Please check the amount and try again."}
        elif "category" in function_name.lower():
            return {"error": "I couldn't find products in that category. Please try a different category or search without one."}
        else:
            return {"error": f"An error occurred while processing your request: {str(error)}"}
    
    @staticmethod
    def handle_database_error(operation: str, error: Exception) -> Dict[str, str]:
        """Handle database-related errors."""
        logger.error(f"Database error during {operation}: {error}")
        
        if "connection" in str(error).lower():
            return {"error": "I'm having trouble connecting to the database. Please try again later."}
        elif "timeout" in str(error).lower():
            return {"error": "The request timed out. Please try again with a simpler query."}
        else:
            return {"error": "I encountered a database error. Please try again."}

