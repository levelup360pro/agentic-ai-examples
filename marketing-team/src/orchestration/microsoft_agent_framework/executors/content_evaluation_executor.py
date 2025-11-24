"""Content evaluation executor adapters for Microsoft Agent Framework.

This module contains the thin adapter node and an `Executor` wrapper
that integrates the domain-level `ContentEvaluationAgent` with the
Microsoft Agent Framework runtime. Responsibilities of this module:

- Read and normalise inputs from the shared `ContentThreadState`.
- Append audit messages (system prompt, payload, result) to the thread
    trace so the workflow maintains a full provenance log.
- Persist evaluation results (`critique`, `evaluation_metadata`, flags)
    back onto the thread state for downstream loop control.

The heavy lifting for evaluation logic is implemented in the domain
agent (`ContentEvaluationAgent`) — the functions here are thin adapters
focused on state I/O and auditability.
"""

import logging
import json
from typing import Any, Dict

from typing import Any
from agent_framework import Executor, handler, WorkflowContext
from src.orchestration.microsoft_agent_framework.thread_states.content_thread_state import (
    ContentThreadState,
)
from src.orchestration.microsoft_agent_framework.agents.content_evaluation_agent import (
    ContentEvaluationAgent,
)
from src.orchestration.microsoft_agent_framework.models.planning_models import (
    EvaluationDecision,
)

logger = logging.getLogger(__name__)


async def content_evaluation_node(
    agent: ContentEvaluationAgent,
    thread: Any,
) -> None:
    """Workflow node that delegates content evaluation to ContentEvaluationAgent.

    Responsibilities:
      - Read normalized inputs from `ContentThreadState` (topic, brand,
        generated content, generation metadata, configs).
      - Call `ContentEvaluationAgent.run(...)`.
      - Persist `critique` and `evaluation_metadata` back to state.

    The internal evaluation behavior lives entirely inside
    `ContentEvaluationAgent`. This node should remain a thin adapter.
    """

    state = getattr(thread, "state")

    logger.info(
        f"[ContentEvaluationExecutor] ENTER | topic='{state.topic}' brand='{state.brand}' iteration={state.iteration_count}",
    )

    # Get the actual system message from brand_config
    evaluation_config = state.brand_config.get("models", {}).get("content_evaluation", {})
    actual_system_message = evaluation_config.get("system_message", "")

    # Audit: record evaluation system instruction once
    if not any(m.get("metadata", {}).get("type") == "evaluation_system" for m in state.messages):
        eval_system = {
            "role": "system",
            "name": "evaluation_system",
            "content": actual_system_message,
            "metadata": {"type": "evaluation_system"},
        }
        state.messages.append(eval_system)
    else:
        # Use the already-recorded system message
        eval_system = next(m for m in state.messages if m.get("metadata", {}).get("type") == "evaluation_system")

    # Audit: capture evaluation prompt payload
    eval_prompt_payload = {
        "system": actual_system_message,
        "inputs": {
            "topic": state.topic,
            "brand": state.brand,
            "content": state.content,
            "brand_config": state.brand_config,
            "content_type": "post",
            "quality_threshold": state.quality_threshold or 0.0,
            "iteration_count": state.iteration_count,
        },
        "previous_messages": list(state.messages),
    }
    state.messages.append(
        {
            "role": "assistant",
            "name": "evaluation_prompt",
            "content": "Evaluation prompt payload recorded",
            "metadata": {"type": "evaluation_prompt", "payload": eval_prompt_payload},
        }
    )

    # Sanitize previous_messages for the domain agent (ensure metadata values are strings)
    def _sanitize(messages):
        sanitized = []
        for m in messages:
            md = m.get("metadata") if isinstance(m, dict) else None
            if isinstance(md, dict):
                md_val = json.dumps(md)
            else:
                md_val = "" if md is None else str(md)
            entry = {
                "role": str(m.get("role", "")),
                "content": str(m.get("content", "")),
            }
            if m.get("name") is not None:
                entry["name"] = str(m.get("name"))
            entry["metadata"] = md_val
            sanitized.append(entry)
        return sanitized

    result = await agent.run(
        topic=state.topic,
        brand=state.brand,
        content=state.content,
        brand_config=state.brand_config,
        content_type="post",  # can be refined based on template/pattern
        quality_threshold=state.quality_threshold or 0.0,
        iteration_count=state.iteration_count,
        previous_messages=_sanitize(state.messages),
    )

    state.critique = result.get("critique")
    state.evaluation_metadata = result.get("evaluation_metadata", {})
    state.meets_quality_threshold = result.get("meets_quality_threshold")

    score = state.evaluation_metadata.get("score")
    threshold = state.evaluation_metadata.get("threshold")
    score_str = f"{score:.2f}" if isinstance(score, (int, float)) else "N/A"
    reasoning = getattr(state.critique, "reasoning", "") if state.critique is not None else ""

    state.messages.append(
        {
            "role": "assistant",
            "name": "content_evaluator",
            "content": (
                f"Evaluation: {score_str}/10 "
                f"(threshold={threshold})\n{reasoning}"
            ),
            "metadata": {"type": "evaluation_result"},
        },
    )

    # Node owns loop control; increment iteration here if workflow is looping
    state.iteration_count += 1

    logger.info(
        f"[ContentEvaluationExecutor] EXIT | score={score_str} meets={state.meets_quality_threshold} updates=['critique', 'evaluation_metadata', 'messages', 'iteration_count']"
    )


class ContentEvaluationExecutor(Executor):
    """Workflow executor that wraps ContentEvaluationAgent and node.

    Evaluation logic remains in the domain agent; this executor
    is the sole Agent Framework integration point for evaluation.
    """

    def __init__(self, evaluation_agent: ContentEvaluationAgent) -> None:
        super().__init__(id="content_evaluation_node")
        self.evaluation_agent = evaluation_agent

    @handler
    async def handle(self, message: Any, ctx: WorkflowContext) -> None:
        """Run evaluation and send result downstream."""
        thread = await ctx.get_shared_state("thread")
        await content_evaluation_node(self.evaluation_agent, thread)
        
        state = thread.state
        
        # Check if we're done (quality met OR iterations exhausted)
        if state.meets_quality_threshold or state.iteration_count >= state.max_iterations:
            # Workflow complete - yield final output
            await ctx.yield_output(thread)
        else:
            # Need another iteration - send message to trigger regeneration
            await ctx.send_message({"regenerate": True})
