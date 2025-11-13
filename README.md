# LevelUp360 Agentic Marketing System

**Production-grade agentic AI system for dual-brand content generation, built through Evaluation-Driven Development.**

**Status**: Week 4 Complete — LangGraph Multi-Agent System  
**Methodology**: Data-driven architecture decisions through systematic testing  
**Deployment**: Local development (Weeks 1-4) → Azure production (Weeks 5+)

---

## What I'm Building

A production agentic marketing system that generates LinkedIn content for two real brands (AI consulting + cosmetics), designed to **enterprise production standards**:

**Core Capabilities**:
- **Quality-First**: >7/10 content quality (human rubric), >2% engagement target (stretch >3%)
- **Cost-Efficient**: <€2 per post operational cost
- **Production-Grade**: HITL approvals, observability, cost monitoring, evaluation pipelines
- **Enterprise Security**: Azure Content Safety (Prompt Shield, Content Moderation, Groundedness Detection)
- **Performance Tracking**: Automated Facebook + LinkedIn analytics with insights embedded as retrieval context for adaptive decision-making
- **Data-Driven**: All architectural decisions validated through systematic testing with real content

**Technical Stack** (Locked After Testing):
- **Orchestration**: LangGraph supervisor pattern (100% routing accuracy, Week 4 winner)
- **Pattern**: Eval-optimizer (8.56/10 avg quality, Week 3 winner)
- **Model**: Claude Sonnet 4 with reference post (9.5/10 narrative quality, Week 3 winner)
- **Grounding**: RAG with Chroma (local) → PostgreSQL + pgvector (production) for brand knowledge; text-embedding-3-small (1536D)
- **Search**: Tavily AI-first search API for LLM-optimized evidence retrieval
- **Security**: Azure Content Safety (Prompt Shield, Content Moderation, Groundedness Detection)
- **Analytics**: Automated Facebook + LinkedIn post performance tracking with agentic learning
- **Multi-Brand Isolation**: Separate PostgreSQL tables per brand (zero cross-contamination)
- **Deployment**: Azure Container Apps (Staging + Production) with Application Insights monitoring

**Why This Approach**:
- **Evaluation-Driven Development**: Define success metrics BEFORE building, test alternatives with data
- **Transparent Methodology**: Share testing process, decision rationale, outcomes weekly
- **Production Patterns**: Implements evaluation pipelines, logging, cost tracking, drift detection from Day 1
- **Transferable**: Same patterns map to enterprise use cases (finance, healthcare, compliance)

---

## Repository Structure: Week-by-Week Branches

**Each week has its own Git branch** with complete code, notebooks, and setup instructions specific to that week's focus:

### **Week Branches**

| Branch | Focus | Status | Key Deliverables |
|--------|-------|--------|------------------|
| `week-01` | Evaluation framework, infrastructure setup | ✅ Complete | Three-environment strategy, decision criteria, evaluation rubrics |
| `week-02` | RAG system + baseline testing | ✅ Complete | Chroma vector store, 40-post corpus, Tavily search, brand guidelines refinement |
| `week-03` | Orchestration patterns + model selection | ✅ Complete | Single-pass/reflection/eval-optimizer testing, Claude Sonnet 4 selection, cross-brand validation |
| `week-04` | LangGraph multi-agent system | ✅ Complete | Supervisor pattern, 100% routing accuracy, framework-agnostic architecture, config-driven system |
| `week-05` | CrewAI integration + framework comparison | 🔄 In Progress | CrewAI implementation, LangGraph vs CrewAI objective comparison |
| `week-06` | Production deployment | 📅 Planned | Azure Container Apps, PostgreSQL + pgvector, HITL approval UI |
| `week-07` | Observability + monitoring | 📅 Planned | Application Insights, LangSmith tracing, cost monitoring, quality drift detection |
| `week-08` | End-to-end validation | 📅 Planned | Staging testing, dual-brand workflows, performance validation |

### **How to Use Week Branches**

Each week branch is **self-contained** with:
- Complete working code for that week's implementation
- Jupyter notebooks with setup instructions and testing methodology
- Week-specific `requirements.txt` (dependencies may evolve week-to-week)
- Configuration files and sample data
- Detailed README with environment setup for that week

**To work with a specific week**:

```bash
# Clone the repository
git clone <repository-url>
cd agentic-ai-marketing-team

# Checkout the week you want to explore
git checkout week-04  # For Week 4 LangGraph implementation

# Follow that week's setup instructions
# (each week's notebooks contain setup steps)
```

**Why separate branches?**
- Each week builds on previous learnings but may refactor significantly
- Week 3 tested patterns → Week 4 implemented winner (eval-optimizer)
- Week 4 tested LangGraph → Week 5 tests CrewAI → one will be chosen for production
- Branches preserve working code at each stage (no breaking changes when refactoring)

---

## Weekly Reports (Design Decisions + Results)

Detailed week reports are published in this repository documenting:
- Design decisions (architecture, patterns, tools)
- Testing methodology (scenarios, criteria, sample sizes)
- Results (quality scores, cost, latency, insights)
- Lessons learned (what worked, what didn't, enterprise transferability)

| Week | Report | Key Outcomes |
|------|--------|--------------|
| **Week 1** | [WEEK1.md](WEEK1.md) | Evaluation framework, three-environment strategy, decision criteria |
| **Week 2** | [WEEK2.md](WEEK2.md) | RAG system (Chroma, 40-post corpus), Tavily search, corpus testing (25% → 100% retrieval success) |
| **Week 3** | [WEEK3.md](WEEK3.md) | Orchestration pattern testing (60 pieces), eval-optimizer winner (8.56/10), model selection (Claude Sonnet 4), evaluation system calibration |
| **Week 4** | [WEEK4.md](WEEK4.md) | LangGraph supervisor pattern, 100% routing accuracy (22/22 scenarios), framework-agnostic architecture, config-driven system (4.3x ROI) |
| **Week 5** | WEEK5.md | *In progress* - CrewAI integration, framework comparison |

---

## Why This Approach: Patterns Over Tools

**The use case is marketing (what I actually need). The patterns are enterprise.**

This system demonstrates enterprise production-grade AI patterns that transfer directly to regulated industries:

| Pattern | Marketing Implementation | Enterprise Translation |
|---------|-------------------------|------------------------|
| **HITL Approvals** | Human reviews content before publishing | Compliance officer approves financial advice, legal reviews contracts |
| **RAG Grounding** | Brand guidelines + past posts context | Policy documents + regulatory requirements grounding |
| **Security Layers** | Prompt Shield + Content Moderation + Groundedness Detection | Jailbreak prevention, harmful content filtering, hallucination detection for regulated outputs |
| **Agentic Routing** | Supervisor analyzes topic → selects tools (RAG, web search, both, neither) | Risk engine analyzes transaction → routes to fraud detection, compliance check, manual review |
| **Evaluation Pipelines** | Quality scoring (clarity, brand voice, accuracy) | Risk scoring (compliance, bias detection, hallucination checks) |
| **Cost Monitoring** | Per-post cost tracking (<€2 target) | Per-transaction budget enforcement |
| **Observability** | Full decision audit trail (what was generated, why, by whom) | Regulatory audit trail (explainability, version control) |
| **Drift Detection** | Content quality degradation monitoring | Model performance degradation in production |
| **Multi-Brand Isolation** | Separate PostgreSQL tables per brand (zero cross-contamination) | Separate tenant data stores (HIPAA, GDPR compliance for multi-client deployments) |

**Production Bias**: Everything runs with logs, budgets, and evidence. Local-first for cost efficiency; Azure parity for enterprise deployment.

---

## Methodology: Evaluation-Driven Development

Based on Chip Huyen's AI Engineering principles.

**Core Tenet**: "Define what 'good' looks like BEFORE you build, and use those definitions to guide model selection, design, deployment, and iteration."

**Our Application**:
- Week 1: Define evaluation criteria (four pillars, rubric, metrics)
- Weeks 2-4: Test alternatives systematically (prompts/RAG, patterns, frameworks)
- Decision framework: Choose based on data (quality scores, cost, latency)
- Weeks 5+: Build with confidence; monitor continuously
- Publication: Share transparent testing process and outcomes

**Key Validation Results**:
- Week 3: Eval-optimizer pattern wins (8.56/10 avg quality vs 8.20/10 reflection)
- Week 3: Claude Sonnet 4 + reference wins (9.5/10 vs 8.5/10 without reference)
- Week 4: LangGraph supervisor achieves 100% routing accuracy (22/22 scenarios, 110/110 runs)
- Week 4: Framework-agnostic architecture enables objective Week 5 comparison (same business logic, different orchestration)

---

## Quick Start (Week-Specific)

**Setup depends on which week you're exploring.** Each week branch contains:
- Week-specific `requirements.txt`
- Jupyter notebooks with setup instructions
- Configuration examples

**General pattern** (adapt per week):

```bash
# 1. Checkout the week branch
git checkout week-04  # Example: Week 4 LangGraph

# 2. Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# OR
.\.venv\Scripts\Activate.ps1  # Windows PowerShell

# 3. Install dependencies
pip install -U pip
pip install -r requirements.txt

# 4. Configure environment
# Copy .env.example to .env and add your API keys
# (see week's README for required keys)

# 5. Run week's notebooks
# Open notebooks/weekXX_*.ipynb
# Follow setup cells for that week's specific requirements
```

**Required API Keys vary by week**

---

## Architecture Philosophy

### **Three-Environment Strategy**

**Local Development (Weeks 1-4)**:
- **Purpose**: Rapid experimentation, pattern/framework/model testing
- **LLM**: OpenRouter API (GPT-4o-mini, GPT-4o, Claude Sonnet 4) for flexible model testing
- **Vector Store**: Chroma (local file) with text-embedding-3-small (1536D)
- **Search**: Tavily web search integration for evidence-based content
- **Testing**: Jupyter notebooks with systematic evaluation (10-20 pieces per condition)
- **Cost**: ~€18.40 for Weeks 1-4 testing phase

**Staging Deployment (Week 6+)**:
- **Purpose**: Production-parity validation before release
- **LLM**: Azure OpenAI (GPT-4o + Claude Sonnet 4 based on Week 3 selection)
- **Vector Store**: PostgreSQL + pgvector (1536D, persistent)
- **Platform**: Azure Container Apps (stateless, scalable)
- **Monitoring**: Application Insights (full observability)
- **Testing**: End-to-end validation, HITL approval workflow, cost/latency verification

**Production Deployment (Week 6+)**:
- **Purpose**: Live content generation with strict governance
- **Stack**: Same as Staging (consistency guaranteed)
- **Differences**: Separate resources, stricter RBAC, production secrets, higher availability targets
- **Monitoring**: Application Insights + alerting on quality drift, cost overruns, failures

---

## Success Metrics

### Technical
- Content quality (human rubric): ≥ 7/10 average ✅ **Achieved**: 8.56/10 (Week 3)
- Technical generation cost: < €2 per post ✅ **Achieved**: €0.054/post (Week 4)
- Generation latency: < 60 seconds ✅ **Achieved**: <40s (Week 4)
- Routing accuracy: 100% ✅ **Achieved**: 22/22 scenarios (Week 4)

### Business (Weeks 6+)
- Content published: 50+ pieces (both brands)
- Engagement rate: >2% target (accept baseline in Month 2)
- Page views: +30%
- Gig inquiries: 1-2 (assessments/pilots)
- Network growth: +50 relevant connections

### Learning
- Skills assessment: Avg 8.8/10 across competencies (Week 4)
- Testing notebooks: 6+ published (transparent methodology)
- Case studies: 2 planned (LevelUp360, cosmetics brand)
- Principles adherence: 100% data-driven decisions ✅ **Maintained**

---

## What I'll Share vs What Stays Private

### **Public (This Repository)**
- Weekly reports documenting design decisions, testing results, outcomes
- Week branches with complete code and notebooks (setup instructions per week)
- Architecture diagrams and technical documentation
- Sanitized brand configs and evaluation rubrics
- Public tool adapters (web search, RAG interfaces)
- Cost and performance metrics from local and Azure environments
- Case studies with real engagement data

### **Private (Not Included)**
- Proprietary prompt engineering "personalities"
- Detailed brand content and competitive intelligence
- Production secrets, API keys, Azure resource IDs
- Client-specific customizations and governance rules
- Advanced evaluation logic and threshold tuning
- Full Azure infrastructure as code (Terraform)

**Why the Split**: Public content demonstrates methodology and capability (consulting value). Private content is implementation-specific IP.

---

## About

This repository documents a 12-week journey building a production agentic marketing system through Evaluation-Driven Development.

### Target Audience
- **AI Engineers/Architects**: Production patterns (evaluation, observability, cost control)
- **Security Architects**: Patterns translate directly to compliance-sensitive workloads
- **Technical Leaders**: Data-driven AI architecture methodology
- **Consultants**: Transferable patterns for enterprise AI delivery

### Value Proposition
The system serves two real brands and generates actual published content. The patterns demonstrated (approvals, RAG grounding, observability, cost guards, secure deployment, agentic routing with governance) translate directly to compliance-sensitive workloads in finance, healthcare, insurance, and legal industries.

### Core Message
Patterns, not tools. If I trust these patterns with my own brand, you can trust them for your regulated workloads.

---

## License
MIT — see LICENSE

## Contact
Manuel Tomas Estarlich  
LinkedIn: https://www.linkedin.com/in/manuel-tomas-estarlich/
