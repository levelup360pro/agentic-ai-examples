"""
Defines LangGraph workflow for agentic content generation:
content_planning → tools → content_generation → content_evaluation → (loop or end)
"""

from typing import Literal
import logging

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AIMessage

from src.orchestration.langgraph.states.content_generation_state import ContentGenerationState
from src.orchestration.langgraph.nodes.content_planning import content_planning_node
from src.orchestration.langgraph.nodes.content_generation import content_generation_node
from src.orchestration.langgraph.nodes.content_evaluation import content_evaluation_node

from src.shared.tools.rag_search_factory import create_rag_search_tool
from src.shared.tools.web_search_factory import create_tavily_search_tool

from src.core.rag.vector_store import VectorStore
from src.core.rag.rag_helper import RAGHelper
from src.infrastructure.llm.llm_client import LLMClient
from src.core.utils.config_loader import load_brand_config
from src.core.utils.paths import CHROMA_DIR, CONFIG_DIR
from src.infrastructure.search.tavily_client import TavilySearchClient

from src.core.generation.content_generator import ContentGenerator
from src.core.prompt.prompt_builder import PromptBuilder
from src.core.evaluation.content_evaluator import ContentEvaluator

logger = logging.getLogger(__name__)


def route_after_content_planning(state: ContentGenerationState) -> Literal["tools", "content_generation_node"]:
    """Route to tools if tool_calls present; otherwise proceed to generation."""
    messages = state.get("messages", [])
    last = messages[-1] if messages else None
    tool_calls = getattr(last, "tool_calls", None) if isinstance(last, AIMessage) else None
    if tool_calls:
        tool_names = [tc.get("name") for tc in tool_calls]
        logger.info(f"Routing to tools: {len(tool_calls)} tool(s): {tool_names}")
        return "tools"
    logger.info("No tools requested, routing to content_generation_node")
    return "content_generation_node"


def route_after_content_evaluation(state: ContentGenerationState) -> Literal["content_generation_node", "end"]:
    """
    Decide whether to loop (regenerate → re-evaluate) or end.

    Logic:
      - If meets_quality_threshold: end
      - Else if iteration_count < max_iterations: regenerate → content_generation_node
      - Else: end
    """
    meets_threshold = bool(state.get("meets_quality_threshold", False))
    iteration_count = int(state.get("iteration_count", 0))
    max_iterations = int(state.get("max_iterations", 1))

    logger.info(
        "Eval routing: meets_threshold=%s, iteration_count=%d, max_iterations=%d",
        meets_threshold, iteration_count, max_iterations
    )

    if meets_threshold:
        return "end"
    if iteration_count < max_iterations:
        logger.info("Quality not met; regenerating content (looping to content_generation_node)")
        return "content_generation_node"
    logger.info("Max iterations reached; ending")
    return "end"


def build_content_workflow(brand: str):
    """Build and compile the content workflow for a given brand."""
    # Load config and initialize infra
    brand_config = load_brand_config(brand=brand)

    vector_store = VectorStore(persist_directory=str(CHROMA_DIR))
    completion_client = LLMClient()
    completion_client.get_client("openrouter")

    embedding_client = LLMClient()
    embedding_client.get_client("azure")

    rag_helper = RAGHelper(
        embedding_client=embedding_client,
        embedding_model=brand_config["models"]["vectorization"]["model"],
    )

    search_client = TavilySearchClient()
    prompt_builder = PromptBuilder(vector_store=vector_store, rag_helper=rag_helper, search_client=search_client)
    content_evaluator = ContentEvaluator(llm_client=completion_client)
    
    content_generator = ContentGenerator(
        llm_client=completion_client,
        prompt_builder=prompt_builder,
        content_evaluator=content_evaluator,  # provided to support patterns if used
    )
    

    # Tools
    valid_brands = [p.stem for p in CONFIG_DIR.glob("*.yaml")]
    rag_search_tool = create_rag_search_tool(
        vector_store=vector_store,
        rag_helper=rag_helper,
        valid_brands=valid_brands,
        collection_name="marketing_content",
        max_results=brand_config["retrieval"]["rag"]["max_results"],
        max_distance=brand_config["retrieval"]["rag"]["max_distance"],
        name="rag_search",
    )
    web_search_tool = create_tavily_search_tool(
        search_client=search_client,
        llm_client=completion_client,
        search_depth=brand_config["retrieval"]["search"]["search_depth"],
        max_results=brand_config["retrieval"]["search"]["max_results"],
        search_type=brand_config["retrieval"]["search"]["search_type"],
        model=brand_config["models"]["search_optimization"]["model"],
        temperature=brand_config["models"]["search_optimization"]["temperature"],
        max_tokens=brand_config["models"]["search_optimization"]["max_tokens"],
        name="web_search",
    )
    tools = [rag_search_tool, web_search_tool]
    expected = {"rag_search", "web_search"}
    actual = {t.name for t in tools}
    if actual != expected:
        raise ValueError(f"Tool name mismatch. expected={expected}, actual={actual}")
    logger.info(f"Tools validated: {actual}")

    # Build graph
    workflow = StateGraph(ContentGenerationState)

    workflow.add_node(
        "content_planning_node",
        lambda state: content_planning_node(
            state=state,
            llm_client=completion_client,
            content_planning_config=brand_config["models"]["content_planning"],
            tools=tools,
        ),
    )
    workflow.add_node("tools", ToolNode(tools))

    workflow.add_node(
        "content_generation_node",
        lambda state: content_generation_node(
            state=state,
            content_generation_config=brand_config["models"]["content_generation"],
            content_generator=content_generator,
        ),
    )

    workflow.add_node(
        "content_evaluation_node",
        lambda state: content_evaluation_node(
            state=state,
            content_evaluator=content_evaluator,
            content_evaluation_config=brand_config["models"]["content_evaluation"],
        ),
    )

    # Edges
    workflow.add_edge(START, "content_planning_node")
    workflow.add_conditional_edges(
        "content_planning_node",
        route_after_content_planning,
        {"tools": "tools", "content_generation_node": "content_generation_node"},
    )
    workflow.add_edge("tools", "content_planning_node")
    workflow.add_edge("content_generation_node", "content_evaluation_node")

    # Add evaluation loop based on iteration_count and threshold
    workflow.add_conditional_edges(
        "content_evaluation_node",
        route_after_content_evaluation,
        {"content_generation_node": "content_generation_node", "end": END},
    )

    app = workflow.compile(checkpointer=MemorySaver())

    logger.info(f"Workflow compiled for brand: {brand}")
    return app