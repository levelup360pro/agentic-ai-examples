"""Research executor for the Microsoft Agent Framework workflow.

This module defines a pure executor (no WorkflowContext dependency)
that performs RAG + web search + synthesis and returns a ResearchResult
model. A separate research node is responsible for interacting with
thread state and the Agent Framework runtime.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List
import json
import logging

from src.orchestration.microsoft_agent_framework.models.planning_models import (
    ResearchResult,
)

logger = logging.getLogger(__name__)


class ResearchExecutor:
    """Pure research executor that returns a ResearchResult.

    This class is intentionally decoupled from the workflow runtime.
    It consumes infra (LLM client, RAG, search) and domain inputs,
    and returns a structured ResearchResult instance.
    """

    def __init__(
        self,
        rag_tool: Callable[..., Dict[str, Any]],
        web_tool: Callable[..., Dict[str, Any]],
    ) -> None:
        """Initialize the executor with tool callables.

        Args:
            rag_tool: Callable created by `create_rag_search_tool`.
            web_tool: Callable created by `create_tavily_search_tool`.
        """
        self.rag_tool = rag_tool
        self.web_tool = web_tool

    async def run(
        self,
        topic: str,
        brand: str,
        tools: List[str]
    ) -> ResearchResult:
        """Execute research for a given topic/brand using selected tools."""

        rag_results: List[Any] = []
        web_results: List[Any] = []

        if "rag_search" in tools:
            rag_payload = self.rag_tool.invoke({"query": topic, "brand": brand})
            rag_results = rag_payload.get("results", [])

        if "web_search" in tools:
            web_payload = self.web_tool.invoke({"query": topic})
            web_results = web_payload.get("sources", [])

        # Build evidence dict with summary for each tool executed
        evidence: Dict[str, str] = {}
        if rag_results:
            evidence["rag_search"] = f"Found {len(rag_results)} relevant brand documents"
        if web_results:
            evidence["web_search"] = f"Found {len(web_results)} web sources"

        tool_contexts: Dict[str, str] = {}
        if rag_results:
            tool_contexts["rag_search"] = json.dumps(rag_results)
        if web_results:
            tool_contexts["web_search"] = json.dumps(web_results)

        logger.info(
            f"[ResearchExecutor] run completed: topic='{topic}', brand='{brand}', tools={tools}, rag_documents={len(rag_results)}, rag_results={rag_results}, web_sources={len(web_results)}, web_results={web_results}"
        )

        return ResearchResult(
            topic=topic,
            brand=brand,
            tools_executed=tools,
            evidence=evidence,
            tool_contexts=tool_contexts,
        )