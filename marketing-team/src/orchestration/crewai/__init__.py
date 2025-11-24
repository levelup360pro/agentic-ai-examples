"""CrewAI orchestration adapters for the marketing_team example.

This package contains helpers and flows that integrate the CrewAI library
with the example content-generation pipelines (planning, research,
generation, evaluation). Modules provide factory helpers for agents,
task definitions, StructuredTool adapters, and lightweight state models
for traceability.

Public API (selected)
		- config.agents: build_content_planner_agent, build_content_generator_agent, build_content_evaluator_agent
		- config.tasks: helpers to build CrewAI Task objects for planner/generator/evaluator
		- flows.content_generation_flow: CrewContentGenerationFlow orchestration class
		- states: CrewContentGenerationState, MessageEvent and helpers

Notes
		- These modules are example integrations and are intentionally
			lightweight; they are suitable for demonstration and local testing.
		- Do not treat this package as a production-grade orchestration layer.
"""
