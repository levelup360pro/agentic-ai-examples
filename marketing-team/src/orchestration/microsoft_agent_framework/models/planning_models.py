"""Pydantic models that define planner, research and evaluation shapes.

This module declares the typed data contracts used by the planning and
research stages of the content workflow. Models are intentionally
lightweight and serializable so they can be attached to thread state
and passed between executors cleanly.
"""

from typing import List, Literal, Dict

from pydantic import BaseModel, ConfigDict, Field


class PlanningInput(BaseModel):
    """Input to the planner for a new content request.

    previous_messages is a chat history of dicts with role/content.
    """

    model_config = ConfigDict(frozen=True)

    topic: str
    brand: str
    previous_messages: List[Dict[str, str]] = Field(default_factory=list)
    planner_config: Dict[str, object] = Field(default_factory=dict)


class PlanningDecision(BaseModel):
    """Planner decision for whether to run research and which tools.

    route: "research" or "write".
    If route == "research", tools must be a subset of ["rag_search", "web_search"].
    """

    model_config = ConfigDict(frozen=True)

    route: Literal["research", "write"]
    tools: List[Literal["rag_search", "web_search"]] = Field(default_factory=list)
    reason: str
    confidence: float
    topic: str
    brand: str


class ResearchResult(BaseModel):
    """Aggregated research evidence returned from the research executor."""

    model_config = ConfigDict(frozen=True)

    topic: str
    brand: str
    tools_executed: List[str]
    evidence: Dict[str, str]
    tool_contexts: Dict[str, str]


class WritingPlan(BaseModel):
    """Prompt plan for the writer, derived from research evidence."""

    model_config = ConfigDict(frozen=True)

    topic: str
    brand: str
    draft_prompt: str
    evidence_used: Dict[str, str]
    reason: str


class EvaluationDecision(BaseModel):
    """Evaluation result with loop control decision."""

    model_config = ConfigDict(frozen=True)

    should_regenerate: bool  # True if quality below threshold and iterations remain
    should_end: bool  # True if quality met OR iterations exhausted
    meets_quality_threshold: bool
    iteration_count: int
    max_iterations: int
    topic: str
    brand: str
