"""Content generation executor for Microsoft Agent Framework workflows.

This module defines a thin, framework-agnostic executor that will
delegate to the shared `ContentGenerator` used across orchestration
stacks. A separate node function is responsible for:

- Reading `ContentThreadState` from the Agent Framework thread
- Extracting topic/brand/template/use_cot/iteration metadata and
  tool_contexts from state (typically via `ResearchResult`)
- Calling this executor
- Writing `content` and `generation_metadata` back to state

The actual generation logic (how we call `ContentGenerator` and
assemble configs) is intentionally left for manual implementation and
will be reviewed afterward for alignment with the LangGraph
`content_generation_node`.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional
import logging

from src.core.generation.content_generator import ContentGenerator

logger = logging.getLogger(__name__)


class ContentGenerationAgent:
	"""Pure content generation executor.

	This class is responsible only for taking normalized inputs
	(topic, brand, brand_config, tool_contexts, template, etc.) and
	delegating to `ContentGenerator`. It does not know about threads or
	workflow runtime types.
	"""

	def __init__(
		self,
		content_generator: ContentGenerator,
		content_generation_config: Dict[str, Any],
	) -> None:
		"""Initialize the executor with shared ContentGenerator and config.

		Args:
			content_generator: Shared ContentGenerator instance.
			content_generation_config: Base generation config for this brand
				(typically `brand_config["models"]["content_generation"]`).
		"""

		self.content_generator = content_generator
		self.content_generation_config = content_generation_config

	async def run(
		self,
		topic: str,
		brand: str,
		brand_config: Dict[str, Any],
		tool_contexts: Dict[str, str],
		template: str,
		use_cot: bool,
		iteration_count: int,
		meets_quality_threshold: bool,
		pattern: Optional[str] = None,
	) -> Dict[str, Any]:
		"""Run one content generation pass.

		This method is intentionally scaffolded; the internal logic
		should mirror the behavior of the LangGraph
		`content_generation_node`, including:

		- Handling regeneration vs. first-pass based on
		  `iteration_count` and `meets_quality_threshold`
		- Deciding which system message/config to apply
		- Calling `ContentGenerator.generate_from_context(...)`

		Returns:
			A dict containing at least `content` and
			`generation_metadata` keys, suitable for persisting onto
			`ContentThreadState` by the calling node.
		"""

		logger.info(
			f"[ContentGenerationAgent] run called: topic='{topic}', brand='{brand}', iteration={iteration_count}, pattern={pattern}"
		)

		# Make a local effective config we can override safely
		effective_generation_config = deepcopy(self.content_generation_config)

		# If we're in a regeneration loop and last evaluation did not meet threshold,
		# use the optimization system message for this generation turn.
		if iteration_count > 0 and not meets_quality_threshold:
			optimization_model_config = brand_config.get("models", {}).get("content_optimization", {})
			optimization_system_message = optimization_model_config.get("system_message")
			if optimization_system_message:
				logger.info("Using optimization system message for regeneration turn")
				effective_generation_config["system_message"] = optimization_system_message

		# Always single-pass here (loop is handled by evaluation node)
		requested_pattern = pattern
		if requested_pattern and requested_pattern != "single_pass":
			logger.warning(f"Agentic path ignores pattern={requested_pattern}; using single_pass")
		pattern = "single_pass"

		# This node performs exactly one generation pass per cycle
		max_iterations = 1

		# Pass full optimization model config so evaluator-optimizer internal loop can use it if pattern demands
		optimization_config = brand_config.get("models", {}).get("content_optimization", {})

		# Call ContentGenerator (agentic path; unified return shape)
		result = self.content_generator.generate_from_context(
			topic=topic,
			brand=brand,
			brand_config=brand_config,
			tool_contexts=tool_contexts,
			template=template,                 # string key; generator resolves to template object
			use_cot=use_cot,
			pattern=pattern,
			max_iterations=max_iterations,
			generation_config=effective_generation_config,  # may include optimization system message override
			optimization_config=optimization_config,        # used for evaluator-optimizer internal loop
		)

		content = result["content"]
		generation_metadata = result.get("metadata", {})

		logger.info(
			f"[ContentGenerationAgent] Generated content: length={len(content)} chars, pattern='{pattern}', iteration={iteration_count}"
		)

		return {
			"content": content,  
			"generation_metadata": generation_metadata,
		}

