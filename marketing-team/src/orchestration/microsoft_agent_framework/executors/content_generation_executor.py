"""Content generation executor adapters for Microsoft Agent Framework.

This module provides a small adapter node and an Executor class that
bridge the domain-level `ContentGenerationAgent` with the Microsoft
Agent Framework. The node reads normalized inputs from the shared
`ContentThreadState`, records audit messages (system instructions and
prompt payloads), invokes the domain agent, and writes generated
drafts and metadata back to the thread state.

Keep this module thin: the domain agent encapsulates the LLM calls and
generation policy; this file handles state I/O and provenance only.
"""

import logging
from typing import Any, Dict

from typing import Any
from agent_framework import Executor, handler, WorkflowContext
from src.orchestration.microsoft_agent_framework.thread_states.content_thread_state import (
    ContentThreadState,
)
from src.orchestration.microsoft_agent_framework.agents.content_generation_agent import (
    ContentGenerationAgent,
)

logger = logging.getLogger(__name__)


async def content_generation_node(
    agent: ContentGenerationAgent,
    thread: Any,
) -> None:
    """Workflow node that delegates content generation to ContentGenerationAgent.

    Responsibilities:
      - Read normalized inputs from `ContentThreadState`.
      - Call `ContentGenerationAgent.run(...)`.
      - Persist `content` and `generation_metadata` back to state.

    The internal generation behavior (how configs are assembled and how
    `ContentGenerator` is called) lives entirely inside
    `ContentGenerationAgent`. This node should remain a thin adapter.
    """

    state = getattr(thread, "state")

    logger.info(
        f"[ContentGenerationExecutor] ENTER | topic='{state.topic}' brand='{state.brand}' iteration={state.iteration_count}",
    )

    tools_contexts = state.research_result.tool_contexts if state.research_result else {}

    # Determine the actual system message that will be used (same logic as ContentGenerationAgent)
    # If regenerating and below threshold, use optimization system message; otherwise use generation system message
    generation_config = state.brand_config.get("models", {}).get("content_generation", {})
    optimization_config = state.brand_config.get("models", {}).get("content_optimization", {})
    
    if state.iteration_count > 0 and not state.meets_quality_threshold:
        actual_system_message = optimization_config.get("system_message", generation_config.get("system_message", ""))
        system_type = "content_optimization_system"
    else:
        actual_system_message = generation_config.get("system_message", "")
        system_type = "content_generation_system"

    # Audit: record the actual generation system instruction once per type
    if not any(m.get("metadata", {}).get("type") == system_type for m in state.messages):
        gen_system = {
            "role": "system",
            "name": system_type,
            "content": actual_system_message,
            "metadata": {"type": system_type},
        }
        state.messages.append(gen_system)
    else:
        # Use the already-recorded system message
        gen_system = next(m for m in state.messages if m.get("metadata", {}).get("type") == system_type)

    # Audit: capture the exact prompt/payload used for generation
    gen_prompt_payload = {
        "system": actual_system_message,
        "inputs": {
            "topic": state.topic,
            "brand": state.brand,
            "brand_config": state.brand_config,
            "tool_contexts": tools_contexts,
            "template": state.template,
            "use_cot": state.use_cot,
            "iteration_count": state.iteration_count,
            "pattern": state.pattern,
        },
        "previous_messages": list(state.messages),
    }
    state.messages.append(
        {
            "role": "assistant",
            "name": "generation_prompt",
            "content": "Generation prompt payload recorded",
            "metadata": {"type": "generation_prompt", "payload": gen_prompt_payload},
        }
    )

    result = await agent.run(
        topic=state.topic,
        brand=state.brand,
        brand_config=state.brand_config,
        tool_contexts=tools_contexts,
        template=state.template,
        use_cot=state.use_cot,
        iteration_count=state.iteration_count,
        meets_quality_threshold=state.meets_quality_threshold,
        pattern=state.pattern,
    )

    state.content = result["content"]
    state.generation_metadata = result.get("generation_metadata", {})

    state.messages.append(
        {
            "role": "assistant",
            "content": state.content,
            "metadata": {
                "type": "draft",
                "iteration": state.iteration_count,
            },
        },
    )

    logger.info(
        f"[ContentGenerationExecutor] EXIT | content_len={len(state.content)} updates=['content', 'generation_metadata', 'messages']"
    )


class ContentGenerationExecutor(Executor):
    """Workflow executor that wraps ContentGenerationAgent and node.

    The agent stays framework-agnostic; this executor is the only
    Agent Framework integration point for generation.
    """

    def __init__(self, generation_agent: ContentGenerationAgent) -> None:
        super().__init__(id="content_generation_node")
        self.generation_agent = generation_agent

    @handler
    async def handle(self, message: Any, ctx: WorkflowContext) -> None:
        thread = await ctx.get_shared_state("thread")
        await content_generation_node(self.generation_agent, thread)
        # Pass the message downstream (state updates are in shared state)
        await ctx.send_message(message)
