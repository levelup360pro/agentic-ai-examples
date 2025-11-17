"""
Content generation node: Creates/updates content using tool results.
Applies optimization system message on regeneration after evaluation.
"""

from typing import Dict, Any
import logging
from copy import deepcopy
from langchain_core.messages import AIMessage, ToolMessage

from src.orchestration.langgraph.states.content_generation_state import ContentGenerationState
from src.core.generation.content_generator import ContentGenerator

logger = logging.getLogger(__name__)


def content_generation_node(
    state: ContentGenerationState,
    content_generation_config: dict,  # brand_config["models"]["content_generation"]
    content_generator: ContentGenerator
) -> Dict[str, Any]:
    """
    Generate content using tool results from state (agentic path).
    If this is a regeneration (iteration_count > 0) and previous evaluation
    did not meet the threshold, override the system message with the
    content_optimization.system_message.

    Args:
        state: Current workflow state with topic, brand, tool results
        content_generation_config: Base model/temp/max_tokens/system_message for generation
        content_generator: ContentGenerator instance (framework-agnostic)

    Returns:
        Partial state update:
            {
              "content": str,
              "generation_metadata": dict,
              "messages": [AIMessage]
            }
    """
    # Extract tool contexts from ToolMessages (agentic context; may be empty)
    tool_contexts: Dict[str, str] = {}
    for msg in state.get("messages", []):
        if isinstance(msg, ToolMessage):
            tool_contexts[msg.name] = msg.content

    logger.info("Found %d tool results for generation", len(tool_contexts))

    # Determine if we should use optimization system message on this turn
    iteration_count = int(state.get("iteration_count", 0))
    meets_quality_threshold = bool(state.get("meets_quality_threshold", False))
    brand_config = state["brand_config"]

    # Make a local effective config we can override safely
    effective_generation_config = deepcopy(content_generation_config)

    # If we're in a regeneration loop and last evaluation did not meet threshold,
    # use the optimization system message for this generation turn.
    if iteration_count > 0 and not meets_quality_threshold:
        optimization_model_config = brand_config.get("models", {}).get("content_optimization", {})
        optimization_system_message = optimization_model_config.get("system_message")
        if optimization_system_message:
            logger.info("Using optimization system message for regeneration turn")
            effective_generation_config["system_message"] = optimization_system_message

    # Always single-pass here (loop is handled by evaluation node)
    requested_pattern = state.get("pattern")
    if requested_pattern and requested_pattern != "single_pass":
        logger.warning("Agentic path ignores pattern=%s; using single_pass", requested_pattern)
    pattern = "single_pass"

    # This node performs exactly one generation pass per cycle
    max_iterations = 1

    # Pass full optimization model config so evaluator-optimizer internal loop can use it if pattern demands
    optimization_config = brand_config.get("models", {}).get("content_optimization", {})

    # Call ContentGenerator (agentic path; unified return shape)
    result = content_generator.generate_from_context(
        topic=state["topic"],
        brand=state["brand"],
        brand_config=brand_config,
        tool_contexts=tool_contexts,
        template=state["template"],                 # string key; generator resolves to template object
        use_cot=state.get("use_cot", False),
        pattern=pattern,
        max_iterations=max_iterations,
        generation_config=effective_generation_config,  # may include optimization system message override
        optimization_config=optimization_config,        # used for evaluator-optimizer internal loop
    )

    content = result["content"]
    generation_metadata = result.get("metadata", {})

    logger.info(
        "Generated content (length: %d chars) pattern='%s' iteration=%d",
        len(content), pattern, iteration_count
    )

    # Return state update
    return {
        "content": content,
        "generation_metadata": generation_metadata,
        "messages": [AIMessage(content=content)],
    }