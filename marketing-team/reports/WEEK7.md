# Week 7: Azure Production Infrastructure & CI/CD Pipeline

**Status**: Complete ✅
**Focus**: Azure infrastructure deployment, Terraform architecture split, CI/CD automation, and unified local/production codebase.

---

## Executive Summary

Week 7 marks the transition from local reference implementation to **production-grade Azure deployment**. Following the strategic decision to use Azure Container Apps (documented in Week 6), this week delivered the complete infrastructure foundation and automated deployment pipeline.

**Key Outcomes**:
- ✅ **Infrastructure Foundation**: Deployed full Azure infrastructure via Terraform: PostgreSQL with pgvector, Azure AI Foundry, Container Apps Environment, ACR, Key Vault, VNet with private endpoints, Managed Identities...
- ✅ **Terraform Architecture Split**: Separated Container App deployment from infrastructure project.
- ✅ **CI/CD Pipeline**: Implemented GitHub Actions workflow for automated Docker builds and Terraform-based deployments.
- ✅ **Unified Codebase**: Single `app.py` works seamlessly in both local (ChromaDB) and Azure (PostgreSQL/pgvector) environments.
- ✅ **Managed Identity Authentication**: Passwordless database access using Azure Managed Identity, eliminating credential management overhead.

**Architecture Achievement**: Built a **two-project Terraform architecture** that decouples long-running infrastructure resources  from the Container App deployment. This pattern allows independent deployment.

**Critical Discovery**: Azure AI Foundry enters an "Accepted" provisioning state that can block other resources in the same Terraform project. The `terraform_remote_state` pattern elegantly solves this by allowing the application project to read infrastructure outputs without waiting for AI Foundry state transitions.

**Production Readiness**: The infrastructure demonstrates **enterprise-ready patterns** including:
- Private endpoints for all sensitive resources (PostgreSQL, Key Vault, AI Foundry)
- VNet integration with NSG rules limiting traffic flow
- Managed identity for all service-to-service authentication
- Customer-managed keys ready for regulated environments
- Automated deployments triggered on code changes

---

## Design Decisions

### Decision 28: Separate Terraform Project for Container App Deployment

**Challenge**: AI Foundry resource enters a non-terminal "Updating" provisioning state during Terraform apply, blocking Container App deployment with a 409 Conflict error: "Cannot perform operation because resource is not in a terminal provisioning state."

**Discovery Process**:
Multiple attempts to resolve within a single Terraform project failed:
- `depends_on` with null_resource delay: AI Foundry state is non-deterministic
- Retry logic: Not natively supported in Terraform
- Extended timeouts: Still fails when AI Foundry is updating

**Solution**: **Two-Project Architecture with Remote State**.
- `infrastructure/terraform/`: Core infrastructure (VNet, PostgreSQL, AI Foundry, Container Apps Environment, ACR, Key Vault, ...)
- `application/`: Container App deployment only, reads outputs via `terraform_remote_state`

**Rationale**:
- **Independence**: Infrastructure and application have different deployment cadences. Infrastructure changes rarely; Container App changes on every code push.
- **Isolation**: AI Foundry state transitions no longer block application deployments.
- **Reusability**: Same infrastructure can support multiple application deployments.

**Impact**:
- `examples/marketing_team/application/` contains: `main.tf`, `variables.tf`, `data.tf`, `backend.tf`, `modules/container-app/`
- `data.tf`: Uses `terraform_remote_state` to read outputs from infrastructure state file
- Separate backend configurations per environment (`environments/test/`, `environments/prod/`)

**Alternative Rejected**: Continue with single Terraform project using extended timeouts and manual retries. Rejected because it's fragile, time-consuming, and doesn't scale for CI/CD automation.

---

### Decision 29: GitHub Actions Build & Deploy Workflow

**Challenge**: Automate the build and deployment process while keeping source code secure (private repository) and supporting multiple environments with destroy capability.

**Discovery Process**:
Evaluated several CI/CD approaches:
- ACR Tasks with GitHub webhook: Requires storing GitHub PAT in Azure, security risk for private repos
- Azure DevOps Pipelines: Adds another platform to manage
- Manual build and push: Error-prone, doesn't scale

**Solution**: **GitHub Actions with Local Docker Build**.
- Build job: Docker build runs in GitHub runner, pushes only the image to ACR
- Deploy job: Terraform init/plan/apply in application folder
- Destroy job: Optional teardown via workflow_dispatch

**Rationale**:
- **Security**: Source code never leaves GitHub; only built container images are pushed to ACR.
- **Traceability**: Image tags use commit SHA, enabling exact correlation between deployed code and Git history.
- **Flexibility**: Manual workflow_dispatch supports environment selection and destroy operations.

**Impact**:
- `.github/workflows/deploy-app.yml`: Three jobs (build, deploy, destroy)
- Triggers: Push to `main` with `examples/marketing_team/**` changes, or manual dispatch
- Build job: `docker build -f application/Dockerfile`, tags with commit SHA, pushes to ACR
- Secrets required: `ARM_CLIENT_ID`, `ARM_CLIENT_SECRET`, `ARM_SUBSCRIPTION_ID`, `ARM_TENANT_ID`

**Alternative Rejected**: ACR Tasks with GitHub integration. Rejected because it requires storing GitHub credentials in Azure, creating a security surface that's unnecessary when GitHub Actions can build locally.

---

### Decision 30: Unified Application Codebase for Local and Azure Deployment

**Challenge**: Maintain a single codebase that works identically in local development (ChromaDB, OpenRouter) and Azure production (PostgreSQL/pgvector, Azure AI Foundry), avoiding code drift and reducing testing burden.

**Discovery Process**:
Considered several approaches:
- Separate `app_local.py` and `app_prod.py`: High maintenance burden, code drift risk
- ChromaDB-only with external migration: Requires separate deployment artifacts
- PostgreSQL-only everywhere: Adds Docker Compose complexity for local development

**Solution**: **Environment-Driven Backend Selection**.
- Single `app.py` in `examples/marketing_team/application/`
- `VectorStore` facade selects backend via `VECTOR_STORE_TYPE` environment variable
- Config loading respects `BRAND_CONFIG_PATH` for Azure File Share mounts
- LLM provider detection via `AZURE_AIFOUNDRY_ENDPOINT` presence

**Rationale**:
- **Parity**: Identical application behavior with zero code changes between environments.
- **Simplicity**: One entry point, one Dockerfile, one deployment artifact.
- **Testability**: Local testing validates the exact code that runs in production.

**Impact**:
- `examples/marketing_team/application/app.py`: Unified entry point with `get_vector_store_type()` and `get_llm_provider()` helpers
- `examples/marketing_team/application/Dockerfile`: Builds from `marketing_team/` context, includes both ChromaDB and psycopg2

**Alternative Rejected**: Separate local and production applications. Rejected because it creates code drift risk and doubles the testing surface.

---

### Decision 31: PostgreSQL Managed Identity Authentication

**Challenge**: Eliminate credential management overhead and security risks associated with database passwords while maintaining Terraform code simplicity.

**Discovery Process**:
Initial approach used password authentication stored in Key Vault. This required:
- Password rotation strategy
- Secret retrieval in application code
- Key Vault access from Container App

Managed Identity eliminates all of this complexity.

**Solution**: **Azure AD Authentication**.
- `uai-app` managed identity created in Terraform
- PostgreSQL AAD admin configured for the identity
- Application uses `DefaultAzureCredential` to obtain database tokens
- Terraform provider uses module outputs for host configuration

**Rationale**:
- **Security**: No passwords to rotate, leak, or manage.
- **Simplicity**: `DefaultAzureCredential` handles all token acquisition automatically.

**Impact**:
- `modules/postgresql/main.tf`: Creates AAD admin pointing to managed identity
- Application code: Uses `DefaultAzureCredential()` for database connections
- No password secrets in Key Vault required for database access

**Alternative Rejected**: Password authentication with Key Vault storage. Rejected due to credential rotation complexity and unnecessary security surface.

---

## Architecture Overview

### Infrastructure Architecture

**Two-Project Terraform Structure**:
```
examples/marketing_team/
├── infrastructure/terraform/          # Core infrastructure (14 modules)
│   ├── main.tf                        # Orchestrates all module calls
│   ├── variables.tf                   # Input variable definitions
│   ├── outputs.tf                     # Exports for application project
│   ├── providers.tf                   # Azure, PostgreSQL provider configs
│   ├── backend.tf                     # Azure Storage backend for state
│   ├── modules/
│   │   ├── resource-group/            # Resource group with tags
│   │   ├── network/                   # VNet, subnets, NSGs
│   │   ├── vnet-peering/              # Cross-VNet connectivity
│   │   ├── private-endpoint/          # Private endpoints for secure access
│   │   ├── user-assigned-identity/    # Managed identities for RBAC
│   │   ├── key-vault/                 # Secrets management
│   │   ├── storage-account/           # Blob storage, file shares
│   │   ├── postgresql/                # Flexible Server, pgvector, AAD auth
│   │   ├── ai-foundry/                # AI Foundry workspace, model deployments
│   │   ├── ai-search/                 # Azure AI Search (optional)
│   │   ├── openai-service/            # Azure OpenAI (alternative to AI Foundry)
│   │   ├── app-insights/              # Application Insights, Log Analytics
│   │   ├── container-apps-environment/# Container Apps Environment (no app)
│   │   └── container-registry/        # ACR with admin disabled
│   └── environments/
│       ├── test/terraform-test.tfvars
│       └── prod/terraform-prod.tfvars
│
└── application/                       # Container App deployment
    ├── main.tf                        # Container App module call
    ├── variables.tf                   # Input variable definitions
    ├── data.tf                        # terraform_remote_state for infra outputs
    ├── backend.tf                     # Azure Storage backend (separate state)
    ├── Dockerfile                     # Container image definition
    ├── .dockerignore                  # Build exclusions
    ├── app.py                         # Unified application entry point
    ├── requirements.txt               # Python dependencies
    ├── modules/
    │   └── container-app/             # Container App with managed identity
    └── environments/
        ├── test/terraform.tfvars
        └── prod/terraform.tfvars
```

### CI/CD Architecture (GitHub Actions)

**Two Workflows**:

| Workflow | File | Trigger | Purpose |
|----------|------|---------|---------|
| **Infrastructure** | `deploy-infra.yml` | Push to main, manual | Deploy/destroy core Azure resources |
| **Application** | `deploy-app.yml` | Push to main, manual | Build image, deploy Container App |

**Infrastructure Workflow** (`deploy-infra.yml`):
```
Push to main OR Manual Trigger
    │
    ├── Environment: test / prod
    ├── Action: deploy / destroy
    │
    ▼
┌─────────────────────┐
│   Terraform Job     │
│ ─────────────────── │
│ • Checkout repo     │
│ • Azure Login       │
│ • Terraform init    │
│ • Terraform plan    │
│ • Terraform apply   │
│   (or destroy)      │
└─────────────────────┘
```

**Application Workflow** (`deploy-app.yml`):
```
Push to main OR Manual Trigger
    │
    ▼
┌─────────────────┐
│   Build Job     │
│ ─────────────── │
│ • Checkout repo │
│ • Azure Login   │
│ • Docker build  │
│ • Push to ACR   │
│ • Output: tag   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Deploy Job    │
│ ─────────────── │
│ • Terraform init│
│ • Terraform plan│
│ • Terraform apply│
│ • Output: URL   │
└─────────────────┘
```

### Docker Build Architecture

**Dockerfile Design**:
- Base: `python:3.11-slim`
- Build context: `examples/marketing_team/` (not `application/`)
- Copies: `src/`, `configs/`, `assets/`, `application/app.py`
- Excludes: `notebooks/`, `data/`, `reports/`, `crewai/`, `langgraph/` (via `.dockerignore`)
- Security: Non-root `appuser`, no root privileges at runtime

---

## What Worked

### 1. Two-Project Terraform Architecture

**Approach**: Separating infrastructure and application into independent Terraform projects with `terraform_remote_state` data source.

**Outcome**: Complete isolation of AI Foundry state transitions from Container App deployments. Infrastructure can be deployed once and remain stable while application deploys happen on every code push.

### 2. Environment-Driven Application Configuration

**Approach**: Using environment variables (`VECTOR_STORE_TYPE`, `AZURE_OPENAI_ENDPOINT`) to select backends at runtime rather than compile-time conditionals.

**Outcome**: Single codebase, single Docker image, single deployment artifact. Local development with ChromaDB is seamless; production switches to PostgreSQL without code changes.

---

## What Didn't Work

### 1. Single Terraform Project for All Resources

**Problem**: AI Foundry's "Accepted" provisioning state blocked Container App deployment with 409 Conflict errors.

**Impact**: Deployment failures, manual retries, unpredictable CI/CD behavior.

**Correction**: Split into two projects. Infrastructure project exports outputs; application project consumes them via remote state.

### 2. ACR Tasks for Docker Builds

**Problem**: ACR Tasks require GitHub PAT stored in Azure to clone private repositories.

**Impact**: Security concern—credentials stored outside GitHub, potential for leakage.

**Correction**: Build Docker images in GitHub Actions runners where code access is native, push only the built image to ACR.

---

## Lessons Learned

### 1. Environment Detection > Conditional Code

**Discovery**: Rather than `if production: ... else: ...` code paths, using environment variable detection keeps the codebase clean and testable.

**Implication**: `get_vector_store_type()` and `get_llm_provider()` helper functions encapsulate environment detection. The rest of the application code is environment-agnostic.

---

## Progress Against 12-Week Plan

### Month 2: Production Build (Weeks 5-8)

**Week 5**: ✅ Framework Evaluation (CrewAI rejected, Microsoft Agent Framework selected)
**Week 6**: ✅ Microsoft Agent Framework Build & UI (v1.0-reference completed)
**Week 7**: ✅ **Azure Infrastructure & CI/CD** (Completed)
- Deployed full Azure infrastructure via Terraform
- Implemented two-project architecture for Container App isolation
- Automated CI/CD pipeline via GitHub Actions
- Unified application codebase for local and Azure
- PostgreSQL managed identity authentication

**Week 8+**: 📅 **Production Hardening**
- End-to-end testing in Azure environment
- HITL workflow implementation (Azure Logic Apps)
- Observability dashboard setup (Application Insights)
- Cost monitoring and alerts

---

## Cost Summary

### Week 7 Costs

**Development & Testing**:
- **Terraform Iterations**: ~20 plan/apply cycles during architecture split
- **Docker Build Testing**: ~15 builds to validate Dockerfile and .dockerignore
- **GitHub Actions Runs**: ~10 workflow executions for CI/CD validation

**Azure Infrastructure** (Test Environment):
- **Container Apps Environment**: Scale-to-zero (minimal cost when idle)
- **PostgreSQL Flexible Server**: Burstable B1ms (~$12/month)
- **AI Foundry**: Pay-per-use (no base cost)
- **ACR**: Basic tier (~$5/month)

**Estimated Week 7 Total**: ~€2.50 (development) + ~€15.00 (Azure resources prorated)

**Cumulative Costs**:
- Week 1: €2.15
- Week 2: €8.60
- Week 3: €5.24
- Week 4: €2.41
- Week 5: ~€0.00
- Week 6: ~€3.50
- Week 7: ~€17.50
- **Total**: ~€39.40

**Budget Status**: Within the €60/month budget. Azure costs will increase as production usage begins, but scale-to-zero Container Apps and burstable PostgreSQL keep baseline costs low.

---

## Future Roadmap (Week 8+)

Week 8 focuses on **production hardening and operational readiness**:

1. **End-to-End Testing**: Validate full content generation workflow in Azure environment
2. **HITL Integration**: Azure Logic Apps for approval workflows
3. **Observability**: Application Insights dashboards, custom metrics for quality/cost/latency
4. **Cost Alerts**: Azure Budget alerts for resource consumption

---

*Infrastructure foundation established. Production deployment ready for application testing.*
