"""State models for the CrewAI content generation workflow.

This module defines `MessageEvent` and `CrewContentGenerationState`, the
Pydantic models used as the single source-of-truth for the Crew-based
content generation flows. Models are intentionally framework-agnostic so the
same state can be serialized and inspected outside Crew runs.
"""

from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from src.core.evaluation.content_evaluator import Critique


class MessageEvent(BaseModel):
    """
    Framework-agnostic message event for state tracing.
    
    Serializable alternative to langchain_core.messages.BaseMessage.
    Captures tool executions, agent outputs, system instructions.
    """
    role: Literal["system", "user", "assistant", "tool"]
    name: Optional[str] = None  # Tool name for role="tool"
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class CrewContentGenerationState(BaseModel):
    """
    State schema for CrewAI content generation workflow.
    
    Mirrors LangGraph ContentGenerationState structure but uses
    framework-agnostic MessageEvent instead of LangChain BaseMessage.
    
    Workflow (same as LangGraph):
        1) Content planning → decides tools (RAG, Web, both, none)
        2) Tool execution → updates rag_context/web_context + appends MessageEvent
        3) Content generation → creates content
        4) Content evaluation → sets critique, scores, meets_quality_threshold
        5) Iteration control:
             - If meets_quality_threshold OR iteration_count >= max_iterations → END
             - Else → regenerate with optimization prompt
    
    Key Differences from LangGraph:
        - messages: List[MessageEvent] (not List[BaseMessage])
          ↳ Manually appended after each task (no add_messages reducer)
        
        - No automatic state propagation between tasks
          ↳ Must explicitly update state in orchestrator after each task
        
        - Tool outputs stored in both:
          ↳ Explicit fields (rag_context, web_context) for easy access
          ↳ MessageEvent for audit trail
    """
    
    # === Core Request ===
    topic: str = Field(description="Content request/topic")
    brand: str = Field(description="Brand key (e.g., 'levelup360')")
    brand_config: Dict[str, Any] = Field(description="Full brand YAML config")
    
    # === Prompt Controls ===
    template: str = Field(description="Template key (e.g., 'LINKEDIN_POST_ZERO_SHOT')")
    use_cot: bool = Field(default=False, description="Enable Chain-of-Thought prompting")
    pattern: Optional[str] = Field(
        default=None,
        description="Generation pattern override (single_pass, reflection, evaluator_optimizer)"
    )
    
    # === Message Trail (Audit/Debug) ===
    messages: List[MessageEvent] = Field(
        default_factory=list,
        description="Conversation history + tool results for observability"
    )
    
    # === Tool Context ===
    include_rag: bool = Field(default=False, description="Whether RAG tool was used")
    include_web: bool = Field(default=False, description="Whether Web tool was used")
    query_rag: str = Field(default="", description="RAG tool query")
    query_web: str = Field(default="", description="Web tool query")
    rag_context: str = Field(default="", description="Retrieved RAG context from brand knowledge")
    web_context: str = Field(default="", description="Retrieved web search context")
    
    # === Generation Outputs ===
    content: str = Field(default="", description="Current content draft")
    generation_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Generation metadata (model, cost, latency, tokens, prompt_used)"
    )
    
    # === Evaluation Outputs ===
    critique: Optional[Critique] = Field(default=None, description="Latest evaluation result")
    evaluation_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Evaluation metadata (cost, latency, tokens)"
    )
    scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Detailed scores (brand_voice, accuracy, etc.)"
    )
    
    # === Loop Control ===
    iteration_count: int = Field(default=0, description="Number of generation→evaluation cycles")
    max_iterations: int = Field(default=3, description="Iteration limit")
    quality_threshold: float = Field(default=7.0, description="Minimum required score")
    meets_quality_threshold: bool = Field(
        default=False,
        description="Whether latest draft meets quality threshold"
    )
    
    # === Observability ===
    correlation_id: Optional[str] = Field(
        default=None,
        description="Unique ID for tracing this workflow run"
    )
    workflow_start_time: Optional[str] = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Workflow start timestamp"
    )
    workflow_end_time: Optional[str] = Field(
        default=None,
        description="Workflow end timestamp (set on completion)"
    )