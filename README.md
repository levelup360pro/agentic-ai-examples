# Agentic AI Examples

## Overview

This is a collection of agentic AI implementations I'm building as an independent Cloud & AI Solutions Architect. Each example demonstrates **how to design and validate enterprise-grade AI systems**—from evaluation frameworks to production deployment—with focus on governance, security, observability, and cost control.

**Background**: I've spent 10+ years building production systems in regulated environments. These examples document my systematic exploration of agentic AI orchestration (LangGraph, CrewAI, multi-agent patterns) applied to real-world use cases, using the same production rigor I've applied in enterprise delivery.

## What Makes These Examples Different

All examples follow **Evaluation-Driven Development (EDD)**—I define success metrics before writing code, test alternatives with real data, and make architectural decisions based on evidence, not assumptions or vendor claims.

**What you'll find here**:
- **Methodology over tools** — How to validate AI systems work before production deployment
- **Enterprise patterns proven in regulated delivery** — HITL approvals, RAG grounding, audit trails, cost monitoring, security layers embedded from Day 1 (not retrofitted after pilots fail)
- **Transparent testing** — Real data, real decisions, real trade-offs documented (what worked, what didn't, why)
- **Production rigor applied to learning** — Same governance standards I'd use for client work, applied while mastering new orchestration frameworks

**Target audience**: IT/Business leaders evaluating AI implementation approaches, solutions architects designing enterprise systems, compliance/security teams needing governance patterns for regulated AI deployments.

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

## Enterprise Patterns Demonstrated

These examples show patterns I've applied in regulated delivery—now proven with agentic orchestration:

| Pattern | Marketing Example Implementation | Where I've Applied This Before | Enterprise Translation (Other Domains) |
|---------|----------------------------------|-------------------------------|----------------------------------------|
| **HITL Approvals** | I review content before publishing to brands | Compliance workflows in finance (approval gates for products/advice) | Legal contract review, medical diagnosis validation, regulatory filings |
| **RAG Grounding** | Brand guidelines + past posts context for content generation | Policy/regulatory document grounding for compliant outputs | Healthcare protocols, legal precedents, financial regulations, compliance manuals |
| **Security Layers** | Azure Content Safety (Prompt Shield, moderation, groundedness detection) | Production AI security patterns in regulated environments | Jailbreak prevention for customer-facing AI, hallucination detection for advice systems, adversarial input filtering |
| **Agentic Routing** | LangGraph supervisor analyzes topic → selects tools (RAG, web search, both, neither) | N/A (new—agentic orchestration is the skill expansion) | Risk engine analyzes transaction → routes to fraud detection, compliance check, manual review based on risk signals |
| **Performance Tracking** | Automated LinkedIn analytics with RAG-based strategy adjustment | Transaction outcome tracking with retrieval-augmented decision-making in enterprise ML | A/B testing results fed back to decision systems, real-time performance monitoring with adaptive logic |
| **Cost Monitoring** | Per-post cost tracking (<€2 target, achieved €0.054) | Cost controls for production ML inference at scale | Per-transaction budget enforcement, ROI tracking for AI operations, infrastructure cost optimization |
| **Observability** | Full decision audit trail (what was generated, why, context used, which agents involved) | Production logging/tracing for regulatory audit requirements (model decisions, data lineage) | Explainability for loan denials, medical decisions, trading algorithms, regulatory compliance audits |
| **Drift Detection** | Content quality degradation monitoring over time (automated metric tracking) | Model performance monitoring in production systems (accuracy decay, data distribution shifts) | Fraud model accuracy drift, recommendation quality degradation, fairness metric decay |
| **Multi-Brand Isolation** | Separate PostgreSQL tables per brand (zero cross-contamination) | Multi-client data isolation in regulated SaaS delivery (GDPR, data residency compliance) | HIPAA-compliant healthcare systems, GDPR-compliant EU data handling, financial services client separation |

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