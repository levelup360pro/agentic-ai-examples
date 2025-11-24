"""CrewAI Task builders used by the Crew orchestration flow.

Provides small factory functions that return pre-configured `crewai.Task`
objects for planning, generation, evaluation and search steps. These
helpers encapsulate expected outputs and descriptions so agents can be
reused across flows.

Public API
    - ContentGenerationPlan (Pydantic model)
    - build_content_planning_task(...)
    - build_content_generation_task(...)
    - build_content_evaluation_task(...)
    - build_content_optimization_task(...)
    - build_rag_search_task(...)
    - build_web_search_task(...)
"""

from typing import List
from crewai import Task, Agent
import logging
from pydantic import BaseModel, Field


class ContentGenerationPlan(BaseModel):
    include_rag: bool = Field(...)
    include_web: bool = Field(...)
    query_rag: str = ""
    query_web: str = ""
    notes: str = ""

logger = logging.getLogger(__name__)


def build_content_planning_task(
    topic: str,
    brand: str,
    agent: Agent,
) -> Task:
    """Build a planning Task that expects strict JSON describing tool decisions.

    The Task enforces a Pydantic output shape (`ContentGenerationPlan`) so downstream
    code can read decisions reliably.

    Args
        topic: The content topic for which planning occurs.
        brand: Brand key used for instructions and constraints.
        agent: The planner `crewai.Agent` that will execute the Task.

    Returns
        A configured `crewai.Task` that will output a `ContentGenerationPlan`.
    """
    return Task(
        name="Plan research",
        description=(
            f"Plan research for brand {brand} on topic: {topic}. "
            "Return STRICT JSON: "
            "{\"include_rag\": boolean, \"include_web\": boolean, "
            "\"query_rag\": string, \"query_web\": string, \"notes\": string}. "
            "Do not call tools."),
        expected_output="Strict JSON with exactly those keys.",
        agent=agent,
        output_pydantic=ContentGenerationPlan)

def build_content_generation_task(
    agent: Agent,
    context: List[Task],
) -> Task:
    """Return a Task that instructs the generator Agent to compose a draft.

    Args
        agent: The generator `crewai.Agent`.
        context: List of prior `Task` objects providing context (planning, research).

    Returns
        A `crewai.Task` configured to produce a content string.
    """
    return Task(
        name="Generate content",
        description="Compose content using provided contexts (no tool calls beyond compose_draft).",
        expected_output="Content string.",
        agent=agent,
        context=context,
    )

def build_content_evaluation_task(
    agent: Agent,
    context: List[Task],
) -> Task:
    """Return a Task that evaluates a draft using the evaluator Agent.

    The evaluator Task is expected to call `evaluate_content` (structured tool)
    and return a JSON payload describing scores, reasoning and violations.
    """
    return Task(
        name="Evaluate content",
        description="Call evaluate_content and do not add any prose; the tool’s output is the final answer.",
        agent=agent,
        context=context,
        expected_output="JSON: {average_score: float, meets_threshold: bool, reasoning: str, violations: list[str], scores: dict, metadata: dict}.",
    )

def build_content_optimization_task(
    agent: Agent,
    context: List[Task],
) -> Task:
    """Return a Task for optimization/regeneration using the optimization system_message."""
    return Task(
        name="Optimize content",
        description="Compose content using provided contexts (no tool calls beyond generate_content).",
        expected_output="Content string.",
        agent=agent,
        context=context,
    )

def build_rag_search_task(
    agent: Agent,
    brand: str,
    context: List[Task]
) -> Task:
    """Return a Task that runs internal RAG retrieval for the given brand."""
    return Task(
        name="Run internal RAG",
        description=f"If plan.include_rag, call rag_search(query_rag, {brand}) and return 'rag_context' string; else empty.",
        expected_output="Internal Brand Context string (or empty).",
        agent=agent,
        context=context
    )

def build_web_search_task(
    agent: Agent,
    context: List[Task]
) -> Task:
    """Return a Task that performs external web research when requested by plan."""
    return Task(
        name="Run web research",
        description="If plan.include_web, call web_search(query_web) and return 'web_context' string; else empty.",
        expected_output="External Research string (or empty).",
        agent=agent,
        context=context
    )
