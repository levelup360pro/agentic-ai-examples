"""Thread state models for Microsoft Agent Framework content workflows.

ContentThreadState mirrors the LangGraph `ContentGenerationState` schema,
but is designed to be attached to a Microsoft Agent Framework thread as
typed state. Agents (planner, research, writer, evaluator) can read and
update this shared state instead of passing individual fields through
every call.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, ConfigDict

from src.core.evaluation.content_evaluator import Critique
from src.orchestration.microsoft_agent_framework.models.planning_models import (
    PlanningDecision,
    ResearchResult,
)


class ContentThreadState(BaseModel):
    """Unified thread state for content planning → tools → generation → evaluation.

    This is the Microsoft Agent Framework analogue of the LangGraph
    `ContentGenerationState` TypedDict. It is intended to be attached to
    a workflow thread and mutated by agents as they progress through the
    loop.
    """

    model_config = ConfigDict(frozen=False)

    # Core request and brand
    topic: str
    brand: str
    brand_config: Dict[str, Any]

    # Optional chat history (LLM-style messages: role/content/extra)
    messages: List[Dict[str, Any]] = Field(default_factory=list)

    # Prompt/generation controls
    template: str
    examples: Optional[List[str]] = Field(default_factory=list)
    use_cot: bool = False

    # Generated content (latest draft)
    content: Optional[str] = None

    # Planner artefacts
    planning_decision: Optional[PlanningDecision] = None
    research_result: Optional[ResearchResult] = None

    # Latest evaluation result
    critique: Optional[Critique] = None

    # Loop controls
    iteration_count: int = 0
    max_iterations: int = 1
    quality_threshold: Optional[float] = None
    meets_quality_threshold: Optional[bool] = None

    # Optional metadata from nodes
    generation_metadata: Optional[Dict[str, Any]] = None
    evaluation_metadata: Optional[Dict[str, Any]] = None

    # Optional pattern override
    pattern: Optional[str] = None
