from typing import Dict, Any
import logging
from pydantic import BaseModel
from langchain.tools import StructuredTool
from crewai import Agent, Task, Crew, Process
from crewai.flow.flow import Flow, listen, start, router
from src.orchestration.crewai.config.agents import (
    build_content_planner_agent, build_content_generator_agent,
    build_content_evaluator_agent)

from src.orchestration.crewai.config.tasks import (
    ContentGenerationPlan,
    build_content_planning_task,
    build_content_generation_task,
    build_content_evaluation_task
)

from src.orchestration.crewai.config.tools import (
    make_generate_content_tool,
    make_evaluate_content_tool
)

from src.orchestration.crewai.states.content_generation_state import CrewContentGenerationState
from src.orchestration.crewai.states.state_helpers import (
    log_tool_event,
    update_generation_output,
    update_evaluation_output_from_critique
)

from src.shared.tools.rag_search_factory import create_rag_search_tool
from src.shared.tools.web_search_factory import create_tavily_search_tool
from src.infrastructure.llm.llm_client import LLMClient
from src.core.prompt.prompt_builder import PromptBuilder
from src.core.generation.content_generator import ContentGenerator
from src.core.evaluation.content_evaluator import ContentEvaluator
from src.infrastructure.search.tavily_client import TavilySearchClient
from src.core.rag.vector_store import VectorStore
from src.core.rag.rag_helper import RAGHelper
from src.core.utils.paths import CHROMA_DIR, CONFIG_DIR
from src.core.utils.config_loader import load_brand_config

RESEARCH = "research"
GENERATE = "generate"
EVALUATE = "evaluate"

logger = logging.getLogger(__name__)

class GenerateArgs(BaseModel):
    topic: str
    brand: str
    template: str
    tool_contexts: dict
    correlation_id: str | None = None

    """Pydantic args schema for the `generate_content` structured tool.

    Attributes
        topic: The content topic or brief.
        brand: Brand key matching a YAML config in `configs/`.
        template: Template key used to select prompt templates.
        tool_contexts: A dict of pre-collected contexts (RAG/web) for generation.
        correlation_id: Optional trace id propagated through payloads.
    """

class EvaluateArgs(BaseModel):
    content: str
    brand: str
    content_type: str
    correlation_id: str | None = None

    """Pydantic args schema for the `evaluate_content` structured tool.

    Attributes
        content: The draft text to evaluate.
        brand: Brand key used for rubric/voice checks.
        content_type: Semantic type of content (e.g., 'linkedin_post').
        correlation_id: Optional trace id to correlate tool calls.
    """


class CrewContentGenerationFlow(Flow[CrewContentGenerationState]):
    """
    CrewAI orchestrator for content generation with evaluation loop.
    
    Pattern:
        1. Orchestrator creates agents/tasks dynamically
        2. Crew executes tasks sequentially
        3. Orchestrator manages state (no built-in state like LangGraph)
        4. Loop control handled by orchestrator (not Crew)
    """

    def __init__(self):
        super().__init__(name="Crew Content Generation Flow")

    @start()
    def initialize(self,
                   topic: str,
                   brand: str,
                   template: str,
                   use_cot: bool = False,
                   quality_threshold: float = 7.0,
                   max_iterations: int = 1) -> Dict[str, Any]:
        """Initialize flow runtime: build infra, agents, and tools.

        Side effects
            - Loads brand YAML via `load_brand_config` and stores in `self.brand_config`.
            - Initializes vector store, LLM clients, RAG helper, prompt builder.
            - Creates planner/generator/evaluator agents and binds StructuredTools.

        Args
            topic: Content topic to generate.
            brand: Brand config key (filename stem in `configs/`).
            template: Prompt template key to use for generation.
            use_cot: Whether to enable chain-of-thought prompting patterns.
            quality_threshold: Minimum acceptable evaluation score to stop iterating.
            max_iterations: Maximum generation→evaluation cycles.

        Returns
            A minimal mapping (usually empty) used by Crew Flow starters; primary
            state is stored on `self.state` and other instance attrs.
        """

        # Load config
        brand_config = load_brand_config(brand=brand)
        logger.info(
            "Flow initialize: brand=%s, topic=%s, template=%s, use_cot=%s, quality_threshold=%.2f, max_iterations=%d",
            brand, topic, template, use_cot, quality_threshold, max_iterations)

        # Update state
        self.state.topic = topic
        self.state.brand = brand
        self.state.brand_config = brand_config
        self.state.template = template
        self.state.use_cot = use_cot
        self.state.iteration_count = 0
        self.state.max_iterations = max_iterations
        self.state.quality_threshold = quality_threshold
        # Make brand_config available to other methods referencing self.brand_config
        self.brand_config = brand_config

        # Build infra + tools (closures capture deps/configs
        self.vector_store = VectorStore(persist_directory=str(CHROMA_DIR))
        logger.info("VectorStore initialized: dir=%s", CHROMA_DIR)

        self.completion_client = LLMClient()
        self.completion_client.get_client("openrouter")
        logger.info("Completion client configured: provider=openrouter")

        self.embedding_client = LLMClient()
        self.embedding_client.get_client("azure")
        logger.info("Embedding client configured: provider=azure")

        self.rag_helper = RAGHelper(
            embedding_client=self.embedding_client,
            embedding_model=brand_config["models"]["vectorization"]["model"],
        )
        logger.info("RAGHelper ready: embedding_model=%s",
                    brand_config["models"]["vectorization"]["model"])

        self.search_client = TavilySearchClient()
        self.prompt_builder = PromptBuilder(vector_store=self.vector_store,
                                            rag_helper=self.rag_helper,
                                            search_client=self.search_client)
        logger.info(
            "PromptBuilder initialized (vector_store, rag_helper, search_client bound)"
        )

        self.content_generator = ContentGenerator(
            llm_client=self.completion_client,
            prompt_builder=self.prompt_builder,
            content_evaluator=ContentEvaluator(
                llm_client=self.completion_client
            ),  # provided to support patterns if used
        )
        self.content_evaluator = ContentEvaluator(
            llm_client=self.completion_client)
        logger.info(
            "Content services created: generator and evaluator bound to LLM client"
        )

        # Create agents (created once, reused)
        self.planner_agent = build_content_planner_agent(brand_config)
        self.generator_agent = build_content_generator_agent(brand_config)
        self.evaluator_agent = build_content_evaluator_agent(brand_config)
        logger.info("Agents created: planner=%s, generator=%s, evaluator=%s",
                    type(self.planner_agent).__name__,
                    type(self.generator_agent).__name__,
                    type(self.evaluator_agent).__name__)

        # Create Tools
        valid_brands = [p.stem for p in CONFIG_DIR.glob("*.yaml")]

        self.rag_search_tool = create_rag_search_tool(
            vector_store=self.vector_store,
            rag_helper=self.rag_helper,
            valid_brands=valid_brands,
            collection_name="marketing_content",
            max_results=brand_config["retrieval"]["rag"]["max_results"],
            max_distance=brand_config["retrieval"]["rag"]["max_distance"],
            name="rag_search",
        )
        logger.info(
            "RAG tool configured: collection=%s, max_results=%s, max_distance=%s, valid_brands=%d",
            "marketing_content",
            brand_config["retrieval"]["rag"]["max_results"],
            brand_config["retrieval"]["rag"]["max_distance"],
            len(valid_brands))

        self.web_search_tool = create_tavily_search_tool(
            search_client=self.search_client,
            llm_client=self.completion_client,
            search_depth=brand_config["retrieval"]["search"]["search_depth"],
            max_results=brand_config["retrieval"]["search"]["max_results"],
            search_type=brand_config["retrieval"]["search"]["search_type"],
            model=brand_config["models"]["search_optimization"]["model"],
            temperature=brand_config["models"]["search_optimization"]
            ["temperature"],
            max_tokens=brand_config["models"]["search_optimization"]
            ["max_tokens"],
            name="web_search",
        )
        logger.info(
            "Web search tool configured: depth=%s, max_results=%s, type=%s, model=%s",
            brand_config["retrieval"]["search"]["search_depth"],
            brand_config["retrieval"]["search"]["max_results"],
            brand_config["retrieval"]["search"]["search_type"],
            brand_config["models"]["search_optimization"]["model"])

        self.generate_tool = StructuredTool.from_function(
            name="generate_content",
            description="Create brand-aligned content from provided contexts.",
            func=make_generate_content_tool(
                content_generator=self.content_generator,
                brand_config=brand_config,
                generation_config=brand_config["models"]
                ["content_generation"]),
            args_schema=GenerateArgs,
            return_diret=True)

        self.evaluate_tool = StructuredTool.from_function(
            name="evaluate_content",
            description="Evaluate content and return a Dict.",
            func=make_evaluate_content_tool(
                content_evaluator=self.content_evaluator,
                brand_config=brand_config,
                evaluation_config=brand_config["models"]
                ["content_evaluation"]),
            args_schema=EvaluateArgs,
            return_diret=True)
        logger.info(
            "Structured tools bound: generate_content, evaluate_content")

        # Bind tools to agents
        self.generator_agent.tools = [self.generate_tool]
        self.evaluator_agent.tools = [self.evaluate_tool]
        logger.info(
            "Tools assigned: generator->generate_content, evaluator->evaluate_content"
        )

    # === Step Methods ===

    @listen(initialize)
    def run_planning(self, agent: Agent):
        """Execute the planning Task to decide which research tools to use.

        This method constructs a `planning_task` using `build_content_planning_task`
        and runs it via a one-agent `Crew`. The Task must return a
        `ContentGenerationPlan` (Pydantic) which is then stored on `self.state`.

        Side effects
            - sets `self.state.include_rag`, `self.state.include_web`
            - sets `self.state.query_rag` and `self.state.query_web`

        Args
            agent: The planner Agent used to produce the research decision.
        """
        logger.info("Planning start: topic=%s, brand=%s, agent=%s",
                    self.state.topic, self.state.brand,
                    type(agent).__name__)
        planning_task = build_content_planning_task(topic=self.state.topic,
                                                    brand=self.state.brand,
                                                    agent=agent)

        crew = Crew(agents=[agent],
                    tasks=[planning_task],
                    process=Process.sequential,
                    verbose=True)

        result = crew.kickoff()
        logger.info("Planning finished: crew result type=%s",
                    type(result).__name__)

        plan: ContentGenerationPlan = planning_task.output.pydantic
        self.state.include_rag = plan.include_rag
        self.state.include_web = plan.include_web
        self.state.query_rag = plan.query_rag or self.state.topic
        self.state.query_web = plan.query_web or self.state.topic

        logger.info("Planning decision: include_rag=%s, include_web=%s",
                    plan.include_rag, plan.include_web)

    @router(run_planning)
    def route_after_content_planning(self) -> str:
        """Router that returns the next step name based on planning decisions.

        Returns
            - `RESEARCH` if plan requested RAG or Web research
            - `GENERATE` otherwise (skip research and proceed to content generation)
        """
        if self.state.include_rag or self.state.include_web:
            logger.info(
                "Router: proceeding to RESEARCH (include_rag=%s, include_web=%s)",
                self.state.include_rag, self.state.include_web)
            return RESEARCH
        else:
            logger.info("Router: skipping research -> GENERATE")
            return GENERATE

    @listen(RESEARCH)
    def _run_research(self) -> str:
        """Run configured research tools (RAG and/or Web) and append results to state.

        Behavior
            - If `self.state.include_rag` is True, calls `self.rag_search_tool` and
              stores the result in `self.state.rag_context` and appends a tool
              `MessageEvent` via `log_tool_event`.
            - If `self.state.include_web` is True, similarly calls `self.web_search_tool`.

        Returns
            - `GENERATE` after research completes to continue the flow.
        """
        logger.info("Research start: include_rag=%s, include_web=%s",
                    self.state.include_rag, self.state.include_web)
        if self.state.include_rag:
            rag_result = self.rag_search_tool(
                self.state.query_rag if self.state.query_rag else
                self.state.topic, self.state.brand)
            self.state.rag_context = rag_result
            log_tool_event(
                self.state, "rag_search", rag_result, {
                    "rag_query": self.state.query_rag,
                    "topic": self.state.topic,
                    "brand": self.state.brand
                })
            logger.info("RAG tool result: %s", rag_result[:500])

        if self.state.include_web:
            web_result = self.web_search_tool(
                self.state.query_web if self.state.query_web else self.state.
                topic)
            self.state.web_context = web_result
            log_tool_event(
                self.state, "web_search", web_result, {
                    "web_query": self.state.query_web,
                    "topic": self.state.topic,
                    "brand": self.state.brand
                })
            logger.info("Web search tool result: %s", web_result[:500])

        logger.info(
            "Research complete. RAG ctx present=%s, Web ctx present=%s",
            self.state.rag_context is not None, self.state.web_context
            is not None)
        return GENERATE

    @listen(GENERATE)
    def run_content_generation(self) -> str:
        """Perform content generation and immediate evaluation, updating flow state.

        Steps
              1. Selects appropriate `system_template` on the generator agent
                  depending on whether this is an initial draft or an optimization pass.
              2. Builds `generation_task` and `evaluation_task` and runs them via a
                  two-agent sequential `Crew` (generator then evaluator).
              3. Writes generated draft into `self.state.content` and appends an
                  assistant `MessageEvent` via `update_generation_output`.
              4. Updates evaluation outputs via `update_evaluation_output_from_critique`.
              5. Decides whether to iterate (return `GENERATE`) or stop based on
                  `meets_threshold` and `max_iterations`.

        Returns
              - `GENERATE` to request another optimization iteration when needed
              - otherwise implicitly falls through (end of flow).
        """

        if self.state.iteration_count == 0:
            self.generator_agent.system_template = self.brand_config["models"][
                "content_generation"]["system_message"]
            logger.info(
                "Generation mode=initial; system_template=content_generation")
        else:
            self.generator_agent.system_template = self.brand_config["models"][
                "content_optimization"]["system_message"]
            logger.info(
                "Generation mode=optimization; system_template=content_optimization; iteration=%d",
                self.state.iteration_count)

        generation_task = build_content_generation_task(
            agent=self.generator_agent,
            topic=self.state.topic,
            brand=self.state.brand,
            template=self.state.template,
            rag_context=self.state.rag_context,
            web_context=self.state.web_context)

        evaluation_task = build_content_evaluation_task(
            agent=self.evaluator_agent,
            brand=self.state.brand,
            draft_content=self.state.content,
            quality_threshold=self.state.quality_threshold)
        logger.info(
            "Tasks prepared: generation + evaluation; quality_threshold=%.2f",
            self.state.quality_threshold)

        crew = Crew(agents=[self.generator_agent, self.evaluator_agent],
                    tasks=[generation_task, evaluation_task],
                    process=Process.sequential,
                    verbose=True)

        result = crew.kickoff()
        logger.info("Generation+Evaluation crew finished: result type=%s",
                    type(result).__name__)

        content = generation_task.output.raw
        logger.info("Generated content length=%s",
                    len(content) if content else 0)
        update_generation_output(self.state,
                                 content=content,
                                 metadata={
                                     "agent": "generator",
                                     "iteration": 0,
                                     "mode": "initial"
                                 })

        critique = evaluation_task.output.pydantic
        evaluation_output = update_evaluation_output_from_critique(
            self.state,
            critique=critique,
            metadata={
                "iteration":
                self.state.iteration_count,
                "mode":
                "initial"
                if self.state.iteration_count == 0 else "optimization"
            })
        logger.info("Evaluation: meets_threshold=%s, overall_score=%s",
                    evaluation_output.get("meets_threshold"),
                    getattr(critique, "overall_score", None))

        if (self.state.iteration_count < self.state.max_iterations -
                1) and (not evaluation_output["meets_threshold"]):
            logger.info("Decision: iterate again (iteration=%d < max=%d)",
                        self.state.iteration_count, self.state.max_iterations)
            return GENERATE  # Optimize
            return GENERATE  # Optimize
