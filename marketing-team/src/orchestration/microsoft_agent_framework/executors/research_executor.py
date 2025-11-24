"""Research executor adapter for Microsoft Agent Framework workflows.

This module exposes an `Executor` which reads the planner decision from
the shared `ContentThreadState`, executes the requested research tools
via the pure-domain `ResearchExecutor` (RAG/web search), records audit
entries in the thread trace, and returns a `ResearchResult` downstream.

The underlying `ResearchExecutor` is framework-agnostic; this wrapper
manages state I/O and message provenance only.
"""

import logging
from typing import List

from typing import Any
from agent_framework import Executor, handler, WorkflowContext

from src.orchestration.microsoft_agent_framework.thread_states.content_thread_state import (
    ContentThreadState,
)
from src.orchestration.microsoft_agent_framework.agents.research_agent import (
    ResearchExecutor as ResearchAgent,
)

logger = logging.getLogger(__name__)


class ResearchExecutor(Executor):
    """Workflow executor that wraps the pure ResearchAgent.

    Orchestration logic (reading/writing ContentThreadState) lives directly
    on this executor; the underlying research agent remains framework-agnostic.
    """

    def __init__(self, research_agent: ResearchAgent) -> None:
        super().__init__(id="research")
        self.research_agent = research_agent

    @handler
    async def handle(self, message: Any, ctx: WorkflowContext) -> None:
        thread = await ctx.get_shared_state("thread")
        state = getattr(thread, "state")
        
        tools_requested = state.planning_decision.tools if state.planning_decision else []
        logger.info(
            f"[ResearchExecutor] ENTER | topic='{state.topic}' brand='{state.brand}' tools={tools_requested}"
        )

        if state.planning_decision is None:
            logger.warning(
                "[ResearchExecutor] called without planning_decision; skipping research",
            )
            return await ctx.send_message(None)

        tools: List[str] = state.planning_decision.tools
        if not tools:
            logger.info(
                "[ResearchExecutor] no tools requested in planning_decision; skipping research",
            )
            return await ctx.send_message(None)

        # Audit: record the system instruction used for research once
        if not any(
                m.get("metadata", {}).get("type") == "research_system"
                for m in state.messages):
            system_msg = {
                "role":
                "system",
                "name":
                "research_system",
                "content":
                ("You are a research assistant. Use the requested tools to gather and summarize evidence, "
                 "returning concise findings, sources, and a short evidence summary suitable for content generation."
                 ),
                "metadata": {
                    "type": "research_system"
                },
            }
            state.messages.append(system_msg)

        # Audit: capture the exact prompt/payload sent to the research agent
        prompt_payload = {
            "system": system_msg["content"],
            "inputs": {
                "topic": state.topic,
                "brand": state.brand,
                "tools": tools
            },
            "previous_messages": list(state.messages),
        }
        state.messages.append({
            "role": "assistant",
            "name": "research_prompt",
            "content": "Research prompt payload recorded",
            "metadata": {
                "type": "research_prompt",
                "payload": prompt_payload
            },
        })

        result = await self.research_agent.run(
            topic=state.topic,
            brand=state.brand,
            tools=tools,
        )

        state.research_result = result
        
        # Format evidence dict as a readable string for message content
        evidence_summary = " | ".join([f"{k}: {v}" for k, v in result.evidence.items()]) if result.evidence else "No evidence gathered"
        
        state.messages.append(
            {
                "role":
                "tool",
                "name":
                "research_executor",
                "content":
                (f"Executed tools={result.tools_executed} for topic='{result.topic}', "
                 f"brand='{result.brand}'. Evidence: {evidence_summary}"
                 ),
                "metadata": {
                    "type": "research_result"
                },
            }, )
        logger.info(
            f"[ResearchExecutor] EXIT | tools_executed={result.tools_executed} updates=['research_result', 'messages']"
        )

        await ctx.send_message(result)
