"""Framework-agnostic routing evaluator with adapters for LangGraph and CrewAI.

The adapter pattern lets us exercise a content-planning decision (tool routing)
independently of the underlying orchestration framework. Use
``RoutingEvaluator`` with a concrete adapter to test accuracy and consistency
of routing decisions across queries and runs.
"""
from typing import List, Dict, Any
import pandas as pd
from abc import ABC, abstractmethod

from langchain_core.messages import AIMessage, HumanMessage
from src.agents.states.content_generation_state import ContentGenerationState
from src.utils.config_loader import load_brand_config


# ============================================================================
# Abstract Base
# ============================================================================

class RoutingAdapter(ABC):
    """Abstract adapter for different orchestration frameworks."""

    @abstractmethod
    def invoke(self, query: str, config: Dict) -> Any:
        """Execute the workflow with the given query and return raw result."""
        pass

    @abstractmethod
    def extract_routing_decision(self, result: Any) -> Dict[str, Any]:
        """Extract routing decision from framework-specific result.

        Returns dict with keys:
            - tools: List[str]
            - tool: Optional[str]
            - reasoning: str
        """
        pass


# ============================================================================
# LangGraph Adapter
# ============================================================================

class LangGraphRoutingAdapter(RoutingAdapter):
    """Adapter for LangGraph workflows that perform tool-based routing."""

    def __init__(
        self,
        app,
        brand: str,
        template: str = "LINKEDIN_POST_ZERO_SHOT",
        use_cot: bool = True,
    ):
        self.app = app
        self.brand = brand
        self.template = template
        self.use_cot = use_cot

    def invoke(self, query: str, config: Dict) -> Any:
        """Execute LangGraph workflow up to the content planning decision."""
        brand_config = load_brand_config(self.brand)

        state = ContentGenerationState(
            messages=[HumanMessage(content=query)],
            topic=query,
            brand=self.brand,
            brand_config=brand_config,
            template=self.template,
            use_cot=self.use_cot,
            draft_content="",
            critique=None,
            iteration_count=0,
            max_iterations=1  # Stop after content planning decision
        )

        return self.app.invoke(state, config={"configurable": config})

    def extract_routing_decision(self, result: Any) -> Dict[str, Any]:
        """Extract routing decision from first AIMessage with tool_calls, if any."""
        messages = result.get("messages", [])

        for msg in messages:
            if isinstance(msg, AIMessage):
                tool_calls = getattr(msg, "tool_calls", None)
                if isinstance(tool_calls, list) and tool_calls:
                    tools = [tc.get("name") for tc in tool_calls if tc and isinstance(tc, dict)]
                    reasoning = tool_calls[0].get("args", {}).get("reasoning", "") if tools else ""
                    return {
                        "tools": tools,
                        "tool": tools[0] if tools else None,
                        "reasoning": reasoning,
                    }
                else:
                    # No tools requested by content planning node
                    return {
                        "tools": [],
                        "tool": None,
                        "reasoning": "Content planning node decided no tools needed",
                    }

        # Fallback if no AIMessage found
        return {
            "tools": ["unknown"],
            "tool": "unknown",
            "reasoning": "Could not find content planning decision",
        }


# ============================================================================
# CrewAI Adapter
# ============================================================================

class CrewAIRoutingAdapter(RoutingAdapter):
    """Adapter for CrewAI workflows using manager/agent delegation."""

    def __init__(self, crew, brand: str):
        """
        Initialize CrewAI adapter.

        Args:
            crew: CrewAI Crew instance with manager + specialized agents
            brand: Brand identifier
        """
        self.crew = crew
        self.brand = brand

    def invoke(self, query: str, config: Dict) -> Any:
        """Execute CrewAI workflow; capture only the first assignment/decision."""
        brand_config = load_brand_config(self.brand)
        result = self.crew.kickoff(
            inputs={
                "query": query,
                "brand": self.brand,
                "brand_config": brand_config,
                "max_iterations": 1,  # Stop after first assignment
            }
        )
        return result

    def extract_routing_decision(self, result: Any) -> Dict[str, Any]:
        """Extract routing decision from CrewAI result and map agent roles to tools."""
        # Method 1: Structured outputs
        if hasattr(result, "tasks_output") and result.tasks_output:
            first_task = result.tasks_output[0]
            agent_role = getattr(first_task, "agent", None) or getattr(first_task, "node", None)

            agent_to_tool = {
                "RAG Researcher": "rag_search",
                "Web Researcher": "web_search",
                "Content Writer": None,  # no tools
            }
            tool = agent_to_tool.get(agent_role, None)
            tools = [] if tool is None else [tool]

            return {
                "tools": tools,
                "tool": tool,
                "reasoning": getattr(first_task, "description", ""),
            }

        # Method 2: Heuristic from raw text
        if hasattr(result, "raw") and result.raw:
            raw_text = str(result.raw).lower()
            if "rag" in raw_text or "retrieval" in raw_text:
                return {"tools": ["rag_search"], "tool": "rag_search", "reasoning": "RAG agent detected in output"}
            if "web search" in raw_text or "tavily" in raw_text:
                return {"tools": ["web_search"], "tool": "web_search", "reasoning": "Web search agent detected in output"}
            # No tools inferred
            return {"tools": [], "tool": None, "reasoning": "Content writer (no tools)"}

        # Fallback
        return {"tools": ["unknown"], "tool": "unknown", "reasoning": "Could not infer agent assignment"}


# ============================================================================
# Framework-Agnostic Evaluator
# ============================================================================

class RoutingEvaluator:
    """Evaluate routing accuracy and consistency via an adapter.

    Example:
        adapter = LangGraphRoutingAdapter(app, brand)
        evaluator = RoutingEvaluator(adapter)
    """

    def __init__(self, adapter: RoutingAdapter):
        self.adapter = adapter

    def test_routing_accuracy(self, test_cases: List[Dict[str, str]]) -> pd.DataFrame:
        results = []

        for i, case in enumerate(test_cases):
            result = self.adapter.invoke(query=case["query"], config={"thread_id": f"test_{i}"})
            decision = self.adapter.extract_routing_decision(result)

            expected = case.get("expected_tools") or [case.get("expected_tool")]
            actual = decision.get("tools") or [decision.get("tool")]

            is_correct = set(actual) == set(expected)

            results.append({
                "query": case["query"],
                "expected_tools": expected,
                "actual_tools": actual,
                "reasoning": decision.get("reasoning", ""),
                "correct": is_correct,
                "reason_for_expected": case.get("reason", ""),
            })

        return pd.DataFrame(results)

    def test_routing_consistency(self, test_cases: List[Dict[str, str]], num_runs: int = 5) -> pd.DataFrame:
        """Test if the same tool set is returned across multiple runs (order-independent)."""
        consistency_results = []

        for case in test_cases:
            decisions = []
            for run in range(num_runs):
                result = self.adapter.invoke(query=case["query"], config={"thread_id": f"consistency_{run}"})
                decision = self.adapter.extract_routing_decision(result)
                tools = decision.get("tools", [])
                tools_tuple = tuple(sorted(tools)) if tools else ()
                decisions.append(tools_tuple)

            is_consistent = len(set(decisions)) == 1

            consistency_results.append({
                "query": case["query"],
                "expected_tools": case.get("expected_tools"),
                "actual_decisions": decisions,
                "consistent": is_consistent,
                "unique_decisions": len(set(decisions)),
                "mode_decision": max(set(decisions), key=decisions.count) if decisions else (),
            })

        return pd.DataFrame(consistency_results)

    def analyze_results(
        self,
        accuracy_results: pd.DataFrame,
        consistency_results: pd.DataFrame,
        accuracy_threshold: float = 0.90,
        consistency_threshold: float = 0.95,
    ) -> Dict[str, Any]:
        """Summarize accuracy/consistency and list failures and inconsistencies."""
        acc_df = accuracy_results.copy()

        acc_df["tools_key"] = acc_df["expected_tools"].apply(
            lambda x: tuple(sorted(x)) if isinstance(x, list) and x else ("none",)
        )

        accuracy = acc_df["correct"].mean()
        consistency = consistency_results["consistent"].mean()

        by_tool = acc_df.groupby("tools_key")["correct"].agg(["mean", "count"])

        failures = acc_df[~acc_df["correct"]][["query", "expected_tools", "actual_tools"]]
        inconsistent = consistency_results[~consistency_results["consistent"]]

        passes = (accuracy >= accuracy_threshold) and (consistency >= consistency_threshold)

        return {
            "accuracy": accuracy,
            "consistency": consistency,
            "passes": passes,
            "accuracy_by_tool": by_tool.to_dict("index"),
            "failures": failures.to_dict("records"),
            "inconsistent_cases": inconsistent.to_dict("records"),
            "thresholds": {"accuracy": accuracy_threshold, "consistency": consistency_threshold},
        }