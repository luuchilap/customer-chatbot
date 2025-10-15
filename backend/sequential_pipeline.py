"""
Sequential pipeline for intent routing and tool execution.
"""
import json
import logging
from typing import Dict, Any, Optional
from langchain.chains import LLMChain
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)


class SequentialPipeline:
    """Handles sequential intent routing and tool execution."""
    
    def __init__(self, llm, tools: Dict[str, Any]):
        self.llm = llm
        self.tools = tools
        self._initialized = False
        self._intent_router = None
        self._summarizer = None
    
    def _ensure_initialized(self):
        """Initialize the pipeline components if not already done."""
        if self._initialized:
            return
        
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
            llm=self.llm,
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
            llm=self.llm,
            prompt=ChatPromptTemplate.from_template(summarizer_template),
        )

        self._initialized = True
    
    def route_intent(self, user_question: str) -> Dict[str, Any]:
        """Route user question to appropriate tool."""
        self._ensure_initialized()
        
        try:
            intent_json = self._intent_router.run({
                "tool_names": "\n".join(sorted(self.tools.keys())),
                "user_question": user_question,
            }).strip()

            # Be defensive: parse JSON best-effort
            function_name = "none"
            arguments = {}
            try:
                intent_obj = json.loads(intent_json)
                function_name = str(intent_obj.get("function_name") or intent_obj.get("destination") or "none").strip()
                arguments = intent_obj.get("arguments") or intent_obj.get("next_inputs") or {}
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except Exception:
                        arguments = {"input": arguments}
            except Exception:
                # If LLM returned non-JSON, fallback to none
                function_name = "none"
                arguments = {}

            return {
                "function_name": function_name,
                "arguments": arguments
            }
        except Exception as e:
            logger.error(f"Intent routing error: {e}")
            return {
                "function_name": "none",
                "arguments": {}
            }
    
    def summarize_result(self, user_question: str, function_name: str, arguments: Dict[str, Any], tool_result: Any) -> Dict[str, str]:
        """Summarize tool result and propose follow-up."""
        self._ensure_initialized()
        
        try:
            tool_result_str = json.dumps(tool_result, ensure_ascii=False)
            arguments_str = json.dumps(arguments, ensure_ascii=False)
            
            summarizer_json = self._summarizer.run({
                "user_question": user_question,
                "function_name": function_name,
                "arguments": arguments_str,
                "tool_result": tool_result_str,
            }).strip()

            summary_answer = None
            follow_up = None
            try:
                summary_obj = json.loads(summarizer_json)
                summary_answer = summary_obj.get("answer")
                follow_up = summary_obj.get("follow_up")
            except Exception:
                # If parsing fails, just return the raw text
                summary_answer = summarizer_json

            return {
                "answer": summary_answer or "",
                "follow_up": follow_up or ""
            }
        except Exception as e:
            logger.error(f"Result summarization error: {e}")
            return {
                "answer": "I'm sorry, I encountered an error processing the result.",
                "follow_up": ""
            }

