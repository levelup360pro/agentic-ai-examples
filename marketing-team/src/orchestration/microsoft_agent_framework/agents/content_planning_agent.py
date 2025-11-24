"""Planner agent for content workflows (framework-agnostic).

`ContentPlanningAgent` encapsulates the domain logic used to decide
whether research is required and which tools to run. It is intentionally
framework-agnostic: it accepts typed input models, uses the configured
LLM client to produce a `PlanningDecision`, and returns domain models
that are serializable and safe to persist on thread state.

The agent supports a two-pass workflow: an initial planning pass that
may route to research, and a post-research pass that synthesizes
evidence into a writing plan or final routing decision.
"""

from typing import List, Union, Dict, Literal
import logging

from src.orchestration.microsoft_agent_framework.models.planning_models import (
    PlanningInput,
    PlanningDecision,
    ResearchResult,
    WritingPlan,
)


logger = logging.getLogger(__name__)


class ContentPlanningAgent:
    """Planner executor that performs two roles:
    1. Initial planning: decide if research is required and which tools (internal RAG, external search).
    2. Post‑research synthesis: convert research evidence into a prompt plan for the writer.

    Workflow expectations:
    - Start message type: PlanningInput -> returns PlanningDecision
        - If route == "research": workflow routes to ResearchExecutor
        - ResearchExecutor returns ResearchResult -> routed back here
        - Second invocation: ResearchResult -> returns a second PlanningDecision whose
            route determines the next step (typically writer, but could be extended).

        This keeps research execution separate while preserving a single planning
        and routing surface, in line with coordinator-style agent patterns.
    """

    def __init__(self, llm_client, content_planning_config: dict):
        self.llm = llm_client
        self.content_planning_config = content_planning_config

    async def plan(
            self, message: Union[PlanningInput,
                                 ResearchResult]) -> PlanningDecision:
        """Planner entrypoint.

        - First pass: PlanningInput -> PlanningDecision (whether to run research
          and which tools to use).
        - Second pass: ResearchResult -> PlanningDecision (what to do with the
          research: typically route to writer, or optionally request more research
          in future extensions).
        """

        if isinstance(message, ResearchResult):
            logger.info(
                f"[ContentPlanningAgent] Received ResearchResult for topic='{message.topic}', brand='{message.brand}' with tools_executed={message.tools_executed}",
            )
            return self._post_research_planning(message)

        logger.info(
            f"[ContentPlanningAgent] Initial planning for topic='{message.topic}', brand='{message.brand}'"
        )
        return await self._initial_planning(message)

    async def _initial_planning(
            self, planning_input: PlanningInput) -> PlanningDecision:
        planner_config = planning_input.planner_config or self.content_planning_config

        system_message = planner_config["system_message"]

        user_message = (
            f"Content request: {planning_input.topic}\n"
            f"Brand: {planning_input.brand}\n"
            "Decide whether research is required. If research is needed, choose from "
            "['rag_search','web_search'] and return exactly those tool names.")

        messages: List[Dict[str, str]] = [
            {
                "role": "system",
                "content": system_message
            },
            {
                "role": "user",
                "content": user_message
            },
        ]

        if planning_input.previous_messages:
            # Exclude prior system messages to avoid duplicates; cap history length
            history = [m for m in planning_input.previous_messages if m.get("role") != "system"]

            # Sanitize prior messages' content to avoid passing provider-specific
            # structured blocks (e.g. tool_result with tool_use_id) which some
            # providers (Amazon Bedrock) reject when the corresponding tool_use
            # block is missing. Convert non-string contents to plain text.
            def _sanitize_content(content):
                # Common shapes: string, list of strings, or structured dict
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    parts = []
                    for c in content:
                        parts.append(c if isinstance(c, str) else str(c))
                    return "\n".join(parts)
                # Fallback: stringify dicts/objects safely
                try:
                    return str(content)
                except Exception:
                    return ""

            sanitized_history = []
            for m in history[-6:]:
                sanitized_history.append({
                    "role": m.get("role"),
                    "content": _sanitize_content(m.get("content", "")),
                    **({"metadata": m.get("metadata")} if m.get("metadata") is not None else {}),
                })

            messages.extend(sanitized_history)

        logger.info(
            f"[ContentPlanningAgent] Initial planning: topic='{planning_input.topic}', brand='{planning_input.brand}', model='{planner_config['model']}'"
        )

        result = self.llm.get_completion(
            model=planner_config["model"],
            temperature=planner_config["temperature"],
            max_tokens=planner_config["max_tokens"],
            messages=messages,
            response_format=PlanningDecision,
            tool_support=False,
            tools=[],
        )

        decision = result.structured_output
        logger.info(
            f"[ContentPlanningAgent] Decision: route='{decision.route}', tools={decision.tools}, confidence={decision.confidence:.3f}"
        )
        return decision

    def _post_research_planning(
            self, research_result: ResearchResult) -> PlanningDecision:
        """Second-pass planning after research.

        Current behavior:
        - If any evidence is present, route to "write".
        - If no evidence is found, still route to "write" but with lower
          confidence and a reason indicating that content will be written
          without external evidence. This keeps behavior simple for now while
          allowing future extension to re-trigger research or escalate.
        """

        has_evidence = bool(research_result.evidence)
        route: Literal["research", "write"] = "write"

        if has_evidence:
            reason = "Research completed; evidence available. Proceed to writer using aggregated tool contexts."
            confidence = 0.9
        else:
            reason = (
                "No research evidence returned; proceed to writer using brand guidance only. "
                "Future versions may re-trigger research instead.")
            confidence = 0.6

        decision = PlanningDecision(
            route=route,
            tools=[],
            reason=reason,
            confidence=confidence,
            topic=research_result.topic,
            brand=research_result.brand,
        )

        logger.info(
            f"[ContentPlanningAgent] Post-research decision: route='{decision.route}', confidence={decision.confidence:.3f}, has_evidence={has_evidence}"
        )

        return decision
