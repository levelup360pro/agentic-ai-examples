# Agentic AI Examples

## Overview
Welcome to the Agentic AI Examples repository! This is a collection of production-grade agentic AI implementations I've built as part of my work as an independent Cloud & AI Solutions Architect. Each example demonstrates end-to-end system design, from evaluation frameworks to production deployment, with a focus on enterprise patterns: governance, security, observability, and cost control.

These examples are built through Evaluation-Driven Development (EDD)—I define success metrics before writing code, test alternatives with real data, and make architectural decisions based on evidence, not assumptions. Everything here is shared publicly to demonstrate methodology, technical rigor, and transferable patterns for regulated industries (finance, healthcare, legal).

Whether you're a technical leader evaluating AI implementations, an AI engineer learning production patterns, or a consultant building client systems, these examples show what "production-ready" actually means: HITL approvals, RAG grounding, audit trails, cost monitoring, and security layers from day one.

This repo is for sharing examples only—no contributions or pull requests are accepted. If you find these useful, star the repo, fork it for personal use, or connect with me on LinkedIn.

## Available Examples
Below is a curated list of examples, organized by folder. Each includes a brief description, key patterns demonstrated, and direct link to detailed documentation.

| Example | Description | Key Patterns | Link |
|---------|-------------|--------------|------|
| **Marketing Team (Agentic Content Generation)** | Production-grade agentic system generating LinkedIn content for two brands (B2B AI consulting + B2C cosmetics). Built over 12 weeks using EDD methodology. Demonstrates: pattern testing (single-pass vs reflection vs evaluator-optimizer), framework comparison (LangGraph vs CrewAI), model selection (GPT-4o-mini vs hybrid configs), dual-brand transferability, and RAG-augmented strategy adjustment. | • Evaluation-Driven Development<br>• HITL approval workflows<br>• RAG grounding (PostgreSQL+pgvector)<br>• Azure Content Safety integration<br>• Cost monitoring (<€2/post target)<br>• Automated performance tracking (Facebook/LinkedIn APIs)<br>• Strategy adjustment via RAG (not model retraining)<br>• Multi-brand isolation<br>• Gradio demo UI | [/marketing-team](/marketing-team) |

## How to Use
1. **Clone the Repo:** `git clone https://github.com/yourusername/agentic-ai-examples.git`
2. **Navigate to Example:** Each folder contains its own comprehensive README.md with:
   - Architecture overview
   - Setup instructions
   - Testing methodology
   - Decision rationale (why we chose X over Y)
   - Results and metrics
   - Lessons learned
3. **Reproduce/Adapt:** Examples include Jupyter notebooks, sanitized configs, and deployment guides
4. **Feedback:** Connect on LinkedIn or DM me with questions (no issues/PRs here)

## Methodology: Evaluation-Driven Development

All examples follow EDD principles:

**1. Define Success Metrics First**
- Quality thresholds (e.g., ≥7/10 on human rubric)
- Cost targets (e.g., <€2/post)
- Latency requirements (e.g., <60s generation)
- Business outcomes (e.g., >2% engagement rate)

**2. Test Alternatives with Real Data**
- Sample sizes for directional confidence (10 pieces per condition)
- Controlled comparisons (same topics, different approaches)
- Statistical validation where possible

**3. Make Data-Driven Decisions**
- Document decision criteria before testing
- Choose based on evidence, not assumptions
- Transparent trade-offs (cost vs quality, simplicity vs features)

**4. Production Patterns from Day One**
- HITL approvals (human-in-the-loop governance)
- RAG grounding (prevent hallucinations)
- Observability (full audit trails)
- Cost monitoring (real-time tracking)
- Security layers (Azure Content Safety, RBAC)

**5. Continuous Evaluation**
- AI-as-a-judge (scaled quality scoring)
- Performance tracking (engagement metrics)
- Drift detection (quality degradation alerts)
- Strategy adjustment via RAG (not model retraining)

## Enterprise Patterns Demonstrated

These examples show patterns that transfer directly to regulated industries:

| Pattern | Marketing Example | Enterprise Translation |
|---------|-------------------|------------------------|
| **HITL Approvals** | Human reviews content before publishing | Compliance officer approves financial advice, legal reviews contracts |
| **RAG Grounding** | Brand guidelines + past posts context | Policy documents + regulatory requirements grounding |
| **Security Layers** | Prompt Shield + Content Moderation + Groundedness Detection | Jailbreak prevention, harmful content filtering, hallucination detection for regulated outputs |
| **Performance Tracking** | Automated Facebook/LinkedIn analytics with RAG-based strategy adjustment | Transaction outcome tracking with retrieval-augmented decision-making |
| **Cost Monitoring** | Per-post cost tracking (<€2 target) | Per-transaction budget enforcement |
| **Observability** | Full decision audit trail (what was generated, why, by whom) | Regulatory audit trail (explainability, version control) |
| **Multi-Brand Isolation** | Separate PostgreSQL tables per brand (zero cross-contamination) | Separate tenant data stores (HIPAA, GDPR compliance for multi-client deployments) |

## What You Won't Find Here

**No toy demos.** Every example runs in production (or is production-ready). No "hello world" agentic systems.

**No hype.** Transparent methodology, including failures and trade-offs. If something didn't work, I document why.

**No vendor lock-in.** Examples use Azure (my expertise), but patterns transfer to AWS, GCP, or on-prem. Architecture decisions documented with alternatives considered.

**No "trust me" claims.** Every architectural choice backed by data from testing. Numbers, not opinions.

## License
MIT License – see [LICENSE](/LICENSE) for details.

## Connect & Level Up

**Questions or ideas?** Reach out on LinkedIn: https://www.linkedin.com/in/manuel-tomas-estarlich/

**Need help with AI implementation?** I offer:
- 30-minute architecture audits (free; limited slots)

## Contact
Manuel Tomas Estarlich  
LinkedIn: https://www.linkedin.com/in/manuel-tomas-estarlich/  

**If you're trying to get AI past compliance and into production, these examples show the patterns that work.**