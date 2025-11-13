# Agentic AI Examples

## Overview
Welcome to the Agentic AI Examples repository! This is a collection of agentic AI implementations I am building as part of my work as an independent Cloud & AI Solutions Architect. Each example demonstrates end-to-end system design, from evaluation frameworks to production deployment, with a focus on enterprise patterns: governance, security, observability, and cost control.

**Background**: I've spent several years building production-grade systems in regulated environments. These examples document my systematic exploration of agentic AI orchestration (LangGraph, CrewAI, multi-agent patterns) applied to real-world use cases, using the same production rigor I've applied in enterprise delivery.

These examples are built through **Evaluation-Driven Development (EDD)**—I define success metrics before writing code, test alternatives with real data, and make architectural decisions based on evidence, not assumptions. Everything here is shared publicly to demonstrate methodology, technical rigor, and transferable patterns for regulated industries (finance, healthcare, legal).

Whether you're a technical leader evaluating AI implementations, an AI engineer learning production patterns, or a consultant building client systems, these examples show what "production-ready" actually means: HITL approvals, RAG grounding, audit trails, cost monitoring, and security layers from day one.

**This repo is for sharing examples only**—no contributions or pull requests are accepted. If you find these useful, star the repo, fork it for personal use, or connect with me on LinkedIn.

## Available Examples
Below is a curated list of examples, organized by folder. Each includes a brief description, key patterns demonstrated, and direct link to detailed documentation.

| Example | Description | Key Patterns | Link |
|---------|-------------|--------------|------|
| **Marketing Team (Agentic Content Generation)** | Production agentic system generating LinkedIn content for two brands (B2B AI consulting + B2C cosmetics). Built over 12 weeks using EDD methodology with systematic testing: pattern comparison (single-pass vs reflection vs eval-optimizer), framework evaluation (LangGraph vs CrewAI), model selection (Claude Sonnet 4 vs GPT-4o configurations). Demonstrates dual-brand transferability and RAG-augmented strategy adjustment. Uses marketing as low-risk sandbox to master agentic orchestration with enterprise-grade rigor. | • Evaluation-Driven Development<br>• HITL approval workflows<br>• RAG grounding (PostgreSQL+pgvector)<br>• Azure Content Safety integration<br>• Cost monitoring (<€2/post target, achieved €0.054)<br>• Automated performance tracking (LinkedIn analytics)<br>• Strategy adjustment via RAG (not model retraining)<br>• Multi-brand isolation<br>• LangGraph supervisor pattern (100% routing accuracy)<br>• Framework-agnostic architecture | [/marketing-team](/marketing-team) |

## How to Use
1. **Clone the Repo:** `git clone https://github.com/yourusername/agentic-ai-examples.git`
2. **Navigate to Example:** Each folder contains its own comprehensive README.md with:
   - Architecture overview
   - Setup instructions
   - Testing methodology
   - Decision rationale (why we chose X over Y, backed by data)
   - Results and metrics
   - Lessons learned (what worked, what didn't, enterprise transferability)
3. **Reproduce/Adapt:** Examples include Jupyter notebooks, sanitized configs, and deployment guides
4. **Feedback:** Connect on LinkedIn or DM me with questions (no issues/PRs here)

## Methodology: Evaluation-Driven Development

All examples follow EDD principles (industry standard for production ML/AI systems):

**1. Define Success Metrics First**
- Quality thresholds (e.g., ≥7/10 on human rubric)
- Cost targets (e.g., <€2/post)
- Latency requirements (e.g., <60s generation)
- Business outcomes (e.g., >2% engagement rate)

**2. Test Alternatives with Real Data**
- Sample sizes for directional confidence (10-20 pieces per condition)
- Controlled comparisons (same topics, different approaches)
- Statistical validation where meaningful
- Transparent testing methodology (documented in weekly reports)

**3. Make Data-Driven Decisions**
- Document decision criteria before testing
- Choose based on evidence, not assumptions or vendor claims
- Transparent trade-offs (cost vs quality, simplicity vs features)
- All architectural choices validated through systematic testing

**4. Production Patterns from Day One**
- HITL approvals (human-in-the-loop governance)
- RAG grounding (prevent hallucinations with retrieval-augmented generation)
- Observability (full audit trails with decision lineage)
- Cost monitoring (real-time tracking, budget enforcement)
- Security layers (Azure Content Safety: Prompt Shield, content moderation, groundedness detection)

**5. Continuous Evaluation**
- AI-as-a-judge (scaled quality scoring)
- Performance tracking (engagement metrics, business outcomes)
- Drift detection (quality degradation alerts)
- Strategy adjustment via RAG (update retrieval context, not model retraining)

**Production bias from Day 1**: Everything runs with logs, budgets, and evidence. Local-first for cost efficiency during testing; Azure parity for enterprise deployment patterns.

## What You Won't Find Here

**No toy demos.** Every example runs in production (or is production-ready with deployment guides). No "hello world" agentic systems.

**No hype.** Transparent methodology, including failures and trade-offs. If something didn't work, I document why (with data).

**No vendor lock-in.** Examples use Azure (my expertise), but patterns transfer to AWS, GCP, or on-prem. Architecture decisions documented with alternatives considered.

**No "trust me" claims.** Every architectural choice backed by data from systematic testing. Numbers, not opinions. Decision rationale transparent.

**No overnight builds.** Each example documents realistic timelines (weeks, not days). Shows iterative refinement through testing phases.

## License
MIT License – see [LICENSE](/LICENSE) for details.

## Connect & Level Up

**Questions or ideas?** Reach out on LinkedIn: https://www.linkedin.com/in/manuel-tomas-estarlich/

**Need help with AI implementation?** I offer:
- 30-minute architecture audits (free; limited slots)
- Enterprise agentic AI assessments (strategy + blueprint, 2 weeks)
- Pilot implementations (custom agentic workflows, 4-6 weeks)

## Contact
Manuel Tomas Estarlich  
LinkedIn: https://www.linkedin.com/in/manuel-tomas-estarlich/  

---

**If you're trying to get AI past compliance and into production, these examples show the patterns that work.**

Proven in regulated environments. Now applied to agentic orchestration. Documented transparently.

