"""
Conversation management utilities for the MongoDB chatbot service.
"""
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from bson.json_util import dumps as bson_dumps

logger = logging.getLogger(__name__)


class ConversationManager:
    """Manages conversation history and customer inquiries."""
    
    def __init__(self, db):
        self.db = db
        self.conversations: Dict[str, Dict[str, Any]] = {}
    
    def get_conversation_history(self, session_id: str) -> List[Dict]:
        """Get conversation history for a session."""
        if session_id not in self.conversations:
            self.conversations[session_id] = {"history": [], "last_conversation_subject": None}
        return self.conversations[session_id]["history"]
    
    def update_conversation_subject(self, session_id: str, function_result: Any, name_field: str):
        """Update the last conversation subject based on function result."""
        if isinstance(function_result, dict):
            if name_field in function_result:
                self.conversations[session_id]["last_conversation_subject"] = function_result.get(name_field)
            elif "reference_product" in function_result and "name" in function_result["reference_product"]:
                self.conversations[session_id]["last_conversation_subject"] = function_result["reference_product"].get("name")
        elif isinstance(function_result, list) and len(function_result) == 1 and name_field in function_result[0]:
            self.conversations[session_id]["last_conversation_subject"] = function_result[0].get(name_field)
    
    def add_customer_inquiry(self, customer_name: str, inquiry: str, response: str, session_id: str = "default"):
        """Add a customer inquiry to the database."""
        inquiry_doc = {
            "customer_name": customer_name,
            "inquiry": inquiry,
            "response": response,
            "session_id": session_id,
            "timestamp": datetime.utcnow()
        }
        self.db.customer_inquiries.insert_one(inquiry_doc)
    
    def add_to_history(self, session_id: str, user_message: str, assistant_message: str, max_history: int = 20):
        """Add messages to conversation history."""
        conversation_history = self.get_conversation_history(session_id)
        conversation_history.append({"role": "user", "content": user_message})
        conversation_history.append({"role": "assistant", "content": assistant_message})
        
        if len(conversation_history) > max_history:
            self.conversations[session_id]["history"] = conversation_history[-max_history:]
    
    def reset_conversation(self, session_id: str = "default"):
        """Reset conversation history for a session."""
        if session_id in self.conversations:
            del self.conversations[session_id]
    
    def to_jsonable(self, value):
        """Best-effort conversion of Mongo/complex values to JSON-safe Python types."""
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
    
    def build_reasoning_trace(self, intermediate_steps) -> List[Dict]:
        """Convert LangChain intermediate steps to a simple serializable trace."""
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
                tool_input = self.to_jsonable(tool_input)
                observation = self.to_jsonable(observation)

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

