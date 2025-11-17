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
    return Task(
        name="Run web research",
        description="If plan.include_web, call web_search(query_web) and return 'web_context' string; else empty.",
        expected_output="External Research string (or empty).",
        agent=agent,
        context=context
    )
