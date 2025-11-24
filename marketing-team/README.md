# LevelUp360 Agentic Marketing System

**Systematic exploration of agentic AI orchestration (Microsoft Agent Framework, LangGraph, CrewAI) for enterprise delivery, applied to dual-brand marketing use case.**

**Context**: Expanding my enterprise AI delivery capabilities (10+ years building production systems in regulated environments) into agentic orchestration patterns. Using marketing as a low-risk sandbox to master Microsoft Agent Framework/LangGraph/CrewAI with the same production rigor I've applied in finance/compliance workloads.

**Status**: Week 6 Complete — v1.0-reference released (public code frozen, private hardening begins)  
**Methodology**: Evaluation-Driven Development (data-driven architecture decisions—enterprise standard)  
**Deployment Path**: Local reference implementation complete → Azure production (Weeks 7+ private)

---

## What I'm Building

An **agentic marketing system** serving two real brands (my AI consulting practice LevelUp360 + partner's cosmetics brand), built with **the same production-grade patterns I've used in enterprise delivery for 10+ years**—now applied to agentic orchestration frameworks (LangGraph, CrewAI).

### Why Marketing as the Use Case?

**Low-risk sandbox** to master agentic frameworks while applying enterprise rigor I already know from regulated delivery (evaluation pipelines, cost budgets, HITL approvals, security layers, observability, drift detection).

Marketing generates real published content (not academic), but stakes are lower than finance/healthcare—safe environment to systematically test orchestration frameworks before applying to higher-stakes client work.

### What's Familiar (Enterprise Patterns I've Delivered Before)

These patterns are **proven in my production work** (finance, compliance, regulated ML systems). I'm applying them here to validate they work with agentic orchestration:

- ✅ **Evaluation-Driven Development**: Define metrics before building, test systematically, choose based on data (not opinions)
- ✅ **Cost Controls**: Runtime budget enforcement, per-operation tracking (achieved €0.054/post Week 4 vs <€2 target)
- ✅ **Security Layers**: Azure Content Safety integrated from Day 1 (Prompt Shield, content moderation, groundedness detection)
- ✅ **HITL Approval Workflows**: Human-in-the-loop governance before any output goes live
- ✅ **Full Observability**: Application Insights monitoring, decision audit trails, lineage tracking
- ✅ **Drift Detection**: Quality degradation monitoring over time (automated alerts on metric decay)
- ✅ **Multi-Tenant Isolation**: Separate PostgreSQL tables per brand (zero cross-contamination—GDPR/compliance pattern)

### What's New (Agentic AI Tooling I'm Systematically Testing)

This is the **skill expansion** focus—mastering agentic orchestration frameworks through hands-on testing:

- 🔄 **LangGraph supervisor patterns**: 100% routing accuracy achieved Week 4 (22/22 scenarios, 110/110 runs)
- 🔄 **CrewAI hierarchical orchestration**: Week 5 testing in progress (objective comparison vs LangGraph)
- 🔄 **Multi-agent coordination strategies**: Eval-optimizer pattern winner Week 3 (8.56/10 avg quality vs 8.20 reflection, 7.64 single-pass)
- 🔄 **Framework-agnostic architecture**: Same business logic, swappable orchestration—enables objective comparison without refactoring

### Technical Stack (v1.0-reference)

- **Orchestration**: Microsoft Agent Framework (primary, Week 6) with custom typed state model; LangGraph (alternative implementation for comparison)
- **Pattern**: Eval-optimizer (8.56/10 avg quality, Week 3 winner)
- **Model**: Claude Sonnet 4 with reference post (9.5/10 narrative quality, Week 3 winner)
- **Grounding**: RAG with ChromaDB (local/reference) for brand knowledge; text-embedding-3-small (1536D)
- **Search**: Tavily AI-first search API for LLM-optimized evidence retrieval
- **UI**: Gradio 5.33.1 (simple functional interface for brand config, document ingestion, content generation)
- **Future (Private)**: Azure Container Apps, PostgreSQL + pgvector, Azure Content Safety, Application Insights

### Core Capabilities (Validated Metrics)

- **Quality-First**: >7/10 content quality via human rubric evaluation ✅ **Achieved**: 8.56/10 (Week 3)
- **Cost-Efficient**: <€2 per post operational cost ✅ **Achieved**: €0.054/post (Week 4)
- **Performance**: <60s generation latency ✅ **Achieved**: <40s (Week 4)
- **Routing Accuracy**: 100% correct tool selection ✅ **Achieved**: 22/22 scenarios (Week 4)
- **Production-Grade**: HITL approvals, observability, cost monitoring, evaluation pipelines (enterprise standard)

---

## Repository Structure: Week-by-Week Branches

**Each week has its own Git branch** with complete code, notebooks, and setup instructions specific to that week's focus:

### Week Branches

| Branch | Focus | Status | Key Deliverables |
|--------|-------|--------|------------------|
| `week-01` | Evaluation framework, infrastructure setup | ✅ Complete | Three-environment strategy, decision criteria, evaluation rubrics |
| `week-02` | RAG system + baseline testing | ✅ Complete | Chroma vector store, 40-post corpus, Tavily search, brand guidelines refinement |
| `week-03` | Orchestration patterns + model selection | ✅ Complete | Single-pass/reflection/eval-optimizer testing, Claude Sonnet 4 selection, cross-brand validation |
| `week-04` | LangGraph multi-agent system | ✅ Complete | Supervisor pattern, 100% routing accuracy, framework-agnostic architecture, config-driven system |
| `week-05` | Framework comparison + Microsoft Agent Framework adoption | ✅ Complete | CrewAI evaluation (rejected: LangChain dependency), Microsoft Agent Framework validation (custom LLMClient + state passing), Design decision #21: Microsoft Agent Framework for production |
| `week-06` | Microsoft Agent Framework + Gradio UI | ✅ Complete | Custom typed state model, executor/agent separation, simple functional UI, v1.0-reference release |
| `week-07+` | Production hardening (private) | 🔒 Private | Azure deployment, HITL workflows, advanced features, governance automation, observability (insights shared, code private) |

### How to Use Week Branches

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
- Week 5 tested CrewAI → Early rejection + Microsoft Agent Framework evaluation → Microsoft Agent Framework chosen for production
- Branches preserve working code at each stage (no breaking changes when refactoring)

---

## Weekly Reports (Design Decisions + Results)

Detailed week reports are published in this repository documenting:
- Design decisions (architecture, patterns, tools)
- Testing methodology (scenarios, criteria, sample sizes)
- Results (quality scores, cost, latency, insights)
- Lessons learned (what worked, what didn't, enterprise transferability)


| Week | Report | Key Outcomes |
|------|--------|--------------||
| **Week 1** | [WEEK1.md](/marketing-team/reports/WEEK1.md) | Evaluation framework, three-environment strategy, decision criteria |
| **Week 2** | [WEEK2.md](/marketing-team/reports/WEEK2.md) | RAG system (Chroma, 40-post corpus), Tavily search, corpus testing (25% → 100% retrieval success) |
| **Week 3** | [WEEK3.md](/marketing-team/reports/WEEK3.md) | Orchestration pattern testing (60 pieces), eval-optimizer winner (8.56/10), model selection (Claude Sonnet 4), evaluation system calibration |
| **Week 4** | [WEEK4.md](/marketing-team/reports/WEEK4.md) | LangGraph supervisor pattern, 100% routing accuracy (22/22 scenarios), framework-agnostic architecture, config-driven system (4.3x ROI) |
| **Week 5** | [WEEK5.md](/marketing-team/reports/WEEK5.md) | Framework comparison (CrewAI rejected, Microsoft Agent Framework adopted), custom agent validation, Decision #21: production orchestration choice |
| **Week 6** | [WEEK6.md](/marketing-team/reports/WEEK6.md) | Microsoft Agent Framework migration, custom typed state model, Gradio UI, v1.0-reference release, transition to private hardening |

---

## Why Production Rigor for Marketing? (Enterprise Transferability)

**The use case is marketing (low-risk sandbox). The patterns are enterprise (proven in regulated delivery).**

I'm applying the same production-grade patterns I've used in highly regulatede environments to master agentic tooling in a controlled context. These patterns transfer directly—I've already delivered them in high-stakes domains; now I'm proving they work with agentic orchestration.



## Methodology: Evaluation-Driven Development

Based on **Chip Huyen's AI Engineering principles** (industry standard for production ML/AI systems):

> *"Define what 'good' looks like BEFORE you build, and use those definitions to guide model selection, design, deployment, and iteration."*

### My Application (12-Week Process)

- **Week 1**: Define evaluation criteria (four pillars: clarity, engagement, brand voice, accuracy; human rubric 1-10; metrics targets)
- **Weeks 2-4**: Test alternatives systematically (prompts/RAG configurations, orchestration patterns, frameworks)
- **Decision framework**: Choose based on data (quality scores, cost, latency measurements—not opinions or vendor claims)
- **Weeks 5+**: Build with confidence knowing choices are validated; monitor continuously for drift
- **Publication**: Share transparent testing process and outcomes (methodology transparency)

### Key Validation Results (Data-Driven Decisions)

- ✅ **Week 3**: Eval-optimizer pattern wins (8.56/10 avg quality vs 8.20/10 reflection, 7.64/10 single-pass—20-piece test per condition)
- ✅ **Week 3**: Claude Sonnet 4 + reference post wins (9.5/10 vs 8.5/10 without reference—narrative quality focus)
- ✅ **Week 4**: LangGraph supervisor achieves 100% routing accuracy (22/22 scenarios, 110/110 runs—zero misroutes)
- ✅ **Week 4**: Framework-agnostic architecture enables objective Week 5 comparison (same business logic, different orchestration—isolates framework variable)
- ✅ **Week 5**: CrewAI spike and early rejection. Strategic pivot to Microsoft Agent Framework 
- ✅ **Week 6**: Microsoft Agent Framework supervisor achieves 100% routing accuracy (22/22 scenarios, 110/110 runs—zero misroutes)

---

## Quick Start (v1.0-reference)

**The public reference implementation is now complete and frozen at v1.0-reference.** You can run the full system locally with the Gradio UI.

### Running the Gradio Application

```bash
# 1. Clone the repository
git clone https://github.com/levelup360pro/levelup360-agentic-ai-eil
cd levelup360-agentic-ai-eil

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# OR
.\.venv\Scripts\Activate.ps1  # Windows PowerShell

# 3. Install dependencies
pip install -U pip
pip install -e .  # Core framework
pip install -r examples/marketing_team/requirements.txt  # Marketing example

# 4. Configure environment
# Copy .env.example to .env and add your API keys
cp .env.example .env
# Edit .env with:
#   OPENROUTER_API_KEY=sk-...  # For LLM access
#   TAVILY_API_KEY=...         # For web search

# 5. Navigate to marketing team example
cd examples/marketing_team

# 6. Run the Gradio UI
python app.py

# 7. Access the UI
# Open browser to http://127.0.0.1:7860 (or port shown in terminal)
```

### Using the Application

**First-Time Setup (One Brand Pre-Loaded)**:

If you have exactly one brand config in `configs/` (e.g., `levelup360.yaml`), the UI auto-loads it on startup. Skip to Tab 2.

**Workflow**:

1. **Configure Your Brand** (Tab 1: Brand Configuration)
   - **Option A**: Select existing brand from dropdown → Click "Load Selected Brand"
   - **Option B**: Upload new YAML config → Auto-validates and saves to `configs/`
   - ✅ **Success**: "Active Brand Name" displays your brand; status shows green confirmation

2. **Build Knowledge Base** (Tab 2: Knowledge Base)
   - Click "Upload Documents" → Select `.md` or `.txt` files (brand guidelines, past content, reference materials)
   - Click "Process & Store" → Watch progress bar (chunking → embedding → storage)
   - ✅ **Success**: "Current Knowledge Base" shows chunk count and file list
   - **Optional**: Click "Clear/Delete All Stored Documents" to reset (keeps configs, removes chunks)

3. **Generate Content** (Tab 3: Content Generation)
   - **Enter Topic**: "AI governance best practices for enterprise leaders"
   - **Select Template**: 
     - `LINKEDIN_POST_ZERO_SHOT` (no examples)
     - `LINKEDIN_POST_FEW_SHOT` (shows example input box)
   - **Optional**: Toggle "Use Chain of Thought (CoT)" for complex reasoning
   - **Optional** (Few-Shot only): Add example posts → Click "Add Example"
   - Click **"Generate Content"** → Workflow runs (planning → research → drafting → evaluation)
   - ✅ **Output**:
     - Generated content rendered as Markdown
     - Evaluation scores (overall + per-dimension)
     - Critique reasoning explaining strengths/weaknesses
     - Full system trace (accordion) for debugging

**Tips**:
- **Multiple Brands**: Switch brands in Tab 1 → Tab 2 auto-refreshes to show that brand's knowledge base
- **Iterative Refinement**: The workflow auto-iterates up to 3 times if quality score < threshold (configurable in brand YAML)
- **Trace Inspection**: Open "Full System Trace" accordion to see every LLM call, tool execution, and routing decision
- **Cost Tracking**: Check terminal logs for per-operation cost breakdown (planning, RAG, web search, generation, evaluation)

### Exploring Week-by-Week Branches

For historical context, each week 1-6 has its own branch with complete code and notebooks:

```bash
# Checkout a specific week
git checkout week-06  # Example: Week 6 Microsoft Agent Framework implementation

# Follow that week's setup instructions in notebooks/
```

**Required API Keys**:
- **OpenRouter API**: For LLM access (GPT-4o, Claude Sonnet 4)
- **Tavily API**: For web search tool
- **Optional**: Azure OpenAI (for production Azure deployment)

---

## Architecture Philosophy

### Three-Environment Strategy (Enterprise Standard)

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
- **Purpose**: Live content generation for my brands with strict governance
- **Stack**: Same as Staging (consistency guaranteed)
- **Differences**: Separate resources, stricter RBAC, production secrets, higher availability targets
- **Monitoring**: Application Insights + alerting on quality drift, cost overruns, failures

---

## Success Metrics

### Technical (Systematic Validation)
- Content quality (human rubric): ≥ 7/10 average ✅ **Achieved**: 8.56/10 (Week 3)
- Technical generation cost: < €2 per post ✅ **Achieved**: €0.054/post (Week 4)
- Generation latency: < 60 seconds ✅ **Achieved**: <40s (Week 4)
- Routing accuracy: 100% ✅ **Achieved**: 22/22 scenarios (Week 4)

### Business (Personal Use, Weeks 6+)
- Content published: 50+ pieces (both brands)
- Engagement rate: >2% target (baseline acceptance Month 2)
- Page views: +30% on LevelUp360 site
- Network growth: +50 relevant connections (technical leaders, AI practitioners)

### Learning (Skill Expansion)
- Agentic orchestration competency: LangGraph + CrewAI mastery via hands-on testing
- Testing notebooks: 6+ published with transparent methodology
- Weekly reports: 8 weeks documented (design decisions, testing data, outcomes)
- Principles adherence: 100% data-driven decisions ✅ **Maintained** (no opinion-based framework choices)

---

## What Changes After Week 6 (v1.0-reference)

**Week 6 marks the completion of the public reference implementation.** The codebase is now frozen at **v1.0-reference**, providing a stable foundation that demonstrates production-ready agentic AI architecture.

### What's Included in v1.0-reference

- ✅ **Full Agentic Workflow**: Microsoft Agent Framework orchestration (planning → research → generation → evaluation)
- ✅ **Alternative Implementation**: LangGraph version for framework comparison
- ✅ **RAG Integration**: Complete vector store (ChromaDB), document ingestion, brand-specific retrieval
- ✅ **Evaluation Framework**: Automated critique generation, scoring, quality thresholds
- ✅ **Simple Functional UI**: Gradio application for brand configuration, document upload, content generation
- ✅ **Testing Notebooks**: End-to-end validation demonstrating routing accuracy, quality metrics, cross-brand workflows
- ✅ **Documentation**: Architecture diagrams, design decisions (Weeks 1-6), implementation guides

### What Continues (Weeks 7+: Documentation & Insights)

From Week 7 onward, the journey continues with **production hardening and operational evolution**, shared through documentation rather than code:

- ✅ **Architecture Diagrams**: Production deployment patterns, governance flows, infrastructure evolution
- ✅ **Design Decisions**: Same rigor as Weeks 1-6 (Challenge → Solution → Rationale → Impact)
- ✅ **High-Level Guides**: HITL workflows, Azure security patterns, observability strategies
- ✅ **Demos & Videos**: Live system in action (both brands, approval workflows, monitoring dashboards)
- ✅ **Metrics & Learnings**: Cost trends, quality data, operational insights from production

### What Becomes Private (Production IP)

- ❌ **Azure Infrastructure Code**: Terraform/Bicep, CI/CD pipelines, deployment scripts
- ❌ **Production Features**: Advanced functionality, admin dashboards, monitoring panels
- ❌ **Brand-Specific Tuning**: Exact scoring rubrics, proprietary prompts, competitive advantage
- ❌ **Governance Implementation**: HITL workflow code, approval automation, compliance checking
- ❌ **Proprietary Integrations**: Client-specific connectors, custom pipelines, optimizations

### Why This Boundary?

**v1.0-reference proves the capability**: "Here's a production-ready agentic system with RAG, routing, evaluation, and UI—you can run it yourself."

**Private work proves operational maturity**: Deploying at scale, securing for regulated industries, integrating into real business workflows.

This approach maximizes transparency (show how real systems evolve) while protecting competitive advantage (exact production configurations, proprietary tuning).

---

## What I'll Share vs What Stays Private

### Public (This Repository)
- Weekly reports documenting design decisions, testing results, outcomes
- Week branches with complete code and notebooks (setup instructions per week)
- Architecture diagrams and technical documentation
- Sanitized brand configs and evaluation rubrics (generic examples)
- Public tool adapters (web search, RAG interfaces, orchestration patterns)
- Cost and performance metrics from local and Azure environments
- Enterprise transferability insights (how patterns map to regulated workloads)

### Private (Not Included)
- Proprietary prompt engineering "personalities" (brand-specific voice tuning)
- Detailed brand content and competitive intelligence
- Production secrets, API keys, Azure resource IDs
- Client-specific customizations (when I take on paid work)
- Advanced evaluation logic and threshold tuning (competitive advantage)
- Full Azure infrastructure as code (Terraform—security-sensitive)

**Why the Split**: Public content demonstrates **methodology and capability** (how I apply enterprise rigor to agentic systems). Private content is **implementation-specific details** (what makes my brands unique, production secrets).

---

## About This Repository

### Background

I've spent sevaral years building production-grade systems in regulated environments. This repository documents my systematic exploration of agentic AI orchestration (LangGraph, CrewAI, multi-agent patterns) applied to a real-world marketing use case, using the same production rigor I've applied in enterprise delivery.

### Why Marketing as the Use Case?

**Low-risk sandbox** to master new tooling (agentic frameworks) while applying familiar patterns (evaluation pipelines, cost controls, security, observability). Generates real published content for two brands (my AI consulting practice LevelUp360 + partner's cosmetics), so outcomes are real—but stakes are lower than finance/healthcare, allowing safe experimentation with orchestration frameworks before applying to higher-risk client work.

### What's Demonstrated Here

- ✅ **Enterprise production patterns** applied to agentic systems (evaluation frameworks, HITL approvals, cost budgets, security layers, audit trails—proven in regulated delivery)
- ✅ **Systematic testing methodology** for agentic orchestration (60+ pieces tested Week 3, 110 routing scenarios Week 4—data-driven decisions, not vendor claims)
- ✅ **Framework-agnostic architecture** enabling objective comparisons (LangGraph vs CrewAI tested with identical business logic—isolates orchestration variable)
- ✅ **Transparent documentation** of design decisions, testing outcomes, lessons learned (12-week journey shared publicly)

### Who Might Find This Useful

- **AI architects/consultants**: See enterprise patterns (evaluation, security, cost, observability) applied to agentic orchestration—proven methodology
- **Technical leaders**: Data-driven framework selection process (test systematically, measure outcomes, choose based on evidence—not hype)
- **Security/compliance teams**: Production security patterns (Prompt Shield, groundedness detection, audit trails) validated in agentic context
- **Enterprise delivery teams**: Reference implementation for agentic systems with production rigor (evaluation-first, cost-controlled, governance-embedded)

### Core Value Proposition

If you need **agentic AI delivered with enterprise production rigor** (evaluation frameworks, cost controls, security, HITL governance, observability, compliance readiness), this repository proves I can apply both:

- ✅ **Production patterns** (already proven in regulated environments—finance, compliance, enterprise ML)
- ✅ **Agentic orchestration** (systematically tested LangGraph/CrewAI—documented with transparent methodology)

**Marketing is the sandbox. Enterprise delivery is the capability.**

Patterns transfer. Tools are swappable. Rigor is non-negotiable.

---

## License
MIT — see LICENSE

## Contact
Manuel Tomas Estarlich  
LinkedIn: https://www.linkedin.com/in/manuel-tomas-estarlich/
