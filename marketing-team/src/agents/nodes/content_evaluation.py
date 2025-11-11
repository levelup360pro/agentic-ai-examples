"""Content evaluation node for agentic content workflow.

This module provides a single function, ``content_evaluation_node``, which
wraps the underlying ``ContentEvaluator`` to score a generated draft against
brand rubric criteria. It enriches state with iteration metadata and a
boolean flag indicating whether the quality threshold has been met, enabling
conditional routing (e.g. regenerate vs. finish).

Public API
        content_evaluation_node(state, content_evaluator, content_evaluation_config) -> Dict[str, Any]

Notes
        - Adds ``iteration_count`` (incremented) and ``meets_quality_threshold`` to
            the returned partial state.
        - Returns an ``AIMessage`` summarizing evaluation outcome for traceability
            inside the graph message flow.
"""

from typing import Dict, Any
import logging
from langchain_core.messages import AIMessage

from src.agents.states.content_generation_state import ContentGenerationState
from src.evaluation.content_evaluator import ContentEvaluator, Critique

logger = logging.getLogger(__name__)


def content_evaluation_node(
    state: ContentGenerationState,
    content_evaluator: ContentEvaluator,
    content_evaluation_config: dict
) -> Dict[str, Any]:
    """Evaluate the current draft and update quality/routing metadata.

    Args:
        state: Current workflow state; must contain ``draft_content`` and base
            fields (brand, brand_config, messages, template key).
        content_evaluator: Configured evaluator able to produce a ``Critique``.
        content_evaluation_config: Dict containing model params and pattern
            (e.g. {"model": str, "temperature": float, ...}).

    Returns:
        Partial state dict with keys:
            - ``critique``: Critique object (scored dimensions + reasoning)
            - ``evaluation_metadata``: Cost/latency plus scores & threshold
            - ``iteration_count``: Incremented iteration counter
            - ``meets_quality_threshold``: Bool for routing decisions
            - ``messages``: List with one AIMessage summarizing evaluation
    """
    draft = state["draft_content"]
    brand = state["brand"]
    brand_config = state["brand_config"]
    history = state.get("messages", [])
    content_type = state.get("template")  # pass template key as content_type

    # Evaluate draft content using configured pattern/model
    critique, eval_metadata = content_evaluator.evaluate_content(
        content=draft,
        brand=brand,
        brand_config=brand_config,
        content_type=content_type,
        history=history,
        model=content_evaluation_config["model"],
        pattern=content_evaluation_config["pattern"],
        max_tokens=content_evaluation_config["max_tokens"],
        temperature=content_evaluation_config["temperature"],
        system_message=content_evaluation_config["system_message"],
    )

    # Determine threshold and increment iteration
    default_threshold = 7.0
    threshold = state.get("quality_threshold") or \
        content_evaluation_config.get("quality_threshold", default_threshold)
    score = getattr(critique, "average_score", None)
    meets = (score is not None) and (float(score) >= float(threshold))

    new_iteration_count = int(state.get("iteration_count", 0)) + 1

    logger.info(
        "Evaluation: score=%s threshold=%s meets=%s iteration=%d",
        f"{score:.2f}" if isinstance(score, (int, float)) else "N/A",
        threshold,
        meets,
        new_iteration_count,
    )

    dimension_scores = getattr(critique, "scores", {})
    evaluation_metadata = {
        **eval_metadata,
        "score": score,
        "threshold": threshold,
        "dimension_scores": dimension_scores,
    }    

    # Return partial state update (LangGraph merges this into the shared state)
    return {
        "critique": critique,
        "evaluation_metadata": evaluation_metadata,
        "iteration_count": new_iteration_count,
        "meets_quality_threshold": meets,
        "messages": [
            AIMessage(
                content=(
                    f"Evaluation: {('%.2f' % score) if isinstance(score, (int, float)) else 'N/A'}/10 "
                    f"(threshold={threshold})\n{getattr(critique, 'reasoning', '')}"
                )
            )
        ],
    }