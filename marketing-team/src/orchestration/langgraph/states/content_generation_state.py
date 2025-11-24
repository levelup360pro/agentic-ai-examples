"""
State schema for the marketing_team content planning → tools → generation → evaluation loop.

Exports:
- ContentGenerationState: TypedDict describing the workflow state shape.
"""

from typing import TypedDict, Any, Annotated, Optional, Dict, List
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from src.core.evaluation.content_evaluator import Critique


class ContentGenerationState(TypedDict):
    """
    State schema for agentic content generation with evaluation loop.

    Workflow:
        1) Content planning analyzes topic → decides tools (RAG, Web, both, none)
        2) Tool node executes selected tools → accumulates results in messages
        3) Content generation creates/updates draft using accumulated context
        4) Content evaluation scores draft → returns Critique + metadata
        5) Conditional edge:
             - If meets_quality_threshold OR iteration_count >= max_iterations → END
             - Else → back to content_generation for regeneration (with optimization sys msg)

    Fields:
        messages:
            Conversation history + tool results (ToolMessage) + AIMessage outputs.
            Uses add_messages reducer to accumulate across nodes.

        topic:
            The content request/topic (e.g., "Create a post about AI governance").

        brand:
            Brand key (e.g., "levelup360").

        brand_config:
            Full brand configuration dict (YAML-loaded).

        template:
            Template key (e.g., "LINKEDIN_POST_ZERO_SHOT", "BLOG_POST").

        use_cot:
            Whether to enable Chain-of-Thought prompting scaffold in prompt.

        draft_content:
            The current content draft (updated by content_generation_node).

        critique:
            Latest evaluation result object from content_evaluation_node (None until first eval).

        iteration_count:
            Number of generation→evaluation cycles completed (increments in evaluation node).

        max_iterations:
            Iteration limit to prevent infinite loops (default set by invoker).

        quality_threshold:
            Required minimum score (e.g., 7.0). If None, node uses config default.

        meets_quality_threshold:
            Boolean set by content_evaluation_node indicating whether the latest draft meets threshold.

        generation_metadata:
            Optional dict with model, cost, latency, token counts, pattern, prompt_used, etc.
            Set by content_generation_node.

        evaluation_metadata:
            Optional dict with evaluation cost, latency, tokens, etc.
            Set by content_evaluation_node.

        pattern:
            Optional generation pattern override (e.g., "single_pass", "reflection", "evaluator_optimizer").
            If present, nodes prefer this over config pattern.
    """

    # Reducer-accumulated messages
    messages: Annotated[list[BaseMessage], add_messages]

    # Core request and brand
    topic: str
    brand: str
    brand_config: Dict[str, Any]

    # Optional chat history (LLM-style messages: role/content/extra)
    messages: List[Dict[str, Any]] 


    # Prompt/generation controls
    template: str
    use_cot: bool

    # Generated content (latest draft)
    content: str

    # Latest evaluation result
    critique: Optional[Critique]

    # Loop controls
    iteration_count: int
    max_iterations: int
    quality_threshold: Optional[float]
    meets_quality_threshold: Optional[bool]

    # Optional metadata surfaces from nodes
    generation_metadata: Optional[Dict[str, Any]]
    evaluation_metadata: Optional[Dict[str, Any]]

    # Optional pattern override
    pattern: Optional[str]