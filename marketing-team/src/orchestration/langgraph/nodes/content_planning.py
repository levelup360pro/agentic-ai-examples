"""Content planning node for agentic content-generation workflow.

This module contains a single entry point that asks an LLM to decide which
data-acquisition tools (internal RAG search, external web search, etc.) are
needed for a specific content request before drafting begins. It keeps the
decision logic minimal and returns the raw LLM AIMessage (including any
``tool_calls``) so an orchestration layer (e.g. LangGraph) can execute those
tools next.

Public API
    content_planning_node(state, llm_client, content_planning_config, tools) -> Dict[str, Any]

Notes
    - Requires a configured ``LLMClient`` supporting tool calling.
    - This module does not execute tools; it only produces a decision message.
    - Keeps prior conversation messages (excluding initial system) to provide
      continuity for multi-turn planning.
"""

from typing import Dict, Any, List
import logging
from urllib import response
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool

from src.infrastructure.llm.llm_client import LLMClient
from src.orchestration.langgraph.states.content_generation_state import ContentGenerationState

logger = logging.getLogger(__name__)


def content_planning_node(
        state: ContentGenerationState,
        llm_client: LLMClient,
        content_planning_config: dict,
        tools: List  # List of LangChain tool objects
) -> Dict[str, Any]:
    """
    Analyze the requested topic and decide which enrichment tools to call.
    
    Args:
        state: Current workflow state with topic, brand, messages
        llm_client: LLM client for tool calling
        tools: List of available tools (rag_search, web_search)
    
    Returns:
    Dict with updated messages (single AIMessage possibly containing ``tool_calls``)
    
    Flow:
        1. Build context from state (topic, brand, previous messages)
        2. Create system message with content planning node prompt
        3. Call LLM with tool calling enabled
    4. Return AIMessage (contains ``tool_calls`` when tool usage is required)
    """

    context = {
        "topic": state["topic"],
        "brand": state["brand"],
        "messages": state["messages"]    }

    # Base system instruction defining planner role
    system_message = content_planning_config["system_message"]
    # User prompt asking for tool selection decision
    user_message = (
        f"Content request: {context['topic']}\n"
        f"Brand: {context['brand']}\n"
        "Decide which (if any) tools to call to gather information for content creation."
    )

    messages = [
        SystemMessage(content=system_message),
        HumanMessage(content=user_message)
    ]

    # Preserve previous assistant/user messages (skip original system message)
    if len(context["messages"]) > 1:
        messages.extend(context["messages"][1:])

    # Invoke LLM with tool calling enabled
    result = llm_client.get_completion(
        model=content_planning_config["model"],
        temperature=content_planning_config["temperature"],
        max_tokens=content_planning_config["max_tokens"],
        messages=messages,
        tool_support=True,
        tools=tools,
    )

    logger.info(f"Content planning node decision: {len(result.tool_calls) if result.tool_calls else 0} tool(s) to call")

    if result.tool_calls:
        for tool_call in result.tool_calls:
            logger.info("  - %s with args: %s", tool_call['name'], tool_call['args'])
    else:
        logger.info("  - No tools needed; proceeding directly to generation")

    # Return raw_response (AIMessage) for downstream graph execution
    return {"messages": [result.raw_response]}


