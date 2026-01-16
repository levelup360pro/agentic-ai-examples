# OWASP Top 10 for Agentic Applications 2026 — Security Mapping (Public Version)

This document maps the system architecture against the [OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/), the most actionable security framework for agentic AI systems.

---

## Scope, threat model, and invariants

### Scope (what this system is)
- **Standalone** application (not a multi-tenant agent platform; no public developer API product).
- **Internal users only** authenticated via Entra ID (Easy Auth).
- Produces **draft marketing content**; **no auto-publish** and no destructive/financial actions.

### Implementation scope (repo)
- Runtime code under:
  - `examples/marketing_team/src/`
  - `examples/marketing_team/application/`
  - `examples/marketing_team/alembic/`

### Security invariants
- Two HITL gates exist and are enforced:
  - Gate 1: approve/reject idea before workflow runs
  - Gate 2: approve/reject/regenerate before content is marked approved for publish
- **PII redaction** occurs at workflow boundaries:
  - post Gate 1 (external input) before agentic processing
  - post-RAG (research summaries) before downstream generation/evaluation
  - HITL feedback (incl. regeneration) is also redacted before persistence and before reaching any LLM/tool
- **Single workload identity:** the system runs in **one container** with a **Managed Identity assigned at the Container App level**.
- **Static tool surface:** tools are code-defined; no dynamic tool discovery (no MCP servers; no A2A federation).

---

## Coverage summary (fully covered vs partial vs not applicable)

Legend:
- ✅ **Covered (bank‑grade for this use case)**: implemented controls materially mitigate OWASP risk paths in this system.
- ⚠️ **Partially covered**: strong mitigations exist, but OWASP's full set includes controls not implemented or not applicable without extra complexity.
- ⛔ **Mitigated by design / Not applicable**: primary attack surface is removed by architecture.

| ASI | Risk | Coverage | Rationale (conservative) |
|---|---|---:|---|
| ASI01 | Agent Goal Hijack | ✅ | HITL gates + no auto-publish / no high-impact actions + boundary sanitisation + audit traces reduce impact and aid detection. |
| ASI02 | Tool Misuse & Exploitation | ✅ | Researcher-only tool access + strict domain allowlist + per-run quotas + ToolGuard allow/deny logging + kill switch/quarantine + egress controls. |
| ASI03 | Identity & Privilege Abuse | ⚠️ | Strong baseline (Entra + MI + least privilege + audit), but single workload MI shared by monolith prevents per-component principal isolation / task-scoped identities. |
| ASI04 | Agentic Supply Chain Vulnerabilities | ⚠️ | Strong partial: no MCP/A2A/dynamic tools + lockfile + digest pin + SBOM + provenance pointers + corpus version pointer + run quarantine. Not claiming signed provenance/attestation enforcement. |
| ASI05 | Unexpected Code Execution (RCE) | ⛔ | No code execution tools/sinks; outputs are content only. |
| ASI06 | Memory & Context Poisoning | ✅ | Curated corpus + provenance pointers + corpus version pointer + operational ability to rebuild/clear KB + run quarantine + post-RAG sanitisation + no shared memory across sessions. |
| ASI07 | Insecure Inter-Agent Communication | ⛔ | No external inter-agent federation/protocol; orchestration is internal to monolith. |
| ASI08 | Cascading Failures | ✅ | HITL + serialised execution + per-run quotas + quarantine + kill switch + observability. |
| ASI09 | Human-Agent Trust Exploitation | ✅ | HITL + evaluation outputs + provenance/governance metadata + trace JSON + identity attribution; no auto-publish. |
| ASI10 | Rogue Agents | ✅ | No federation/registration + constrained tools + kill switch/quarantine + auditable traces; scope limits rogue behaviours. |

---

## Detailed mapping by OWASP ASI item (controls + residual risks)

## ASI01 — Agent Goal Hijack
**OWASP risk:** Manipulated inputs (prompt injection, poisoned content, deceptive tool output) redirect goals/plans/actions.

**Controls implemented**
- Two HITL gates; no auto-publish and no autonomous high-impact actions.
- PII boundary redaction at entry and post-RAG.
- Content Safety on LLM calls in the intended production path (Azure AI Foundry).
- Append-only traces reconstruct planning/research/generation/evaluation and HITL actions.

**Residual risk**
- Human manipulation remains possible (see ASI09).
- Non-PII malicious content may still degrade draft quality or waste compute.

---

## ASI02 — Tool Misuse & Exploitation
**OWASP risk:** Legit tools used unsafely (exfiltration, unsafe chaining, loop amplification, unintended actions).

**Controls implemented**
- **Least agency**: tools are code-defined; only Researcher invokes tools.
- **Strict allowlist**: web research uses Tavily only and is constrained via per-brand `include_domains`.
- **ToolGuard runtime governance**:
  - schema/argument validation (fail closed)
  - actor-based allow/deny
  - per-run quotas (web/RAG/total) enforced at tool boundary
  - allow/deny decision events recorded (policy hash, usage snapshot)
- **Containment**: kill switch disables automation; quarantine contains suspicious runs.
- **Observability**: tool decisions and counters persisted in traces.

**Residual risk**
- Allowed domains can still host incorrect/misleading content; mitigated via evaluation + HITL review.
- Tool misuse is reduced but not conceptually eliminable in any system; detection relies on traces/quarantine thresholds.

---

## ASI03 — Identity & Privilege Abuse
**OWASP risk:** Delegation chains, confused deputy, cached creds, authorization drift, synthetic identity injection.

**Controls implemented**
- Entra ID (Easy Auth) for humans.
- Managed Identity for service-to-service; least privilege assigned via Terraform.
- Private networking for data services (as configured in infra).
- Kill switch/quarantine for rapid containment; append-only traces for accountability.

**Accurate architectural note**
- The system is a **single-container monolith**. The Managed Identity is attached at the Container App level and shared by all in-process modules. There is no agent-to-agent credential delegation chain because agents are in-process modules, but there is also no per-agent principal isolation.

**Residual risk**
- A compromise within the container process can use the Managed Identity's granted privileges until revoked.
- This is mitigated by least privilege, constrained tool surface, and operational containment, but it is not the same as task-scoped/JIT permissions.

---

## ASI04 — Agentic Supply Chain Vulnerabilities
**OWASP risk:** Third-party tools/agents/artifacts are malicious/compromised; dynamic runtime composition increases attack surface.

**Controls implemented (strong partial)**
- No MCP/A2A, no dynamic tool loading, no external agent registry.
- Dependency pinning:
  - `requirements.lock.txt` (pinned + hashed) is the build source of truth.
  - Docker base image digest pinned.
- SBOM generation (source + built image) in CI (`.github/workflows/sbom.yml`) with artifacts.
- Provenance pointers in traces (config/prompt/template/model/retrieval/tool_policy_hash/corpus pointer).
- Corpus version pointer + operational ability to rebuild/clear KB; quarantine applies to runs.

**Residual risk (not claimed)**
- SBOM provides **visibility**, not cryptographic integrity enforcement.
- Not claiming signed provenance/attestation verification gates (e.g., cosign/SLSA) in CI/CD.

---

## ASI05 — Unexpected Code Execution (RCE)
**OWASP risk:** Agent-triggered code execution via shell/eval, unsafe serialization, tool chains.

**Mitigated by design**
- No shell/eval/exec tools.
- Outputs are content (markdown), not executed instructions.

**Residual risk**
- Ensure no downstream consumer treats content as executable config.

---

## ASI06 — Memory & Context Poisoning
**OWASP risk:** Persistent poisoning of context (RAG/vector DB/memory) influencing future decisions.

**Controls implemented**
- Curated corpus (governed).
- Provenance pointers + corpus version pointer per run (in trace).
- Corpus version pointer + operational ability to rebuild/clear KB; quarantine applies to runs.
- Post-RAG sanitisation of research summaries.
- No shared memory across users/sessions (as designed).

**Residual risk**
- Human error in corpus updates remains possible; mitigated by provenance + corpus version pointer + review process.

---

## ASI07 — Insecure Inter-Agent Communication
**OWASP risk:** Spoofing/tampering/replay of inter-agent messages across MCP/A2A/message buses.

**Mitigated by design**
- No external inter-agent protocols or federation.
- Internal orchestration in monolith; no peer discovery layer.

**Residual risk**
- If future architecture adds external agents or message buses, implement authn/authz/integrity/anti-replay.

---

## ASI08 — Cascading Failures
**OWASP risk:** Fault propagation across steps/agents/tools causing fan-out, storms, widespread harm.

**Controls implemented**
- HITL gates break automation chains.
- Serialised workflow execution (mutex) reduces fan-out.
- Per-run tool quotas prevent tool loop amplification.
- Kill switch + quarantine provides rapid containment.
- Observability and traces support investigation and rollback.

**Residual risk**
- Misconfigured quotas or overly permissive thresholds could weaken containment; monitor and tune.

---

## ASI09 — Human-Agent Trust Exploitation
**OWASP risk:** Persuasive outputs and fake explainability lead humans to approve harmful actions.

**Controls implemented**
- Mandatory HITL approvals; no auto-publish.
- Evaluation outputs + provenance/governance metadata + trace JSON visible to reviewer.
- Append-only status history (not cryptographically immutable) + identity attribution via Entra GUID.

**Residual risk**
- Human factors remain: reviewers can still be persuaded. Mitigate with UI cues that emphasise system-generated provenance/risk flags over model rationales.

---

## ASI10 — Rogue Agents
**OWASP risk:** Misaligned/malicious agents that persist, sabotage, replicate, or collude.

**Controls implemented (for this scope)**
- No external agent registration/federation.
- Static tool surface; only Researcher can invoke tools.
- Kill switch halts automation; quarantine contains suspicious workflows.
- Full traces enable detection and forensic attribution.

**Residual risk**
- If an attacker compromises the runtime, they can attempt misuse within the bounds of the monolith identity; mitigated by least privilege + containment controls.

---

## Future hardening (not required at the moment for this use case)

If scope expands (platformization, higher-stakes actions):
- Split into two Container Apps with separate Managed Identities (orchestrator vs worker) to strengthen ASI03.
- Add signed provenance/attestations and verification gates (cosign/SLSA) to strengthen ASI04.
- Add explicit message integrity if inter-agent messaging/external federation is introduced (ASI07).

---

## Framework Reference

- **Framework:** OWASP Top 10 for Agentic Applications 2026
- **Version:** December 2025
- **Source:** [genai.owasp.org](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)
- **Related:** OWASP Top 10 for LLM Applications 2025, OWASP Agentic AI Threats & Mitigations Guide