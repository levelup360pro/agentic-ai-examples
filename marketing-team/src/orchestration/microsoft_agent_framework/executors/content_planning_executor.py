import logging

from typing import Any
from agent_framework import Executor, handler, WorkflowContext

from src.infrastructure.llm.llm_client import LLMClient
from src.orchestration.microsoft_agent_framework.agents.content_planning_agent import (
    ContentPlanningAgent,
)
from src.orchestration.microsoft_agent_framework.models.planning_models import (
    PlanningInput,
    ResearchResult,
)
from src.orchestration.microsoft_agent_framework.thread_states.content_thread_state import (
    ContentThreadState,
)

logger = logging.getLogger(__name__)

async def content_planning_node(llm_client: LLMClient, content_planning_config: dict, thread: Any):
    """Planner node: produce a PlanningDecision from thread state.

    Responsibilities:
      - Read the current `ContentThreadState` from the lightweight thread
        namespace passed in via `thread`.
      - If `research_result` is present on state, convert it into a
        post-research planning pass. Otherwise perform initial planning
        based on `previous_messages` and `planner_config`.
      - Persist the resulting `PlanningDecision` and append an audit
        message describing the planner decision to `state.messages`.

    The actual LLM interaction and decision parsing happens in
    `ContentPlanningAgent`; this node marshals state into the agent's
    input shapes and writes the returned decision back into state.
    """
    state = getattr(thread, "state")
    logger.info(
        f"[ContentPlanningExecutor] ENTER | topic='{state.topic}' brand='{state.brand}'",
    )
    if state.research_result is not None:
        message = ResearchResult(**state.research_result.model_dump())
    else:
        # For auditability, include the planner system instruction in the
        # thread messages (this will be filtered by the planner when building
        # its own system message to avoid duplicates). Only add it once.
        try:
            planner_config = state.brand_config["models"]["content_planning"]
            system_msg = planner_config.get("system_message")
            if system_msg and not any(
                (m.get("metadata") and m.get("metadata").get("type") == "planner_system")
                for m in state.messages
            ):
                state.messages.insert(0, {"role": "system", "content": system_msg, "metadata": {"type": "planner_system"}})
        except Exception:
            pass

        # Sanitize previous_messages to ensure all values are strings (Pydantic expects Dict[str, str])
        import json

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

        message = PlanningInput(
            topic=state.topic,
            brand=state.brand,
            previous_messages=_sanitize(state.messages),
            planner_config=state.brand_config["models"]["content_planning"],
        )
    planner = ContentPlanningAgent(llm_client=llm_client, content_planning_config=content_planning_config)
    decision = await planner.plan(message)
    state.planning_decision = decision
    state.messages.append(
        {
            "role": "assistant",
            "content": (
                f"Planner decision: route='{decision.route}', tools={decision.tools}, "
                f"confidence={decision.confidence:.3f}."
            ),
            "metadata": {"type": "planner_decision"},
        },
    )
    logger.info(
        f"[ContentPlanningExecutor] EXIT | route='{decision.route}' tools={decision.tools} reason={decision.reason} updates=['planning_decision', 'messages']",
    )
    
    return decision

class ContentPlanningExecutor(Executor):
    """Workflow executor that wraps the pure ContentPlanningAgent and node.

    This is the only Agent Framework executor for planning; the agent remains
    a framework-agnostic domain object.
    """

    def __init__(self, llm_client: LLMClient, content_planning_config: dict) -> None:
        super().__init__(id="content_planning_node")
        self.llm_client = llm_client
        self.content_planning_config = content_planning_config

    @handler
    async def handle(self, message: Any, ctx: WorkflowContext) -> None:
        logger.info(f"[ContentPlanningExecutor] handle() called | message type={type(message)}")
        # Retrieve the lightweight thread wrapper from shared state
        thread = await ctx.get_shared_state("thread")
        result = await content_planning_node(self.llm_client, self.content_planning_config, thread)
        logger.info(
            f"[ContentPlanningExecutor] sending result | type={type(result)}, "
            f"route={getattr(result, 'route', None)}, tools={getattr(result, 'tools', None)}"
        )
        await ctx.send_message(result)
        logger.info("[ContentPlanningExecutor] ctx.send_message() completed")
        
