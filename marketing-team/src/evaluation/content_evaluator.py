"""Content evaluation utilities with rubric-based and reflection patterns.

This module defines the structured ``Critique`` schema used for LLM-native
response formatting, plus a framework-agnostic ``ContentEvaluator`` that can
evaluate generated content via either a rubric derived from brand config or a
lightweight reflection check using conversation history.

Public API
    Critique, EvaluationRubric, ContentEvaluator
"""
from __future__ import annotations
from typing import Dict, Optional, List, Any, Tuple
import datetime
import yaml
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from src.utils.llm_client import LLMClient


# ---------------------------
# Rubric / Critique Schemas
# ---------------------------

class RubricDimension(BaseModel):
    """Single evaluation dimension with config data."""
    description: str
    criteria: Dict[str, Any]
    weight: float = 1.0


class RubricMetadata(BaseModel):
    """Traceability metadata."""
    brand: str
    config_version: str
    generated_at: str
    content_type: Optional[str] = None  # optional for additional traceability


class EvaluationRubric(BaseModel):
    """Complete evaluation rubric."""
    brand_voice: RubricDimension
    structure: RubricDimension
    accuracy: RubricDimension
    metadata: RubricMetadata


class Critique(BaseModel):
    """Structured critique output for LLM-native response_format."""
    model_config = ConfigDict(json_schema_extra={
        "properties": {
            "brand_voice": {"type": "number", "minimum": 1, "maximum": 10},
            "structure": {"type": "number", "minimum": 1, "maximum": 10},
            "accuracy": {"type": "number", "minimum": 1, "maximum": 10},
            "violations": {"type": "array", "items": {"type": "string"}},
            "reasoning": {"type": "string"}
        },
        "required": ["brand_voice", "structure", "accuracy"],
        "additionalProperties": False
    })

    brand_voice: float = Field(ge=1, le=10, description="Alignment with brand tone, style, and voice guidelines")
    structure: float = Field(ge=1, le=10, description="Compliance with content-type formatting requirements")
    accuracy: float = Field(ge=1, le=10, description="Factual correctness and claim validation")
    violations: List[str] = Field(default_factory=list, description="Specific violations found in the content")
    reasoning: str = Field(default="", description="Detailed reasoning for scores")

    # Internal weights for convenience (excluded from LLM schema)
    weights: Dict[str, float] = Field(
        default_factory=lambda: {"accuracy": 1.2, "brand_voice": 0.9, "structure": 0.9},
        exclude=True
    )

    @property
    def scores(self) -> Dict[str, float]:
        """Per-dimension scores as a dict."""
        return {"brand_voice": self.brand_voice, "structure": self.structure, "accuracy": self.accuracy}

    @property
    def overall_assessment(self) -> str:
        """Alias for reasoning."""
        return self.reasoning

    @property
    def average_score(self) -> float:
        """Weighted average using configured weights (canonical numeric score)."""
        w = self.weights
        total = (w.get("accuracy", 1.0) + w.get("brand_voice", 1.0) + w.get("structure", 1.0)) or 1.0
        return (
            self.brand_voice * w.get("brand_voice", 1.0) +
            self.structure * w.get("structure", 1.0) +
            self.accuracy * w.get("accuracy", 1.0)
        ) / total

    @property
    def meets_threshold(self) -> bool:
        """Static threshold check (kept only for backward-compatibility)."""
        return all([self.brand_voice >= 8, self.structure >= 8, self.accuracy >= 8])


# ---------------------------
# Content Evaluator
# ---------------------------

class ContentEvaluator:
    """Evaluate generated content using either reflection or rubric patterns.

    Notes
            - Brand is not stored on the instance; provide ``brand`` and
                ``brand_config`` for each call to keep state explicit.
            - Execution parameters (model, pattern, temperature, system message)
                are provided per call to avoid hidden state.
    """

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        # Default weights sourced from Critique schema
        try:
            field_info = Critique.model_fields["weights"]
            if getattr(field_info, "default_factory", None):
                self.default_weights = field_info.default_factory()
            else:
                self.default_weights = field_info.default
        except Exception:
            self.default_weights = {"accuracy": 1.2, "brand_voice": 0.9, "structure": 0.9}
        self.rubric: Optional[EvaluationRubric] = None

    def evaluate_content(
        self,
        *,
        content: str,
        brand: str,
        brand_config: dict,
        content_type: Optional[str],
        history: Optional[List[Dict]] = None,
        model: Optional[str] = None,
        pattern: Optional[str] = None,              # "reflection" | "evaluator_optimizer"
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        system_message: Optional[str] = None
    ) -> Tuple[Critique, dict]:
        """Evaluate content quality using the selected pattern.

        Args:
            content: Text to evaluate.
            brand: Brand identifier for rubric and messaging.
            brand_config: Full brand configuration dict.
            content_type: Optional content type key used for rubric selection.
            history: Conversation history for reflection pattern.
            model: Model name to use for evaluation.
            pattern: One of "reflection" or "evaluator_optimizer".
            max_tokens: Max output tokens for evaluator call.
            temperature: Sampling temperature for evaluator call.
            system_message: Optional override for system message.

        Returns:
            Tuple of (Critique, metadata) where metadata includes cost, latency,
            and token counts.
        """
        if not pattern:
            raise ValueError("evaluation pattern must be provided ('reflection' or 'evaluator_optimizer').")
        if not model:
            raise ValueError("evaluation model must be provided.")

        if pattern == "reflection":
            if not history:
                raise ValueError("history must be provided for 'reflection' evaluation.")
            return self._evaluate_with_reflection(
                content=content,
                history=history,
                model=model,
                max_tokens=max_tokens or 800,
                temperature=temperature if temperature is not None else 0.3,
            )

        if pattern == "evaluator_optimizer":
            return self._evaluate_with_rubric(
                content=content,
                brand=brand,
                brand_config=brand_config,
                content_type=content_type or "POST",
                model=model,
                max_tokens=max_tokens or 1200,
                temperature=temperature if temperature is not None else 0.3,
                system_message=system_message or "You are a rigorous content evaluator. Score and explain.",
            )

        raise ValueError(f"Unknown evaluation pattern: {pattern!r}")

    # -------------
    # Internals
    # -------------
    def _generate_rubric(self, *, brand: str, brand_config: dict, content_type: str) -> EvaluationRubric:
        """Build rubric based on brand_config and content_type."""
        voice = brand_config.get("voice", {}) or {}
        formatting = brand_config.get("formatting_rules", {}) or {}

        # Normalize for matching on template keys
        ct_key = (content_type or "").upper()
        if "LONG_POST" in ct_key:
            content_requirements = formatting.get("long_post_requirements", []) or []
        elif "BLOG_POST" in ct_key:
            content_requirements = formatting.get("blog_post_requirements", []) or []
        elif "NEWSLETTER" in ct_key:
            content_requirements = formatting.get("newsletter_requirements", []) or []
        else:
            # Default to short post requirements if 'POST' is present; else empty
            content_requirements = formatting.get("post_requirements", []) if "POST" in ct_key else []

        weights = dict(self.default_weights)

        return EvaluationRubric(
            brand_voice=RubricDimension(
                description="Alignment with brand tone, voice, and style guidelines",
                criteria={
                    "positioning": brand_config.get("positioning", ""),
                    "tone": voice.get("tone", ""),
                    "style_guidelines": voice.get("style_guidelines", []),
                    "banned_terms": voice.get("banned_terms", []),
                    "content_generation_rules": brand_config.get("content_generation_rules", []),
                },
                weight=float(weights.get("brand_voice", 1.0)),
            ),
            structure=RubricDimension(
                description=f"Content organization and formatting for {content_type}",
                criteria={"content_type": content_type, "requirements": content_requirements},
                weight=float(weights.get("structure", 1.0)),
            ),
            accuracy=RubricDimension(
                description="Factual correctness and claim validation",
                criteria={
                    "factual_accuracy": brand_config.get("factual_accuracy", []),
                    "content_generation_rules": brand_config.get("content_generation_rules", []),
                },
                weight=float(weights.get("accuracy", 1.2)),
            ),
            metadata=RubricMetadata(
                brand=brand,
                config_version=brand_config.get("version", "1.0"),
                generated_at=datetime.datetime.now().isoformat(),
                content_type=content_type,
            ),
        )

    def save_rubric(self, path: str) -> None:
        """Persist the last generated rubric to YAML for inspection/versioning."""
        if not self.rubric:
            raise ValueError("No rubric has been generated yet.")
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as f:
            yaml.dump(self.rubric.model_dump(), f, default_flow_style=False, sort_keys=False)

    def _format_rubric_for_prompt(self) -> str:
        """Format the current rubric (without metadata) as YAML for the LLM prompt."""
        if not self.rubric:
            raise ValueError("Rubric is not set; cannot format for prompt.")
        return yaml.dump(
            self.rubric.model_dump(exclude={"metadata"}),
            default_flow_style=False,
            sort_keys=False,
        )

    def _build_critique_prompt(self, *, content: str) -> str:
        """
        Build the critique prompt that includes:
          - The content to evaluate
          - The YAML-formatted rubric
        """
        rubric_yaml = self._format_rubric_for_prompt()
        return f"""Evaluate the following content against the brand rubric.

CONTENT TO EVALUATE:
{content}

EVALUATION RUBRIC:
{rubric_yaml}

Rate each dimension 1-10 where:
- 9-10: Exceptional adherence to all criteria
- 7-8: Good adherence with minor issues
- 5-6: Acceptable but notable violations
- 3-4: Multiple violations or critical failure
- 1-2: Fundamental misalignment with criteria

For brand_voice: Check tone, style guidelines (including opening/hook rules if present), banned terms, and content generation rules.
For structure: Check content-type-specific formatting requirements (length, headers, paragraphs, etc.).
For accuracy: Check factual claims are sourced/qualified, no fabricated statistics, no invented links.

Identify specific violations with examples from the post.
Provide detailed reasoning for each score.
"""

    # Pattern: reflection
    def _evaluate_with_reflection(
        self,
        *,
        content: str,
        history: List[Dict[str, str]],
        model: str,
        max_tokens: int,
        temperature: float
    ) -> Tuple[Critique, dict]:
        """Evaluate against brand guidance present in conversation history (no rubric scoring)."""
        messages = list(history)
        messages.append({
            "role": "user",
            "content": f"Evaluate the following content against the brand guidelines.\n\nContent:\n{content}"
        })

        result = self.llm_client.get_completion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=Critique,
        )

        metadata = {
            "cost": result.cost,
            "latency": result.latency,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
        }
        return result.structured_output, metadata

    # Pattern: evaluator_optimizer (rubric-based)
    def _evaluate_with_rubric(
        self,
        *,
        content: str,
        brand: str,
        brand_config: dict,
        content_type: str,
        model: str,
        max_tokens: int,
        temperature: float,
        system_message: Optional[str],
    ) -> Tuple[Critique, dict]:
        """Evaluate content against a rubric derived from brand_config and content_type."""
        self.rubric = self._generate_rubric(brand=brand, brand_config=brand_config, content_type=content_type)

        critique_prompt = self._build_critique_prompt(content=content)

        final_system_message = system_message or "You are a rigorous content evaluator. Score and explain."
        if "{banned_terms}" in final_system_message:
            banned_terms = (brand_config.get("voice", {}) or {}).get("banned_terms", []) or []
            banned_terms_formatted = "\n   ".join(f"- {term}" for term in banned_terms)
            final_system_message = final_system_message.format(banned_terms=banned_terms_formatted)

        messages = [
            {"role": "system", "content": final_system_message},
            {"role": "user", "content": critique_prompt},
        ]

        result = self.llm_client.get_completion(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format=Critique,
        )

        metadata = {
            "cost": result.cost,
            "latency": result.latency,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
        }
        return result.structured_output, metadata