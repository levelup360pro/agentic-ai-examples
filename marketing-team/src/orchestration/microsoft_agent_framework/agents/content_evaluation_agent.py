"""Content evaluation executor for Microsoft Agent Framework workflows.

This module defines a thin, framework-agnostic executor that will
delegate to the shared `ContentEvaluator` used across orchestration
stacks. A separate node function is responsible for:

- Reading `ContentThreadState` from the Agent Framework thread
- Extracting topic/brand/content/metadata needed for evaluation
- Calling this executor
- Writing `critique` and `evaluation_metadata` back to state

The actual evaluation logic (how we call `ContentEvaluator` and
assemble configs) is intentionally left for manual implementation and
will be reviewed afterward for alignment with the LangGraph
`content_evaluation_node`.
"""

from __future__ import annotations

from typing import Any, Dict, List
import logging

from src.core.evaluation.content_evaluator import ContentEvaluator

logger = logging.getLogger(__name__)


class ContentEvaluationAgent:
    """Pure content evaluation executor.

    This class is responsible only for taking normalized inputs
    (topic, brand, content, metadata, configs) and delegating to
    `ContentEvaluator`. It does not know about threads or workflow
    runtime types.
    """

    def __init__(
        self,
        content_evaluator: ContentEvaluator,
        content_evaluation_config: Dict[str, Any],
    ) -> None:
        """Initialize the executor with a shared ContentEvaluator and config.

        Args:
            content_evaluator: Shared ContentEvaluator instance.
            content_evaluation_config: Base evaluation config for this brand
                (typically `brand_config["models"]["content_evaluation"]`).
        """

        self.content_evaluator = content_evaluator
        self.content_evaluation_config = content_evaluation_config

    async def run(self, topic: str, brand: str, content: str,
                  brand_config: Dict[str, Any], content_type: str,
                  quality_threshold: float, iteration_count: int,
                  previous_messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Run one evaluation pass on generated content.

        This method is intentionally scaffolded; the internal logic
        should mirror the behavior of the LangGraph
        `content_evaluation_node`, including how it:

        - Calls `ContentEvaluator` with the right configs
        - Interprets scores/critique
        - Decides whether quality threshold is met

        Returns:
            A dict containing at least `critique` and
            `evaluation_metadata`, suitable for persisting onto
            `ContentThreadState` by the calling node.
        """

        logger.info(
            f"[ContentEvaluationAgent] run called: topic='{topic}', brand='{brand}', iteration={iteration_count}"
        )

        evaluator_config = (
            brand_config.get("models", {}).get("content_evaluation")
            or self.content_evaluation_config
        )

        # Evaluate content using configured pattern/model
        critique, eval_metadata = self.content_evaluator.evaluate_content(
            content=content,
            brand=brand,
            brand_config=evaluator_config,
            content_type=content_type,
            history=previous_messages,
            model=evaluator_config["model"],
            pattern=evaluator_config["pattern"],
            max_tokens=evaluator_config["max_tokens"],
            temperature=evaluator_config["temperature"],
            system_message=evaluator_config["system_message"],
        )

        # Determine threshold
        default_threshold = 7.0
        threshold = quality_threshold or evaluator_config.get(
            "quality_threshold", default_threshold)

        score = getattr(critique, "average_score", None)
        meets_threshold = (score is not None) and (float(score)
                                                   >= float(threshold))
        score_str = f"{score:.2f}" if isinstance(score, (int, float)) else "N/A"

        logger.info(
            f"[ContentEvaluationAgent] Evaluation: score={score_str}, "
            f"threshold={threshold}, meets_threshold={meets_threshold}, iteration={iteration_count}"
        )

        dimension_scores = getattr(critique, "scores", {})
        evaluation_metadata = {
            **eval_metadata,
            "score": score,
            "threshold": threshold,
            "dimension_scores": dimension_scores,
        }

        return {
            "critique": critique,
            "evaluation_metadata": evaluation_metadata,
            "meets_quality_threshold": meets_threshold
        }
