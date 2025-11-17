from typing import Dict, Any, Optional, List, Callable
import logging

from src.core.generation.content_generator import ContentGenerator
from src.core.evaluation.content_evaluator import ContentEvaluator
from src.shared.serialization.generation import generation_to_payload
from src.shared.serialization.evaluation import critique_to_payload

logger = logging.getLogger(__name__)

def make_generate_content_tool(
    generator: ContentGenerator,
    brand_config: dict,
    generation_config: dict,
    max_iterations: int = 1,
    use_cot: bool = False
) -> Callable:
    """
    CrewAI-ready callable. Single-pass generation. Never raises; returns JSON payload.
    """
    def generate_content(
        topic: str,
        brand: str,
        template: str,
        tool_contexts: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            result = generator.generate_from_context(
                topic=topic,
                brand=brand,
                brand_config=brand_config,
                tool_contexts=tool_contexts,
                template=template,
                use_cot=use_cot,
                pattern="single_pass",
                max_iterations=max_iterations,
                generation_config=generation_config,
            )
            payload = generation_to_payload(result, correlation_id=correlation_id)
            return payload
        except Exception as e:
            logger.exception("generate_content failed")
            return {
                "content": "",
                "metadata": {"correlation_id": correlation_id} if correlation_id else {},
                "error": str(e),
            }
    return generate_content


def make_evaluate_content_tool(
    evaluator: ContentEvaluator,
    brand_config: dict,
    evaluation_config: dict,
    history: Optional[List[Dict[str, Any]]] = None,
    include_weights: bool = False
) -> Callable:
    """
    CrewAI-ready callable. Evaluates and returns detailed JSON (dims + overall).
    Uses evaluation_config['quality_threshold'] or falls back to 7.0.
    Never raises.
    """
    def evaluate_content(
        content: str,
        brand: str,
        content_type: str,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            critique, metadata = evaluator.evaluate_content(
                content=content,
                brand=brand,
                brand_config=brand_config,
                content_type=content_type,
                history=history,
                model=evaluation_config["model"],
                max_tokens=evaluation_config["max_tokens"],
                temperature=evaluation_config["temperature"],
                system_message=evaluation_config["system_message"],
                pattern="evaluator_optimizer",
            )
            threshold = (
                evaluation_config.get("quality_threshold")
                or evaluation_config.get("threshold")
                or 7.0
            )
            payload = critique_to_payload(
                critique,
                threshold=threshold,
                include_weights=include_weights,
            )
            payload["metadata"] = (metadata or {})
            if correlation_id:
                payload["metadata"]["correlation_id"] = correlation_id
            return payload
        except Exception as e:
            logger.exception("evaluate_content failed")
            return {
                "score": None,
                "meets_threshold": False,
                "reasoning": "",
                "violations": [],
                "dimensions": {},
                "metadata": {"correlation_id": correlation_id} if correlation_id else {},
                "error": str(e),
            }
    return evaluate_content