"""
Content Generator
Orchestrates content generation using LLM.
Supports both deterministic (non-agentic) and agentic workflows
with minimal code duplication via shared private helpers.
"""

from typing import Dict, Optional, List, Any, Tuple
from datetime import datetime
import logging

from src.utils.llm_client import LLMClient, CompletionResult
from src.prompts.prompt_builder import PromptBuilder
from src.prompts.templates import (
    LINKEDIN_POST_ZERO_SHOT,
    LINKEDIN_POST_FEW_SHOT,
    LINKEDIN_LONG_POST_ZERO_SHOT,
    LINKEDIN_LONG_POST_FEW_SHOT,
    BLOG_POST,
    NEWSLETTER,
    FACEBOOK_POST_ZERO_SHOT,
    FACEBOOK_POST_FEW_SHOT,
)
from src.evaluation.content_evaluator import ContentEvaluator, Critique

logger = logging.getLogger(__name__)


class ContentGenerator:
    """Generate content using LLM (deterministic and agentic modes)."""

    # Template mapping (string key → PromptTemplate object)
    TEMPLATE_MAP = {
        "LINKEDIN_POST_ZERO_SHOT": LINKEDIN_POST_ZERO_SHOT,
        "LINKEDIN_POST_FEW_SHOT": LINKEDIN_POST_FEW_SHOT,
        "LINKEDIN_LONG_POST_ZERO_SHOT": LINKEDIN_LONG_POST_ZERO_SHOT,
        "LINKEDIN_LONG_POST_FEW_SHOT": LINKEDIN_LONG_POST_FEW_SHOT,
        "BLOG_POST": BLOG_POST,
        "NEWSLETTER": NEWSLETTER,
        "FACEBOOK_POST_ZERO_SHOT": FACEBOOK_POST_ZERO_SHOT,
        "FACEBOOK_POST_FEW_SHOT": FACEBOOK_POST_FEW_SHOT,
    }

    def __init__(
        self,
        llm_client: LLMClient,
        prompt_builder: PromptBuilder,
        content_evaluator: Optional[ContentEvaluator] = None,
    ):
        """
        Initialize ContentGenerator (framework-agnostic).

        Args:
            llm_client: LLM client for all model calls
            prompt_builder: Prompt builder for both deterministic/agentic paths
            content_evaluator: Optional evaluator for reflection/evaluator-optimizer patterns
        """
        self.llm_client = llm_client
        self.prompt_builder = prompt_builder
        self.content_evaluator = content_evaluator

    # -------------------------------
    # Deterministic mode
    # -------------------------------
    def generate(
        self,
        *,
        topic: str,
        brand: str,
        brand_config: dict,
        template: str,
        include_rag: bool = True,
        include_search: bool = False,
        collection_name: str = "marketing_content",
        rag_max_distance: Optional[float] = None,
        search_depth: Optional[str] = None,
        search_type: Optional[str] = None,
        examples: Optional[List[str]] = None,
        use_cot: bool = False,
        pattern: str = "single_pass",  # "single_pass", "reflection", "evaluator_optimizer"
        max_iterations: int = 1,
        # Overrides; if None, pulled from brand_config["models"]["content_generation"]
        model: Optional[str] = None,
        system_message: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        generation_config: Optional[dict] = None,
        optimization_config: Optional[dict] = None,
    ) -> Dict[str, Any]:
        """
        Deterministic workflow: PromptBuilder may call tools internally (include_rag/search).

        Returns:
            Dict with keys:
              - content: Generated text
              - metadata: cost, latency, tokens, pattern, iterations, prompt_used, etc.
        """
        # Resolve configs
        generation_config = self._resolve_generation_config(generation_config, brand_config)
        optimization_config = self._resolve_optimization_config(optimization_config, brand_config)

        # Resolve template object
        template_obj = self._resolve_template(template)

        # Build user prompt (deterministic path may call tools internally)
        user_prompt = self.prompt_builder.build_user_message(
            collection_name=collection_name,
            template=template_obj,
            topic=topic,
            brand=brand.lower(),
            brand_config=brand_config,
            include_rag=include_rag,
            max_distance=rag_max_distance,
            include_search=include_search,
            search_depth=search_depth,
            search_type=search_type,
            llm_client=self.llm_client,
            examples=examples,
            use_cot=use_cot,
        )

        # Build messages
        final_system_message = self._format_system_message(
            system_message or generation_config["system_message"], brand_config
        )
        messages = self._build_messages(user_prompt, final_system_message, use_cot)

        # Run selected pattern
        result, iterations, final_critique = self._run_pattern(
            pattern=pattern,
            model=model or generation_config["model"],
            messages=messages,
            temperature=temperature if temperature is not None else generation_config["temperature"],
            max_tokens=max_tokens if max_tokens is not None else generation_config["max_tokens"],
            max_iterations=max_iterations,
            optimization_system_message=optimization_config.get("system_message") if optimization_config else None,
            template_key=template,
            brand=brand,                    # pass brand
            brand_config=brand_config,      # pass brand_config
        )

        # Package result
        metadata = {
            "topic": topic,
            "template": template,
            "brand": brand,
            "system_message": final_system_message,
            "model": result.model,
            "cost": result.cost,
            "latency": result.latency,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "include_rag": include_rag,
            "include_search": include_search,
            "temperature": temperature if temperature is not None else generation_config["temperature"],
            "pattern": pattern,
            "iterations": iterations,
            "prompt_used": user_prompt,
            "timestamp": datetime.now().isoformat(),
        }
        if final_critique:
            metadata["final_critique"] = {
                "average_score": getattr(final_critique, "average_score", None),
                "meets_threshold": getattr(final_critique, "meets_threshold", None),
                "violations": getattr(final_critique, "violations", None),
            }

        return {"content": result.content, "metadata": metadata}

    # ----------------------------
    # Agentic  mode
    # ----------------------------
    def generate_from_context(
        self,
        *,
        topic: str,
        brand: str,
        brand_config: dict,
        template: str,
        tool_contexts: Optional[Dict[str, str]] = None,  # {"rag_search": "...", "web_search": "..."}
        use_cot: bool = False,
        pattern: str = "single_pass",
        max_iterations: int = 1,
        generation_config: Optional[dict] = None,
        optimization_config: Optional[dict] = None,
    ) -> Dict[str, Any]:
        """
        Agentic workflow: tool_contexts are pre-fetched by orchestration.
        """
        # Resolve configs
        generation_config = self._resolve_generation_config(generation_config, brand_config)
        optimization_config = self._resolve_optimization_config(optimization_config, brand_config)

        # Resolve template object
        template_obj = self._resolve_template(template)

        # Build user prompt from tool contexts (no tool calls here)
        user_prompt = self.prompt_builder.build_generation_prompt(
            template=template_obj,
            topic=topic,
            brand=brand,
            brand_config=brand_config,
            tool_contexts=tool_contexts or {},
            use_cot=use_cot,
        )

        # Build messages
        final_system_message = self._format_system_message(
            generation_config["system_message"], brand_config
        )
        messages = self._build_messages(user_prompt, final_system_message, use_cot)

        # Run selected pattern (same helpers as deterministic)
        result, iterations, final_critique = self._run_pattern(
            pattern=pattern,
            model=generation_config["model"],
            messages=messages,
            temperature=generation_config["temperature"],
            max_tokens=generation_config["max_tokens"],
            max_iterations=max_iterations,
            optimization_system_message=optimization_config.get("system_message") if optimization_config else None,
            template_key=template,
            brand=brand,                    # pass brand
            brand_config=brand_config,      # pass brand_config
        )

        metadata = {
            "topic": topic,
            "template": template,
            "brand": brand,
            "system_message": final_system_message,
            "model": result.model,
            "cost": result.cost,
            "latency": result.latency,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "pattern": pattern,
            "iterations": iterations,
            "prompt_used": user_prompt,
            "timestamp": datetime.now().isoformat(),
        }
        if final_critique:
            metadata["final_critique"] = {
                "average_score": getattr(final_critique, "average_score", None),
                "meets_threshold": getattr(final_critique, "meets_threshold", None),
                "violations": getattr(final_critique, "violations", None),
            }

        return {"content": result.content, "metadata": metadata}

    # ------------------------
    # Convenience: Batch mode
    # ------------------------
    def generate_batch(
        self,
        topics: List[str],
        *,
        brand: str,
        brand_config: dict,
        template: str,
        pattern: str = "single_pass",
        max_iterations: int = 1,
        deterministic: bool = True,
        tool_contexts_list: Optional[List[Optional[Dict[str, str]]]] = None,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """
        Generate multiple pieces of content. Supports both deterministic and agentic.

        If deterministic=True, ignores tool_contexts_list and uses generate().
        If deterministic=False, uses generate_from_context() and expects tool_contexts_list
        of same length as topics (or None for direct generation).
        """
        if isinstance(topics, str):
            topics = [topics]

        results: List[Dict[str, Any]] = []
        n = len(topics)

        if not deterministic and tool_contexts_list and len(tool_contexts_list) != n:
            raise ValueError("tool_contexts_list length must match topics length in agentic mode")

        for i, topic in enumerate(topics):
            if deterministic:
                result = self.generate(
                    topic=topic,
                    brand=brand,
                    brand_config=brand_config,
                    template=template,
                    pattern=pattern,
                    max_iterations=max_iterations,
                    **kwargs,
                )
            else:
                tc = tool_contexts_list[i] if tool_contexts_list else None
                result = self.generate_from_context(
                    topic=topic,
                    brand=brand,
                    brand_config=brand_config,
                    template=template,
                    tool_contexts=tc,
                    pattern=pattern,
                    max_iterations=max_iterations,
                    **kwargs,
                )

            results.append(result)

        return results

    # -----------------------
    # Private helper methods
    # -----------------------
    def _resolve_template(self, template_key: str):
        template_obj = self.TEMPLATE_MAP.get(template_key)
        if not template_obj:
            raise ValueError(
                f"Unknown template: {template_key}. "
                f"Valid options: {list(self.TEMPLATE_MAP.keys())}"
            )
        return template_obj

    def _resolve_generation_config(self, generation_config: Optional[dict], brand_config: dict) -> dict:
        return generation_config or brand_config["models"]["content_generation"]

    def _resolve_optimization_config(self, optimization_config: Optional[dict], brand_config: dict) -> dict:
        return optimization_config or brand_config.get("models", {}).get("content_optimization", {})

    def _format_system_message(self, system_message: str, brand_config: dict) -> str:
        if "{banned_terms}" in system_message:
            banned_terms = brand_config.get("voice", {}).get("banned_terms", [])
            if banned_terms:
                banned_terms_formatted = "\n   ".join(f"- {term}" for term in banned_terms)
                return system_message.format(banned_terms=banned_terms_formatted)
        return system_message

    def _build_messages(self, user_prompt: str, system_message: str, use_cot: bool) -> List[Dict[str, str]]:
        if use_cot:
            cot_prompt = (
                "\nBreak down the task into smaller steps before answering. "
                "Provide your reasoning process clearly, then give the final content."
            )
            return [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt + cot_prompt},
            ]
        return [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_prompt},
        ]

    def _run_pattern(
        self,
        *,
        pattern: str,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        max_iterations: int,
        optimization_system_message: Optional[str],
        template_key: str,
        brand: str,
        brand_config: dict,
    ) -> Tuple[CompletionResult, int, Optional[Critique]]:
        """Route to the appropriate generation pattern."""
        if pattern == "reflection":
            self._ensure_evaluator("reflection")
            return self._run_reflection(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                max_iterations=max_iterations,
                brand=brand,
                brand_config=brand_config,
            )
        if pattern == "evaluator_optimizer":
            self._ensure_evaluator("evaluator_optimizer")
            return self._run_evaluator_optimizer(
                model=model,
                messages=messages,
                template_key=template_key,
                temperature=temperature,
                max_tokens=max_tokens,
                max_iterations=max_iterations,
                optimization_system_message=optimization_system_message,
                brand=brand,
                brand_config=brand_config,
            )
        # Default single pass
        result = self.llm_client.get_completion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return result, 1, None

    def _ensure_evaluator(self, pattern_name: str) -> None:
        if not self.content_evaluator:
            raise ValueError(
                f"{pattern_name} pattern requires ContentEvaluator; "
                f"initialize ContentGenerator with content_evaluator"
            )

    def _run_reflection(
        self,
        *,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        max_iterations: int,
        brand: str,
        brand_config: dict,
    ) -> Tuple[CompletionResult, int, Optional[Critique]]:
        """Generate with reflection and critique loop (aggregates cost/latency)."""
        history = list(messages)  # copy
        total_cost = 0.0
        total_latency = 0.0
        total_in = 0
        total_out = 0
        iterations = 0
        final_critique: Optional[Critique] = None
        last_result: Optional[CompletionResult] = None

        while iterations <= max_iterations:
            result = self.llm_client.get_completion(
                model=model, messages=history, temperature=temperature, max_tokens=max_tokens
            )

            total_cost += result.cost
            total_latency += result.latency
            total_in += result.input_tokens
            total_out += result.output_tokens

            history.append({"role": "assistant", "content": result.content})
            iterations += 1
            last_result = result

            if iterations > max_iterations:
                break

            critique, eval_meta = self.content_evaluator.evaluate_content(
                content=result.content,
                brand=brand,
                brand_config=brand_config,
                content_type=None,
                history=history,
                model=model,
                pattern="reflection",
            )
            total_cost += eval_meta.get("cost", 0.0)
            total_latency += eval_meta.get("latency", 0.0)
            total_in += eval_meta.get("input_tokens", 0)
            total_out += eval_meta.get("output_tokens", 0)

            final_critique = critique
            if getattr(critique, "meets_threshold", False):
                break

            # Add feedback
            history = self._add_evaluation_feedback(history=history, evaluation=critique)

        # Aggregate into a single result
        aggregated = CompletionResult(
            content=last_result.content if last_result else "",
            input_tokens=total_in,
            output_tokens=total_out,
            cost=total_cost,
            latency=total_latency,
            model=last_result.model if last_result else model,
            timestamp=last_result.timestamp if last_result else datetime.now().isoformat(),
        )
        return aggregated, iterations, final_critique

    def _run_evaluator_optimizer(
        self,
        *,
        model: str,
        messages: List[Dict[str, str]],
        template_key: str,
        temperature: float,
        max_tokens: int,
        max_iterations: int,
        optimization_system_message: Optional[str],
        brand: str,
        brand_config: dict,
    ) -> Tuple[CompletionResult, int, Optional[Critique]]:
        """Generate with evaluator-optimizer loop (aggregates cost/latency)."""
        optimize_messages = list(messages)  # copy
        total_cost = 0.0
        total_latency = 0.0
        total_in = 0
        total_out = 0
        iterations = 0
        final_critique: Optional[Critique] = None
        last_result: Optional[CompletionResult] = None

        while iterations <= max_iterations:
            result = self.llm_client.get_completion(
                model=model, messages=optimize_messages, temperature=temperature, max_tokens=max_tokens
            )

            total_cost += result.cost
            total_latency += result.latency
            total_in += result.input_tokens
            total_out += result.output_tokens

            iterations += 1
            last_result = result

            if iterations > max_iterations:
                break

            critique, eval_meta = self.content_evaluator.evaluate_content(
                content=result.content,
                brand=brand,
                brand_config=brand_config,
                content_type=template_key,
                history=None,
                model=model,
                pattern="evaluator_optimizer",
            )
            total_cost += eval_meta.get("cost", 0.0)
            total_latency += eval_meta.get("latency", 0.0)
            total_in += eval_meta.get("input_tokens", 0)
            total_out += eval_meta.get("output_tokens", 0)

            final_critique = critique
            if getattr(critique, "meets_threshold", False):
                break

            # Build optimization prompt for next iteration
            sys_msg = optimization_system_message or (
                "You are a content optimizer. Improve content based on evaluation feedback."
            )
            sys = [{"role": "system", "content": sys_msg}]
            assistant = [{"role": "assistant", "content": result.content}]
            optimize_messages = sys + assistant
            optimize_messages = self._add_evaluation_feedback(history=optimize_messages, evaluation=critique)

        aggregated = CompletionResult(
            content=last_result.content if last_result else "",
            input_tokens=total_in,
            output_tokens=total_out,
            cost=total_cost,
            latency=total_latency,
            model=last_result.model if last_result else model,
            timestamp=last_result.timestamp if last_result else datetime.now().isoformat(),
        )
        return aggregated, iterations, final_critique

    def _add_evaluation_feedback(self, history: List[Dict[str, str]], evaluation: Critique) -> List[Dict[str, str]]:
        """Append evaluation feedback as a user message to guide next iteration."""
        messages = list(history)  # copy
        feedback_lines = []
        if getattr(evaluation, "reasoning", None):
            feedback_lines.append(f"- {evaluation.reasoning}")
        violations = getattr(evaluation, "violations", []) or []
        if violations:
            feedback_lines.append("Brand violations:")
            for v in violations:
                feedback_lines.append(f"  • {v}")

        feedback = "FEEDBACK:\n" + "\n".join(feedback_lines)
        feedback += "\nImprove the content by addressing the feedback."
        feedback += "\nREMINDER: Do not change the content topic, only improve it."
        messages.append({"role": "user", "content": feedback})
        return messages