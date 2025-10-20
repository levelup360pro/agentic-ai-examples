# Week 1: Foundation & Evaluation Framework

**Status**: Complete ✅  
**Focus**: Establish Evaluation-Driven Development methodology and architecture decisions

---

## Executive Summary

Week 1 established the methodological foundation for building a production-grade agentic marketing system. Following Chip Huyen's Evaluation-Driven Development (EDD) principle, we defined success metrics and evaluation frameworks BEFORE making architectural decisions. This directly addresses the 95% GenAI pilot failure rate by ensuring every choice is validated with data, not assumptions.

**Key Outcomes**:
- ✅ Evaluation framework designed (four pillars, 5-dimension rubric)
- ✅ Multi-method evaluation strategy defined
- ✅ Infrastructure architecture decided (APIs + PostgreSQL + pgvector)
- ✅ Testing methodology defined for Weeks 2-4
- ✅ Model selection strategy defined with decision criteria locked
- ✅ Architectural decisions deferred until data validates them

---

## Design Decisions

### **1. Methodological Approach: Evaluation-Driven Development**

**Decision**: Build system using data-driven methodology, not assumption-driven architecture.

**Rationale**:
- AI Engineering Bible core principle: "Define what 'good' looks like BEFORE building"
- Addresses root cause of 95% GenAI pilot failures (MIT 2025)
- 73% of failures trace to poor problem definition and insufficient validation

**Implications**:
- All architectural choices (except infrastructure) deferred until Week 3-4 testing validates them
- Testing integrated throughout (iterative), not batched upfront
- Every decision documented with rationale based on test results

---

### **2. Three-Environment Strategy**

**Decision**: Separate local development from testing and production deployment.

**Rationale**:
- Local environment optimized for rapid iteration
- Testing environment (replica of production) to test changes before releasing to production
- Production environment optimized for reliability and observability
- Clear metrics boundary prevents conflating development costs with operational costs

**Implementation**:

| Environment | Purpose | Key Components |
|-------------|---------|----------------|
| **Local (W1-4)** | Rapid iteration, testing | Laptop + OpenRouter API + Chroma + text-embedding-3-small (1536D) |
| **Staging (W5+)** | Production parity validation | Azure Container Apps + PostgreSQL + pgvector + Azure AI Foundry + App Insights |
| **Production (W5+)** | Live content generation | Same stack as Staging; separate resources, stricter RBAC |

---

### **3. Model Selection Strategy: Test Before Committing**

**Decision**: Defer model selection to Week 3 systematic testing; no assumptions about "best" model without data.

**Challenge**: Original plan assumed "GPT-4o-mini + optional GPT-4o" without validation. This violates Evaluation-Driven Development principles—we can't claim to prove "patterns beat model power" if we never test alternatives.

**Solution**: Week 3 (Days 6-7) will test 4 model configurations on 15 pieces each using the winning orchestration pattern:

**Configurations to Test**:
1. **Config A - GPT-4o-mini Baseline**: Single model everywhere (simplest, lowest cost)
2. **Config B - Hybrid Reasoning**: GPT-4o-mini (research/generation) + GPT-4o (evaluation/optimization)
3. **Config C - Best-in-Class**: GPT-4o-mini (research) + Claude 3.5 Haiku (generation/optimization) + GPT-4o (evaluation)
4. **Config D - GPT-4o Ceiling**: GPT-4o everywhere (quality benchmark; likely exceeds cost target)

**Decision Criteria** (locked now, before testing):
- **Primary** (must pass): Quality ≥7/10, Cost <€2/post, Latency p95 <60s, Consistency (stdev <1.5)
- **Secondary** (tie-breakers): Quality per euro, Brand voice fidelity ≥7.5, Error rate <5%, Developer experience
- **Rules**: If multiple pass, choose lowest cost. If tied on cost, choose highest quality. If tied on both, choose simplest (fewest models to manage).

**Environment Setup**:
- **Local (W1-4)**: OpenRouter API (flexible model access for testing GPT-4o-mini, GPT-4o, Claude 3.5 Haiku)
- **Staging/Production (W5+)**: Azure AI Foundry (GPT-4o-mini, GPT-4o) + Anthropic API if Config C wins

**Rationale**:
- **Aligns with EDD**: Define criteria first, test alternatives with real data, choose based on evidence
- **Reduces risk**: Avoids mid-project model switches if initial choice underperforms
- **Proves thesis**: If Config A (simplest) wins, we prove "patterns beat model power." If Config C wins, we prove quality is worth complexity—either way, decision is data-driven.
- **Time investment**: 1-2 extra days in Week 3 to test 60 pieces (15 per config) prevents weeks of rework later

**Key Principle Applied**: "Test alternatives with YOUR data before committing." We're not assuming GPT-4o-mini is good enough—we're proving it (or proving it's not).

---

### **4. Vector Store: PostgreSQL + pgvector + text-embedding-3-small**

**Decision**: Use PostgreSQL with pgvector extension for embeddings in production; text-embedding-3-small (1536D) for all embeddings.

**Alternatives Considered**: 
- Vector stores: FAISS (in-memory, Azure Files, Blob), Azure AI Search, Pinecone
- Embedding models: text-embedding-ada-002 (1536D, older), text-embedding-3-small (1536D, better quality/cost), text-embedding-3-large (3072D, higher quality but more expensive)

**Decision Rationale**:
1. **PostgreSQL + pgvector**:
   - **Cost**: Zero additional cost (already using PostgreSQL for logs/state)
   - **Persistence**: Database guarantees, survives container restarts
   - **No cold start**: Containers ready immediately
   - **Simplicity**: One database for all data (logs, content, state, embeddings)
   - **Performance**: 10-50ms query time sufficient (LLM inference dominates at 2-3s)
   
2. **text-embedding-3-small**:
   - **Quality**: Better than ada-002 on benchmarks (MTEB)
   - **Cost**: Lower per token than ada-002
   - **Dimension**: 1536D matches ada-002; no migration needed if we switch models later
   - **Adoption timing**: Immediate adoption (Week 2) avoids migration later; Chroma and pgvector both support 1536D

**Implementation**:
- **Local (W1-4)**: Chroma with text-embedding-3-small via OpenRouter/Azure AI Foundry API
- **Production (W5+)**: PostgreSQL + pgvector (VECTOR(1536)) with text-embedding-3-small via Azure AI Foundry
- **Migration**: Week 5 migrates Chroma embeddings to PostgreSQL; same model ensures compatibility

---

## Evaluation Framework

### **Four Evaluation Pillars** (Chip Huyen)

| Pillar | What We Measure | How We Measure |
|--------|-----------------|----------------|
| **Domain Capability** | AI consulting + cosmetics marketing effectiveness | Expert review, factual accuracy checks |
| **Generation Quality** | Coherence, relevance, factuality, fluency, engagement | 1-10 scoring rubric (5 dimensions) |
| **Instruction-Following** | Format compliance, brand voice, required elements | Checklist + rubric score |
| **Cost & Latency** | Cost per post (<€2), generation time (<60s) | Automated logging |

---

### **Multi-Method Evaluation Strategy**

| Method | Phase | Purpose |
|--------|-------|---------|
| **Human Scoring** | W1-4 | Gold standard for quality |
| **Multi-Criteria Rubric** | All phases | Systematic, comparable |
| **AI-as-a-Judge** | W5+ | Scales evaluation |
| **Real User Feedback** | W6+ | Business validation |

**Sample Size**: 15 examples per test condition (80% confidence in relative performance, based on OpenAI research)

---

### **Scoring Rubric (1-10 Scale)**

| Dimension | Score 3 | Score 7 | Score 10 |
|-----------|---------|---------|----------|
| **Clarity** | Confusing, jargon-heavy | Clear, accessible | Exceptionally clear |
| **Brand Voice** | Generic/off-brand | Recognizable tone | Perfect alignment |
| **CTA Strength** | Weak/missing | Clear, relevant | Compelling with urgency |
| **Technical Accuracy** | Factual errors | Accurate, current | Expert-level precision |
| **Engagement Potential** | No hook, low value | Good hook, clear value | Irresistible hook |

---

## Deferred Architectural Decisions

### **Testing-First Approach**

**Principle**: Defer decisions until testing provides data to validate choices.

| Decision | Testing Week | What We'll Test |
|----------|--------------|-----------------|
| **Orchestration Pattern** | Week 3 (Days 1-5) | Single-pass vs Reflection vs Evaluator-Optimizer |
| **Model Selection** | Week 3 (Days 6-7) | GPT-4o-mini baseline vs Hybrid vs Best-in-Class vs GPT-4o ceiling |
| **Framework Choice** | Week 4 | LangGraph vs CrewAI vs Hybrid (using winning pattern + model) |

---

### **Week 3: Orchestration Pattern Testing + Model Selection**

**Part 1: Orchestration Pattern Testing**

**Patterns to Test**:
1. **Single-Pass with HITL**: Generate → Human review → Publish (baseline)
2. **Reflection Pattern**: Generate → Self-critique → Revise → Output
3. **Evaluator-Optimizer Pattern**: Generator → Evaluator → Optimizer → Output

**Methodology**:
- Sample size: 10 content pieces per pattern (30 total)
- Evaluation: Human rubric scoring (4 manual + 6 AI-judge per pattern) + cost tracking + latency measurement
- Documentation: Jupyter notebook (week_03_pattern_comparison.ipynb)

**Decision Criteria**:
- Must achieve ≥7/10 average quality
- Must stay <€2/post
- Must complete <60 seconds
- If tie, choose simpler pattern

---

**Part 2: Model Selection Testing** 

**Configurations to Test**:
1. **Config A - GPT-4o-mini Baseline**: Single model everywhere (simplest)
2. **Config B - Hybrid Reasoning**: GPT-4o-mini (research/generation) + GPT-4o (evaluation/optimization)
3. **Config C - Best-in-Class**: GPT-4o-mini (research) + Claude 3.5 Haiku (generation/optimization) + GPT-4o (evaluation)
4. **Config D - GPT-4o Ceiling**: GPT-4o everywhere (quality benchmark)

**Methodology**:
- Sample size: 10 content pieces per configuration (40 total)
- Use winning pattern from Part 1
- Same topics across all configs (controlled comparison)
- Evaluation: Human rubric scoring (3 manual + 7 AI-judge per config) + cost tracking + latency measurement
- Documentation: Jupyter notebook (week_03_model_selection.ipynb)

**Decision Criteria**:
- **Primary** (must pass): Quality ≥7/10, Cost <€2/post, Latency p95 <60s, Consistency (stdev <1.5)
- **Secondary** (tie-breakers): Quality per euro, Brand voice fidelity ≥7.5, Error rate <5%, Developer experience (1-10 rating)
- **Rules**: If multiple pass, choose lowest cost. If tied on cost, choose highest quality. If tied on both, choose simplest (fewest models).

**Why This Matters**:
- Multi-model configurations (B, C) add integration complexity and debugging challenges
- Single-model (A) is simplest but may sacrifice quality
- Testing with real data determines optimal trade-off before committing to framework implementation in Week 4
- Prevents mid-project model switches if initial choice underperforms

---

### **Week 4: Framework Testing**

**Configurations to Test**:
1. **LangGraph-only**: Pure LangGraph implementation
2. **CrewAI-only**: Pure CrewAI implementation
3. **Hybrid**: LangGraph orchestration + CrewAI agents

**Methodology**:
- Sample size: 15 content pieces per config (45 total)
- Use winning pattern from Week 3
- Evaluate: Quality, development complexity, runtime performance, debugging ease

**Decision Criteria**:
- Quality must be equivalent (±0.5 points)
- Choose framework with best developer experience + observability
- Simplicity > features

---

## Excluded Components (Enterprise Scale Patterns)

**Principle**: Document what we're NOT building in Q1 to show informed trade-offs, not ignorance.

### **Excluded from Q1**

| Component | Enterprise Value | Q1 Decision | Rationale |
|-----------|------------------|-------------|-----------|
| **Azure API Management (APIM)** | ✅ High (API gateway, rate limiting, multi-model routing) | ❌ Exclude | Cost: $150-2,800/month = 400% over Q1 budget. Complexity: 2-3 weeks setup. **Q1 Mitigation**: Direct API calls with retry logic + basic rate limiting in code. **When Needed**: Multi-client deployments (10+ brands), SLA requirements. |
| **Hybrid Search (Azure AI Search)** | ⚠️ Medium (10-15% retrieval quality boost) | ❌ Exclude | Cost: $75-10,000+/month. Complexity: 1 week setup. **Q1 Mitigation**: Optimized pgvector search with re-ranking. **When Needed**: Complex queries at scale (>10K documents/brand). |
| **Auto-Publishing (Post-Approval)** | ⚠️ Low (saves 4 hours over 12 weeks) | ❌ Exclude | Complexity: 5-7 days OAuth + error handling. Risk: Wrong timing, format errors. **Q1 Mitigation**: Manual publishing after HITL approval. **When Needed**: High-volume clients (>20 posts/day). |

---

## Budget Allocation

**Total Available**: €450 (€150/month × 3 months)

| Phase | Estimated Cost | Details |
|-------|------|---------|
| **Weeks 1-4: Testing** | €40-60 | Pattern testing (€10-15) + Model selection (€15-20) + Framework testing (€10-15) + RAG/search baseline (€5-10) |
| **Weeks 5-8: Production** | €55-65 | Azure AI Foundry + Container Apps + PostgreSQL + App Insights |
| **Weeks 9-12: Scale** | €55-65 | Continued production + optimization |

**Note**: Model selection testing (Week 3) adds €15-20 to Month 1 budget but prevents costly mid-project model switches. Total 12-week budget remains within €450 target.

---

## Success Metrics

### **Technical Metrics**

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Content Quality** | >7/10 average | Human rubric (W1-4), AI-judge (W5+) |
| **Cost per Post** | <€2 | API cost logging |
| **Generation Latency** | <60 seconds | Timestamp tracking |
| **System Uptime** | >95% | Application Insights (production) |

### **Business Metrics**

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Content Published** | 50+ pieces | Publication log |
| **Engagement Rate** | >2% (shooting above LinkedIn organic average; stretch target >3%) | LinkedIn analytics |
| **Profile Views** | +30% increase | LinkedIn insights |
| **Gig Inquiries** | 1-2 inquiries | Outreach tracking |

---

## Next Steps (Week 2)

### **Focus**: Establish baseline performance with prompt engineering + RAG

**Key Tasks**:
1. Generate synthetic past posts (10 per brand) to seed RAG (clearly marked as placeholders)
2. Prompt template development (5 templates for different content types)
3. RAG implementation (Chroma + text-embedding-3-small)
4. Tavily AI-first search integration (LLM-optimized evidence retrieval; replaces SERPER for better RAG quality)
5. Baseline performance testing (20 content pieces: 10 per brand, half with RAG, 6 with search)
6. Early AI-judge calibration (mini-calibration on 10 manually scored pieces)
7. Analysis and Week 2 report

**Deliverables**:
- 5 prompt templates (versioned, tested)
- RAG system operational with text-embedding-3-small
- Tavily search adapter integrated (LLM-optimized results vs raw SERP)
- 20 generated content pieces with quality scores (10 manual + 10 AI-judge)
- Baseline metrics (quality, cost, latency; RAG impact quantified; Tavily vs no-search comparison)
- Testing notebook (week_02_baseline_testing.ipynb) with analysis

**Scoring Strategy** (time-boxed ≤3h manual):
- Manual scoring: 10 pieces (5 per brand)
- AI-judge scoring: 10 pieces (same rubric dimensions)
- Mini-calibration: Compare AI-judge vs human on the 10 manually scored pieces (correlation, MAE)
- Goal: Validate AI-judge for bulk scoring in Weeks 3-4 to reduce manual load

---

## Model Selection Decision Criteria

**Challenge**: Choosing models based on assumptions violates Evaluation-Driven Development principles. We can't prove "patterns beat model power" without testing alternatives.

**Solution**: Week 3 (Days 6-7) tests 4 model configurations systematically using the winning orchestration pattern.

**Decision Criteria** (defined now, applied in Week 3):

### **Primary Criteria (Must Pass)**
1. **Quality**: Average rubric score ≥7.0/10 across 15 test pieces
2. **Cost**: Total cost per post <€2 (all LLM calls combined: research, generation, evaluation, optimization)
3. **Latency**: p95 end-to-end generation time <60 seconds
4. **Consistency**: Standard deviation of quality scores <1.5 (no wild swings)

### **Secondary Criteria (Tie-Breakers)**
5. **Cost Efficiency**: Quality points per euro spent (higher is better)
6. **Brand Voice Fidelity**: Brand voice dimension score ≥7.5/10 (critical for dual-brand system)
7. **Error Rate**: <5% failures (retries, timeouts, malformed outputs)
8. **Developer Experience**: Ease of prompt tuning, output parsing, debugging (qualitative 1-10 rating)

### **Decision Rules**
- If multiple configurations pass all primary criteria: choose lowest cost
- If tie on cost: choose highest quality
- If tie on cost and quality: choose best developer experience (simplicity, fewer models to manage)
- If no configuration passes: identify the blocking criterion and iterate (extend testing by 1 day max)

### **Sample Size**
15 pieces per configuration (60 total) for 80% confidence in relative performance (per OpenAI research on evaluation sample sizes).

### **Expected Outcomes**
- **Config A wins**: Proves "patterns beat model power" (simplest model delivers with proper architecture)
- **Config B or C wins**: Proves quality/cost trade-off justifies multi-model complexity
- **Config D wins**: Re-evaluate cost target or iterate prompt optimization (unlikely; €2.50-3.50/post exceeds target)

### **Risk Mitigation**
- If multi-model config wins (B or C): Document integration complexity; implement unified logging with model identifier per step; establish fallback to Config A if error rate >5% in Week 4
- If no config passes quality gate: Extend testing 1 day; optimize prompts; re-test
- If all configs pass: Default to simplest (Config A) unless quality delta >1.0 point justifies complexity

**Why This Matters**: Model selection impacts every subsequent decision (framework implementation, production deployment, cost projections). Testing now with locked criteria prevents assumption-driven architecture and mid-project pivots.

## Conclusion

Week 1 established a methodological foundation that directly addresses the 95% GenAI pilot failure rate. By starting with evaluation criteria, deferring architectural decisions until testing provides data, and committing to transparent documentation, the project is positioned to avoid assumption-driven development pitfalls.

**Core Principle Applied**: "Define what 'good' looks like before building." We now have the framework to measure "good"—time to start generating data.

---

