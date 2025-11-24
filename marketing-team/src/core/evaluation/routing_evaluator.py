"""Framework-agnostic routing evaluator with adapters for LangGraph and CrewAI.

The adapter pattern lets us exercise a content-planning decision (tool routing)
independently of the underlying orchestration framework. Use
``RoutingEvaluator`` with a concrete adapter to test accuracy and consistency
of routing decisions across queries and runs.

Public API
        RoutingAdapter (ABC) and concrete adapters:
                - LangGraphRoutingAdapter
                - CrewAIRoutingAdapter
                - AgentFrameworkRoutingAdapter

Notes
        - Adapters provide `invoke(query, config)` and `extract_routing_decision(result)`
            so test runners can be written against a stable interface regardless
            of the orchestration backend.
        - The module uses best-effort extraction heuristics to cope with different
            workflow output shapes (messages, thread states, or streamed events).
"""
from typing import List, Dict, Any
import pandas as pd
from abc import ABC, abstractmethod

from langchain_core.messages import AIMessage, HumanMessage
from src.orchestration.langgraph.states.content_generation_state import ContentGenerationState
from src.core.utils.config_loader import load_brand_config
import asyncio
from typing import Any
import logging
import time
from pathlib import Path
import json

# We expect the workflow to expose the content thread state inside a
# namespace-like object stored in the workflow shared state (e.g. a
# SimpleNamespace with a `.state` attribute). Import the project
# ContentThreadState model so we can detect it when present.
try:
    from src.orchestration.microsoft_agent_framework.thread_states.content_thread_state import (
        ContentThreadState,
    )
except Exception:
    ContentThreadState = None  # type: ignore


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
            max_iterations=1  
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
# Agent Framework Adapter
# ============================================================================


class AgentFrameworkRoutingAdapter(RoutingAdapter):
    """Adapter for Microsoft Agent Framework workflows.

    This adapter runs the workflow to produce an initial planning decision and
    extracts the chosen tools from the thread state (or from emitted outputs).
    """

    def __init__(
        self,
        workflow,
        brand: str,
        template: str = "LINKEDIN_POST_ZERO_SHOT",
        use_cot: bool = True,
        brand_config: Dict | None = None,
        examples = []
    ):
        self.workflow = workflow
        self.brand = brand
        self.template = template
        self.use_cot = use_cot
        self.brand_config = brand_config
        self.examples = examples

    def invoke(self, query: str, config: Dict) -> Any:
        """Run the workflow synchronously (blocks) and return the WorkflowRunResult."""
        logger = logging.getLogger(__name__)
        logger.info("AgentFrameworkRoutingAdapter.invoke START query=%s", query)
        brand_config = self.brand_config or load_brand_config(self.brand)

        initial_message: Dict[str, Any] = {
            "brand": self.brand,
            "topic": query,
            "brand_config": brand_config,
            "template": self.template,
            "use_cot": self.use_cot,
            "examples": self.examples,
            "max_iterations": 1,  # stop after planning/execution superstep(s)
        }

        # The workflow.run API is async; run it synchronously here.
        # Outside Jupyter we use asyncio.run; inside Jupyter we run
        # workflow.run in a background thread with its own event loop.
        loop = None
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = None

        if loop is None or not loop.is_running():
            t0 = time.perf_counter()
            result = asyncio.run(self.workflow.run(message=initial_message))
            t1 = time.perf_counter()
            logger.info("AgentFrameworkRoutingAdapter.invoke asyncio.run completed in %.3fs", t1 - t0)
        else:
            import threading
            result_container: dict[str, object] = {}

            def _runner():
                new_loop = asyncio.new_event_loop()
                try:
                    asyncio.set_event_loop(new_loop)
                    logger.info("AgentFrameworkRoutingAdapter.invoke: runner starting event loop in thread")
                    rt0 = time.perf_counter()
                    res = new_loop.run_until_complete(self.workflow.run(message=initial_message))
                    rt1 = time.perf_counter()
                    result_container["result"] = res
                    result_container["duration"] = rt1 - rt0
                    logger.info("AgentFrameworkRoutingAdapter.invoke: runner completed in thread in %.3fs", rt1 - rt0)
                except Exception as e:
                    result_container["exc"] = e
                finally:
                    try:
                        new_loop.close()
                    except Exception:
                        pass

            t = threading.Thread(target=_runner)
            t.start()
            t.join()
            if "exc" in result_container:
                logger.error("AgentFrameworkRoutingAdapter.invoke: runner raised exception: %s", result_container["exc"])
                raise result_container["exc"]
            result = result_container.get("result")
            if "duration" in result_container:
                logger.info("AgentFrameworkRoutingAdapter.invoke: background thread run duration %.3fs", result_container["duration"])

        # Inspect result outputs; for now we only log the type and return
        # the WorkflowRunResult so callers can inspect it.
        try:
            outputs = result.get_outputs() if hasattr(result, "get_outputs") else None
        except Exception:
            outputs = None

        # If the WorkflowRunResult reports no outputs, try streaming events
        # and capture any WorkflowOutputEvent instances. This mirrors the
        # official samples which inspect run_stream for output events when
        # outputs are not present via the higher-level API.
        try:
            has_outputs = bool(outputs)
        except Exception:
            has_outputs = False

        if not has_outputs:
            logger.info("AgentFrameworkRoutingAdapter.invoke: no outputs found, attempting run_stream fallback")

            async def _collect_stream_outputs(msg: Dict[str, Any]):
                collected = []
                async for ev in self.workflow.run_stream(message=msg):
                    # Guard against missing attributes; check class name used
                    # in official samples: WorkflowOutputEvent
                    try:
                        ev_name = ev.__class__.__name__
                    except Exception:
                        ev_name = ""

                    if ev_name == "WorkflowOutputEvent":
                        try:
                            collected.append(ev.data)
                        except Exception:
                            # best-effort: append raw event
                            collected.append(ev)
                return collected

            # Run the async stream collector synchronously (handle Jupyter)
            try:
                loop2 = asyncio.get_event_loop()
            except RuntimeError:
                loop2 = None

            if loop2 is None or not loop2.is_running():
                try:
                    streamed_outputs = asyncio.run(_collect_stream_outputs(initial_message))
                except Exception:
                    streamed_outputs = []
            else:
                import threading as _threading

                stream_container: dict = {}

                def _stream_runner():
                    new_loop = asyncio.new_event_loop()
                    try:
                        asyncio.set_event_loop(new_loop)
                        stream_container["outputs"] = new_loop.run_until_complete(_collect_stream_outputs(initial_message))
                    except Exception as e:
                        stream_container["exc"] = e
                    finally:
                        try:
                            new_loop.close()
                        except Exception:
                            pass

                thr = _threading.Thread(target=_stream_runner)
                thr.start()
                thr.join()
                if "exc" in stream_container:
                    logger.warning("AgentFrameworkRoutingAdapter.invoke: run_stream fallback raised: %s", stream_container.get("exc"))
                    streamed_outputs = []
                else:
                    streamed_outputs = stream_container.get("outputs", [])

            # If we found streamed outputs, attach them to the result so
            # downstream callers (extract_routing_decision) can access them
            # via result.get_outputs(). We monkeypatch `get_outputs` only if
            # the original result had no outputs.
            if streamed_outputs:
                try:
                    # Attach a simple get_outputs override to return streamed data
                    setattr(result, "get_outputs", lambda: streamed_outputs)
                    logger.info("AgentFrameworkRoutingAdapter.invoke: attached %d streamed outputs to result", len(streamed_outputs))
                except Exception:
                    logger.warning("AgentFrameworkRoutingAdapter.invoke: failed to attach streamed outputs to result object")

        logger.info("AgentFrameworkRoutingAdapter.invoke: outputs type=%s", type(outputs))
        logger.info("AgentFrameworkRoutingAdapter.invoke END returning result: %s", type(result))
        return result

    def extract_routing_decision(self, result: Any) -> Dict[str, Any]:
        """Extract planning decision (tools) from WorkflowRunResult outputs.

        Supports multiple output shapes:
        - Workflow outputs that contain a `Thread` with `ContentThreadState`.
        - Dict outputs containing `messages` similar to LangGraph app.invoke result.
        """
        # If result is a WorkflowRunResult, get outputs
        outputs = []
        try:
            outputs = result.get_outputs() if hasattr(result, "get_outputs") else list(result)
        except Exception:
            # Fallback: if result is already a list/dict
            if isinstance(result, list):
                outputs = result
            else:
                outputs = [result]

        # 1) Look for namespace-like outputs with `.state` being ContentThreadState
        for out in outputs:
            try:
                state = getattr(out, "state", None)
            except Exception:
                state = None

            if ContentThreadState is not None and state is not None and isinstance(state, ContentThreadState):
                pd = getattr(state, "planning_decision", None)
                if pd is None:
                    return {"tools": [], "tool": None, "reasoning": "No planning_decision in thread state"}

                # Normalize planning decision
                tools = []
                reasoning = ""
                if isinstance(pd, dict):
                    tools = pd.get("tools") or pd.get("tool_calls") or []
                    reasoning = pd.get("reasoning", "")
                else:
                    tools_attr = getattr(pd, "tools", None) or getattr(pd, "tool_calls", None)
                    if tools_attr is not None:
                        tools = tools_attr
                    reasoning = getattr(pd, "reasoning", "") or getattr(pd, "explanation", "")

                # Normalize tool names
                normalized = []
                for t in tools or []:
                    if isinstance(t, str):
                        normalized.append(t)
                    elif isinstance(t, dict):
                        name = t.get("name") or t.get("tool")
                        if name:
                            normalized.append(name)
                    else:
                        name = getattr(t, "name", None)
                        if name:
                            normalized.append(name)

                return {"tools": normalized, "tool": normalized[0] if normalized else None, "reasoning": reasoning}

        # 2) Look for dict-like outputs with `messages` (LangGraph-like)
        for out in outputs:
            if isinstance(out, dict) and "messages" in out:
                messages = out.get("messages", [])
                for msg in messages:
                    if isinstance(msg, AIMessage):
                        tool_calls = getattr(msg, "tool_calls", None)
                        if isinstance(tool_calls, list) and tool_calls:
                            tools = [tc.get("name") for tc in tool_calls if tc and isinstance(tc, dict)]
                            reasoning = tool_calls[0].get("args", {}).get("reasoning", "") if tools else ""
                            return {"tools": tools, "tool": tools[0] if tools else None, "reasoning": reasoning}
                        else:
                            return {"tools": [], "tool": None, "reasoning": "Content planning decided no tools needed"}

        # Fallback
        # As a pragmatic fallback for notebook debugging, attempt to read a
        # planner debug JSON file written by the planning executor. The
        # planning executor writes to: <project>/examples/marketing_team/.debug/
        # with filename `planner_decision_<safe_topic>.json`.
        try:
            # Build a safe filename matching the planner's sanitizer
            topic = None
            # Try to extract topic from outputs or result
            if isinstance(result, dict) and "topic" in result:
                topic = result.get("topic")
            else:
                # Inspect outputs for a candidate topic string
                for out in outputs:
                    try:
                        t = getattr(out, "topic", None)
                    except Exception:
                        t = None
                    if t:
                        topic = t
                        break

            if topic is None and outputs:
                # Last resort: try to parse any dict-like output for a 'topic' key
                for out in outputs:
                    if isinstance(out, dict) and out.get("topic"):
                        topic = out.get("topic")
                        break

            if topic:
                thread_id = str(topic).replace(" ", "_")
                safe_thread_id = "".join(c for c in thread_id if c.isalnum() or c in "-_.")[:120]
                filename = f"planner_decision_{safe_thread_id}.json"

                # Candidate dirs (match planner logic: parents[4] /.debug)
                src_path = Path(__file__).resolve()
                candidates = []
                try:
                    candidates.append(src_path.parents[4] / ".debug")
                except Exception:
                    pass
                # also try repo-level examples path
                candidates.append(Path.cwd() / "examples" / "marketing_team" / ".debug")

                for d in candidates:
                    try_path = d / filename
                    if try_path.exists():
                        with try_path.open("r", encoding="utf-8") as fh:
                            pj = json.load(fh)
                        tools = pj.get("tools") or []
                        return {"tools": tools, "tool": tools[0] if tools else None, "reasoning": "planner_debug_file"}
        except Exception:
            pass

        return {"tools": ["unknown"], "tool": "unknown", "reasoning": "Could not find planning decision in workflow outputs"}


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