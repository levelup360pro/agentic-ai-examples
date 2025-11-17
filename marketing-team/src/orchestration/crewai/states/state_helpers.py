from __future__ import annotations
import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from src.orchestration.crewai.states.content_generation_state import (
    CrewContentGenerationState,
    MessageEvent,
)
from src.core.evaluation.content_evaluator import Critique

logger = logging.getLogger(__name__)


# -------- Message logging --------

def log_tool_event(
    state: CrewContentGenerationState,
    tool_name: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Append tool execution event to state.messages.
    
    Usage after RAG tool:
        log_tool_event(state, "brand_rag", rag_output, {"chunks": 3, "cost": 0.002})
    """
    state.messages.append(MessageEvent(
        role="tool",
        name=tool_name,
        content=content,
        metadata=metadata or {}
    ))
    # Traceability
    logger.info(
        "tool_event",
        extra={
            "correlation_id": state.correlation_id,
            "brand": getattr(state, "brand", None),
            "topic": getattr(state, "topic", None),
            "tool": tool_name,
            "content_len": len(content) if content else 0,
            "metadata": metadata or {},
        },
    )

def log_ai_event(
    state: CrewContentGenerationState,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Append agent/LLM output to state.messages.
    
    Usage after generation:
        log_ai_event(state, content, {"model": "gpt-4o", "tokens": 450})
    """
    state.messages.append(MessageEvent(
        role="assistant",
        content=content,
        metadata=metadata or {}
    ))
    # Traceability
    logger.info(
        "ai_event",
        extra={
            "correlation_id": state.correlation_id,
            "brand": getattr(state, "brand", None),
            "topic": getattr(state, "topic", None),
            "content_len": len(content) if content else 0,
            "metadata": metadata or {},
        },
    )

def log_system_event(
    state: CrewContentGenerationState,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Append system instruction/event to state.messages.
    
    Usage for iteration instructions:
        log_system_event(state, "Regenerating with optimization prompt", {"iteration": 2})
    """
    state.messages.append(MessageEvent(
        role="system",
        content=content,
        metadata=metadata or {}
    ))
    # Traceability
    logger.info(
        "system_event",
        extra={
            "correlation_id": state.correlation_id,
            "brand": getattr(state, "brand", None),
            "topic": getattr(state, "topic", None),
            "content_preview": (content or "")[:200],
            "metadata": metadata or {},
        },
    )

# -------- State updates --------

def update_generation_output(
    state: CrewContentGenerationState,
    content: str,
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Update content + metadata. 
    Returns a minimal status dict for the workflow to decide next steps.
    """
    state.content = content
    state.generation_metadata = metadata or {}
    # Only add as assistant context if you want the LLM to see the draft
    log_ai_event(state, content, metadata=state.generation_metadata)
    # Traceability
    logger.info(
        "generation_updated",
        extra={
            "correlation_id": state.correlation_id,
            "brand": getattr(state, "brand", None),
            "topic": getattr(state, "topic", None),
            "content_len": len(content) if content else 0,
            "metadata": state.generation_metadata,
        },
    )
    return {"status": "generated"}

def update_evaluation_output_from_critique(
    state: CrewContentGenerationState,
    critique: Critique,
    metadata: Dict[str, Any],
    quality_threshold: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Update evaluation fields. 
    Returns {average_score, meets_threshold, scores} for the workflow to act on.
    """
    state.critique = critique
    state.evaluation_metadata = metadata or {}
    state.scores = getattr(critique, "scores", {}) or {}

    threshold = quality_threshold if quality_threshold is not None else (state.quality_threshold or 7.0)
    average_score = getattr(critique, "average_score", None)
    meets_threshold = (average_score is not None) and (float(average_score) >= float(threshold))
    reasoning = getattr(critique, "reasoning", "") or ""

    log_ai_event(
        state,
        content=f"Evaluation complete with average score {average_score}",
        metadata={"average_score": average_score, "threshold": threshold, "scores": state.scores, "reasoning": reasoning}
    )

    logger.info(
        "evaluation_complete",
        extra={
            "correlation_id": state.correlation_id,
            "brand": state.brand,
            "average_score": average_score,
            "threshold": threshold,
            "scores": state.scores,
            "reasoning": reasoning,
            "metadata": state.evaluation_metadata,
            "meets_threshold": meets_threshold,
        },
    )
    return {
        "average_score": average_score,
        "meets_threshold": meets_threshold,
        "scores": state.scores,
        "reasoning": reasoning,
        "threshold": threshold,
    }

def update_evaluation_output_from_payload(
    state: CrewContentGenerationState,
    payload: Dict[str, Any],
    quality_threshold: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Use when evaluate tool returns JSON (return_direct=True).
    """
    average_score = payload.get("average_score")
    meets_threshold = bool(payload.get("meets_threshold"))
    state.scores = payload.get("scores", {}) or {}
    state.evaluation_metadata = payload.get("metadata", {}) or {}

    threshold = quality_threshold if quality_threshold is not None else (state.quality_threshold or 7.0)
    if average_score is not None:
        meets_threshold = float(average_score) >= float(threshold)

    logger.info(
        "evaluation_complete",
        extra={
            "correlation_id": state.correlation_id,
            "brand": state.brand,
            "average_score": average_score,
            "threshold": threshold,
            "scores": state.scores,
            "metadata": state.evaluation_metadata,
            "meets_threshold": meets_threshold,
        },
    )
    return {
        "average_score": average_score,
        "meets_threshold": meets_threshold,
        "scores": state.scores,
        "threshold": threshold,
    }

# -------- Context and export --------

def get_conversation_context(state: CrewContentGenerationState) -> str:
    """
    Convert messages to text context for LLM prompts.
    """
    lines: List[str] = []
    for msg in state.messages:
        if msg.role == "tool":
            name = msg.name or "tool"
            content = msg.content or ""
            lines.append(f"[{name}]: {content}")
        elif msg.role == "assistant":
            lines.append(f"Draft: {msg.content or ''}")
        elif msg.role == "system":
            lines.append(f"System: {msg.content or ''}")
    context = "\n".join(lines)
    # Traceability (no content dump; record lengths only)
    logger.info(
        "conversation_context_built",
        extra={
            "correlation_id": state.correlation_id,
            "brand": getattr(state, "brand", None),
            "topic": getattr(state, "topic", None),
            "messages_count": len(state.messages),
            "context_len": len(context),
        },
    )
    return context

def export_state_snapshot(state: CrewContentGenerationState) -> Dict[str, Any]:
    """
    Export state as JSON-serializable dict for logging/persistence.
    """    
    snapshot = state.model_dump()
    logger.info(
        "state_snapshot_exported",
        extra={
            "correlation_id": state.correlation_id,
            "brand": getattr(state, "brand", None),
            "topic": getattr(state, "topic", None),
            "has_content": bool(getattr(state, "content", None)),
            "has_critique": bool(getattr(state, "critique", None)),
            "messages_count": len(getattr(state, "messages", []) or []),
        },
    )
    return snapshot