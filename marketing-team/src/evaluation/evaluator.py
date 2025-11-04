from pydantic import BaseModel, Field, ConfigDict
from utils.llm_client import LLMClient
from typing import Dict, Optional, List, Any
from pathlib import Path
import datetime
import yaml

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


class EvaluationRubric(BaseModel):
    """Complete evaluation rubric."""
    brand_voice: RubricDimension
    structure: RubricDimension
    accuracy: RubricDimension
    metadata: RubricMetadata


class Critique(BaseModel):
    """Structured critique output."""
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

    # Internal field - not part of LLM schema
    weights: Dict[str, float] = Field(
        default_factory=lambda: {"accuracy": 1.2, "brand_voice": 0.9, "structure": 0.9},
        exclude=True,  # This tells Pydantic to skip it in schema generation
        description="Internal weights for score calculation"
    )
    
    @property
    def scores(self) -> Dict[str, float]:
        """Return scores as dict for easier access."""
        return {
            'brand_voice': self.brand_voice,
            'structure': self.structure,
            'accuracy': self.accuracy
        }
    
    @property
    def overall_assessment(self) -> str:
        """Alias for reasoning."""
        return self.reasoning
    
    @property
    def average_score(self) -> float:
        """Weighted average using configured weights."""
        w = self.weights
        total_weight = sum(w.values())
        return (
            self.brand_voice * w['brand_voice'] +
            self.structure * w['structure'] +
            self.accuracy * w['accuracy']
        ) / total_weight
    
    @property
    def meets_threshold(self) -> bool:
        """Check if all dimensions meet quality threshold."""
        return all([self.brand_voice >= 8, self.structure >= 8, self.accuracy >= 8])


class ContentEvaluator:
    """Evaluate generated content against brand guidelines provided in history or brand rubric"""

    def __init__(self, llm_client: LLMClient, brand_config: dict):
        self.llm_client = llm_client
        self.brand_config = brand_config
        self.brand_name = brand_config.get("name", "Unknown")

       # Get default weights from Critique model (fallback to explicit defaults)
        try:
            field_info = Critique.model_fields["weights"]
            if getattr(field_info, "default_factory", None):
                default_weights = field_info.default_factory()
            else:
                default_weights = field_info.default
        except Exception:
            default_weights = {"accuracy": 1.2, "brand_voice": 0.9, "structure": 0.9}

        # Per-dimension weights (sourced from Critique defaults)
        self.weights: Dict[str, float] = dict(default_weights)

        # Extract banned terms for system prompt
        self.banned_terms = brand_config['voice']['banned_terms']

    def evaluate_content(self, content: str, content_type: Optional[str], history: Optional[List[Dict]] = None, model: str = "anthropic/claude-sonnet-4", pattern: str = "reflection") -> tuple[Critique, dict]:
        """
        Evaluate content quality against content-type-specific rubric.
        
        Args:
            content: Generated content to evaluate
            content_type: Type of content ("post", "long_post", "blog_post", "newsletter")
            history: Conversation history (for reflection pattern)
            model: LLM model to use
            pattern: "reflection" or "evaluator_optimizer"
        
        Returns:
            Tuple of (Critique object, metadata dict with cost/latency)
        """

        if pattern == "reflection":
            if history is None or len(history) == 0:
                raise ValueError("History must be provided for reflection evaluation.")
            return self._evaluate_with_reflection(content=content, history=history, model=model)
        elif pattern == "evaluator_optimizer":
            return self._evaluate_with_rubric(content=content, content_type=content_type, model=model)
        else:
            raise ValueError(f"Unknown evaluation pattern: {pattern}")
        
    def _generate_rubric(self, content_type: str) -> EvaluationRubric:
        """Generate rubric from config sections."""
        voice = self.brand_config.get("voice", {})
        formatting = self.brand_config.get("formatting_rules", {})

        content_requirements = ""
        if "long_post" in content_type:
            content_requirements = formatting.get('long_post_requirements', [])
        elif "blog_post" in content_type:
            content_requirements = formatting.get('blog_post_requirements', [])
        elif "post" in content_type:
            content_requirements = formatting.get('post_requirements', [])
        elif "newsletter" in content_type:
            content_requirements = formatting.get('newsletter_requirements', [])

        evaluation_rubric = EvaluationRubric(
            brand_voice=RubricDimension(
                description="Alignment with brand tone, voice, and style guidelines",
                criteria={
                    "positioning": self.brand_config.get("positioning", ""),
                    "tone": voice.get("tone", ""),
                    "style_guidelines": voice.get("style_guidelines", []),
                    "banned_terms": voice.get("banned_terms", []),
                    "content_generation_rules": self.brand_config.get("content_generation_rules", [])
                },
                weight=float(self.weights.get('brand_voice', 0.0))
            ),
            structure=RubricDimension(
                description=f"Content organization and formatting for {content_type}",
                criteria={
                    "content_type": content_type,
                    "requirements": content_requirements
                },
                weight=float(self.weights.get('structure', 0.0))
            ),
            accuracy=RubricDimension(
                description="Factual correctness and claim validation",
                criteria={
                    "factual_accuracy": self.brand_config.get("factual_accuracy", []),
                    "content_generation_rules": self.brand_config.get("content_generation_rules", [])
                },
                weight=float(self.weights.get('accuracy', 0.0))
            ),
            metadata=RubricMetadata(
                brand=self.brand_name,
                content_type=content_type,
                config_version=self.brand_config.get("version", "1.0"),
                generated_at=datetime.datetime.now().isoformat()
            )
        )

        return evaluation_rubric
    
    def save_rubric(self, path: str):
        """
        Save generated rubric to file for inspection/version control.
        
        Includes metadata for traceability.
        
        Args:
            path: File path (e.g., "generated_rubrics/levelup_v1.0.yaml")
        """
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w") as f:
            yaml.dump(
                self.rubric.model_dump(),
                f,
                default_flow_style=False,
                sort_keys=False
            )
            
    def _format_rubric_for_prompt(self) -> str:
        """
        Format rubric for LLM prompt—simple YAML dump.
        Excludes metadata (not needed for evaluation).
        """
        rubric = yaml.dump(
            self.rubric.model_dump(exclude={'metadata'}),
            default_flow_style=False,
            sort_keys=False
            )

        return rubric
              
    def _build_critique_prompt(self, content: str) -> str:
        """
        Build critique prompt with rubric.
        
        Note: We don't need to specify JSON schema in prompt—
        response_format=Critique handles that automatically.
        """
        rubric_yaml = self._format_rubric_for_prompt()

        critique_prompt = f"""Evaluate the following content against the brand rubric.
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
            Provide detailed reasoning for each score."""        

        return critique_prompt
    
    # Reflection: passes history, no rubric scoring
    def _evaluate_with_reflection(self, content: str, history: List[Dict[str, str]], model: str) -> tuple[Critique, dict]:
        """
        Evaluate content against brand guidelines provided in history.

        Args:
            content: Generated content to evaluate
            history: List of messages exchanged in the conversation
            model: LLM model to use for evaluation

        Returns:
            Tuple of (Critique object, metadata dict with cost/latency)
        """
        messages = history.copy()
        messages.append({
            "role": "user",
            "content": f"Evaluate the following content against the brand guidelines. \n\nContent:\n{content}"
        })
        
        # Call LLM to get critique - returns CompletionResult with structured Critique
        result = self.llm_client.get_completion(
            model=model,
            messages=messages,
            temperature=0.3,
            response_format=Critique
        )
        
        # Return both the critique and the cost/latency metadata
        metadata = {
            "cost": result.cost,
            "latency": result.latency,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens
        }
        return result.structured_output, metadata
    

    def _evaluate_with_rubric(self, content: str, content_type: str, model: str) -> tuple[Critique, dict]:
        """
        Evaluate content against brand rubric.

        Args:
            content: Generated content to evaluate
            rubric: Rubric to evaluate against

        Returns:
            Tuple of (Critique object, metadata dict with cost/latency)
        """
        
        # Generate rubric for this evaluation
        self.rubric = self._generate_rubric(content_type)

        banned_terms_formatted = "\n   ".join(f"- {term}" for term in self.banned_terms)

        critique_prompt = self._build_critique_prompt(content)

        system_message = "You are a marketing content evaluator"

        # Load system message template from brand config and format with banned terms
        template: Optional[str] = self.brand_config.get("evaluation_system_message")
        if template:
            # use .format_map to avoid KeyError if some placeholders are missing
            system_message = template.format_map({
                "banned_terms": banned_terms_formatted
            })

        messages = [
                {"role": "system", "content": system_message}, 
                {"role": "user", "content": critique_prompt}
            ]

        # Call LLM to get critique - returns CompletionResult with structured Critique
        result = self.llm_client.get_completion(
            # model=model,
            model="openai/gpt-4o",
            messages=messages,
            temperature=0.3,
            response_format=Critique
        )

        # Return both the critique and the cost/latency metadata
        metadata = {
            "cost": result.cost,
            "latency": result.latency,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens
        }
        return result.structured_output, metadata
