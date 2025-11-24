"""Canonical content-generation workflow (planner → research → generate → evaluate).

This module constructs a self-contained Workflow instance for the
Microsoft Agent Framework representing the content assembly loop. It
performs the following responsibilities:

- Load and validate brand configuration for a given `brand`.
- Initialize infra (vector store, RAG helper, LLM clients, prompt
    builder, evaluator, generator) used by domain agents.
- Create domain agents and adaptors (planners, research, generation,
    evaluation) and wire them into a Workflow graph using the
    `WorkflowBuilder`.

The returned `Workflow` is ready to run by an Agent Framework runner
and yields the final `ContentThreadState` via `FinalStateExecutor`.
"""

import logging
from typing import Any, Dict

from agent_framework import Executor, WorkflowBuilder, Workflow, handler, WorkflowContext, Case, Default
from types import SimpleNamespace
from src.orchestration.microsoft_agent_framework.agents.research_agent import (
    ResearchExecutor as ResearchAgent,
)
from src.orchestration.microsoft_agent_framework.agents.content_generation_agent import (
    ContentGenerationAgent,
)
from src.orchestration.microsoft_agent_framework.agents.content_evaluation_agent import (
    ContentEvaluationAgent,
)
from src.orchestration.microsoft_agent_framework.executors.content_planning_executor import (
    ContentPlanningExecutor,
)
from src.orchestration.microsoft_agent_framework.executors.research_executor import (
    ResearchExecutor,
)
from src.orchestration.microsoft_agent_framework.executors.content_generation_executor import (
    ContentGenerationExecutor,
)
from src.orchestration.microsoft_agent_framework.executors.content_evaluation_executor import (
    ContentEvaluationExecutor,
)

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
from src.orchestration.microsoft_agent_framework.thread_states.content_thread_state import ContentThreadState

logger = logging.getLogger(__name__)


class StartExecutor(Executor):
    """Executor that initializes the shared thread state for the workflow.

    Expects an input message dict with fields needed to seed ContentThreadState.
    """

    def __init__(self) -> None:
        super().__init__(id="start_executor")

    @handler
    async def handle(self, message: Dict[str, Any],
                     ctx: WorkflowContext) -> None:
        logger.info(
            "[content_generation_workflow][StartExecutor] Initializing ContentThreadState from message"
        )

        brand = message.get("brand", "")
        topic = message.get("topic", "")
        template = message.get("template", "LINKEDIN_POST_ZERO_SHOT")
        examples = message.get("examples", "")
        use_cot = message.get("use_cot", False)
        max_iterations = message.get("max_iterations", 3)
        quality_threshold = message.get("quality_threshold", 7.0)
        pattern = message.get("pattern", "single_pass")
        brand_config = message.get("brand_config")

        thread_state = ContentThreadState(
            brand=brand,
            topic=topic,
            messages=[{
                "role": "user",
                "content": topic,
                "metadata": {
                    "type": "initial_user"
                }
            }],
            brand_config=brand_config,
            template=template,
            examples=examples,
            use_cot=use_cot,
            content="",
            critique=None,
            iteration_count=0,
            max_iterations=max_iterations,
            quality_threshold=quality_threshold,
            meets_quality_threshold=None,
            generation_metadata=None,
            evaluation_metadata=None,
            pattern=pattern,
        )

        # Store the content thread state in a lightweight namespace so executors
        # can access `.state` as before. Use the WorkflowContext API to set shared state.
        await ctx.set_shared_state("thread",
                                   SimpleNamespace(state=thread_state))
        logger.info(
            "[content_generation_workflow][StartExecutor] Thread initialized | "
            f"brand={brand}, topic={topic!r}, template={template}, "
            f"max_iterations={max_iterations}, quality_threshold={quality_threshold}, pattern={pattern}"
        )

        # Kick off the graph by sending the initial message downstream so
        # planning and subsequent executors are actually invoked.
        await ctx.send_message(message)


class FinalStateExecutor(Executor):
    """Executor that exposes the final shared thread state as a workflow output.

    This lets callers (like the routing evaluator) access ContentThreadState
    via WorkflowRunResult.get_outputs().
    """

    def __init__(self) -> None:
        super().__init__(id="final_state_executor")

    @handler
    async def handle(self, message: Dict[str, Any], ctx: WorkflowContext) -> Any:  # type: ignore[override]
        # We ignore the incoming message and simply return the current thread.
        thread = await ctx.get_shared_state("thread")
        logger.info("[content_generation_workflow][FinalStateExecutor] Yielding final thread state as workflow output")
        # Use the WorkflowContext API to yield a workflow-level output so
        # WorkflowRunResult.get_outputs() will contain the thread namespace.
        await ctx.yield_output(thread)

def build_content_generation_workflow(
    brand: str,
) -> Workflow:
    """Build a content-generation workflow: planner → research → generation → evaluation."""

    brand_config = load_brand_config(brand=brand)
    logger.info(
        "[content_generation_workflow] Loaded brand_config | "
        f"brand={brand}, models={list(brand_config.get('models', {}).keys())}, "
        f"retrieval_keys={list(brand_config.get('retrieval', {}).keys())}"
    )

    vector_store = VectorStore(persist_directory=str(CHROMA_DIR))
    logger.info("[content_generation_workflow] Initialized VectorStore | dir=%s", CHROMA_DIR)
    completion_client = LLMClient()
    completion_client.get_client("openrouter")
    logger.info("[content_generation_workflow] Initialized completion_client with provider=openrouter")

    embedding_client = LLMClient()
    embedding_client.get_client("azure")
    logger.info("[content_generation_workflow] Initialized embedding_client with provider=azure")

    rag_helper = RAGHelper(
        embedding_client=embedding_client,
        embedding_model=brand_config["models"]["vectorization"]["model"],
    )
    logger.info(
        f"[content_generation_workflow] Initialized RAGHelper | model={brand_config['models']['vectorization']['model']}"
    )

    search_client = TavilySearchClient()
    logger.info("[content_generation_workflow] Initialized TavilySearchClient")

    prompt_builder = PromptBuilder(vector_store=vector_store, rag_helper=rag_helper, search_client=search_client)
    logger.info("[content_generation_workflow] Initialized PromptBuilder")

    content_evaluator = ContentEvaluator(llm_client=completion_client)
    logger.info("[content_generation_workflow] Initialized ContentEvaluator")

    content_generator = ContentGenerator(
        llm_client=completion_client,
        prompt_builder=prompt_builder,
        content_evaluator=content_evaluator,
    )
    logger.info("[content_generation_workflow] Initialized ContentGenerator")

    # Tools
    valid_brands = [p.stem for p in CONFIG_DIR.glob("*.yaml")]
    rag_tool = create_rag_search_tool(
        vector_store=vector_store,
        rag_helper=rag_helper,
        valid_brands=valid_brands,
        collection_name="marketing_content",
        max_results=brand_config["retrieval"]["rag"]["max_results"],
        max_distance=brand_config["retrieval"]["rag"]["max_distance"],
        name="rag_search",
    )
    web_tool = create_tavily_search_tool(
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
    tools = [rag_tool, web_tool]
    expected = {"rag_search", "web_search"}
    actual = {t.name for t in tools}
    if actual != expected:
        logger.error(
            f"[content_generation_workflow] Tool name mismatch | expected={expected} actual={actual}"
        )
        raise ValueError(f"Tool name mismatch. expected={expected}, actual={actual}")
    logger.info(f"[content_generation_workflow] Tools validated | tools={sorted(actual)}")

    # Instantiate domain agents and executors
    start_executor = StartExecutor()
    logger.info("[content_generation_workflow] Instantiated StartExecutor")
    research_agent = ResearchAgent(rag_tool=rag_tool, web_tool=web_tool)
    generation_agent = ContentGenerationAgent(
        content_generator=content_generator,
        content_generation_config=brand_config["models"]["content_generation"],
    )
    evaluation_agent = ContentEvaluationAgent(
        content_evaluator=content_evaluator,
        content_evaluation_config=brand_config["models"]["content_evaluation"],
    )
    logger.info("[content_generation_workflow] Domain agents created (research, generation, evaluation)")

    planning_node_executor = ContentPlanningExecutor(
        llm_client=completion_client,
        content_planning_config=brand_config["models"]["content_planning"],
    )
    research_node_executor = ResearchExecutor(research_agent=research_agent)
    generation_node_executor = ContentGenerationExecutor(generation_agent=generation_agent)
    evaluation_node_executor = ContentEvaluationExecutor(evaluation_agent=evaluation_agent)

    final_state_executor = FinalStateExecutor()

    logger.info(
        f"[content_generation_workflow] Executors created | planning={planning_node_executor.id} research={research_node_executor.id} generation={generation_node_executor.id} evaluation={evaluation_node_executor.id} final={final_state_executor.id}"
    )

    # Build workflow graph with WorkflowBuilder
    builder = WorkflowBuilder()
    builder.set_start_executor(start_executor)

    def _is_route(message: Any, expected: str) -> bool:
        route = getattr(message, "route", None)
        logger.info(
            f"[content_generation_workflow][_is_route] message type={type(message)}, route={route}, expected={expected}, match={route == expected}"
        )
        return route == expected

    # Start → Planning
    builder.add_edge(source=start_executor, target=planning_node_executor)

    # Planning → Research/Generation using switch-case pattern
    # Planner always returns route="research" or route="write" (Literal type)
    # Default case routes to Final as a safety mechanism (should never be hit in normal operation)
    builder.add_switch_case_edge_group(
        planning_node_executor,
        [
            Case(condition=lambda message: _is_route(message, "research"), target=research_node_executor),
            Case(condition=lambda message: _is_route(message, "write"), target=generation_node_executor),
            Default(target=final_state_executor),  # Safety: terminates if planner returns unexpected route
        ],
    )

    # Research → Planning (loop back after research completes)
    builder.add_edge(source=research_node_executor, target=planning_node_executor)

    # Generation → Evaluation
    builder.add_edge(source=generation_node_executor, target=evaluation_node_executor)

    # Evaluation → Generation (loop back if regeneration needed)
    # ContentEvaluationExecutor sends message only when regeneration is needed
    builder.add_edge(source=evaluation_node_executor, target=generation_node_executor)

    # No explicit edge to Final needed - evaluation executor yields output when done

    logger.info("[content_generation_workflow] Workflow graph built; compiling Workflow instance")

    workflow = builder.build()
    logger.info(f"[content_generation_workflow] Workflow built | id={workflow.id} name={workflow.name}")

    # Debug: Log complete graph structure
    logger.info(f"[content_generation_workflow] Executors: {list(workflow.executors.keys())}")
    logger.info(f"[content_generation_workflow] Edge groups count: {len(workflow.edge_groups)}")
    for idx, eg in enumerate(workflow.edge_groups):
        logger.info(
            f"[content_generation_workflow] EdgeGroup[{idx}]: type={type(eg).__name__}, "
            f"id={getattr(eg, 'id', 'N/A')}, "
            f"edges={len(getattr(eg, 'edges', []))}"
        )
        if hasattr(eg, 'cases'):
            logger.info(f"[content_generation_workflow]   Switch-case with {len(eg.cases)} cases")
            for case_idx, case in enumerate(eg.cases):
                logger.info(
                    f"[content_generation_workflow]     Case[{case_idx}]: type={type(case).__name__}, "
                    f"target_id={getattr(case, 'target_id', 'N/A')}"
                )

    return workflow
