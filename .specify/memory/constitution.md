<!--
Sync Impact Report - Constitution Update
─────────────────────────────────────────────────────────────────
Version Change: INITIAL → 1.0.0
Change Type: MAJOR (Initial ratification)
Date: 2025-12-15

Principles Added:
  1. Specification-First Development
  2. Independent User Stories
  3. Template-Driven Consistency
  4. Test-Optional Flexibility
  5. AI Agent Collaboration
  6. Constitution Authority

Sections Added:
  - Development Workflow
  - Governance

Templates Status:
  ✅ plan-template.md - Aligned with Constitution Check principle
  ✅ spec-template.md - Aligned with Independent User Stories principle
  ✅ tasks-template.md - Aligned with user story organization principle
  ⚠  agent files - Generic guidance verified (no agent-specific names like CLAUDE)

Follow-up TODOs:
  - None (initial constitution complete)

Rationale:
  MAJOR version for initial constitution establishing core governance framework
  for specification-driven development with AI agent collaboration.
─────────────────────────────────────────────────────────────────
-->

# SpecKit Constitution

## Core Principles

### I. Specification-First Development

Every feature MUST begin with a complete specification before implementation begins. The specification workflow is:

1. User describes feature intent → `/speckit.specify` generates `spec.md`
2. Specification validated → `/speckit.plan` generates implementation plan
3. Plan approved → `/speckit.tasks` generates executable task list
4. Tasks executed → Implementation follows task order

**Rationale**: Pre-implementation clarity prevents scope creep, reduces rework, and ensures all stakeholders understand requirements before code is written. Specifications serve as living documentation and acceptance criteria.

### II. Independent User Stories

Every user story MUST be independently testable, implementable, and deployable. Each story:

- Delivers standalone value when implemented alone
- Can be tested without dependencies on other stories
- Has explicit priority (P1, P2, P3, etc.) reflecting business value
- Includes acceptance scenarios in Given/When/Then format

**Rationale**: Independent stories enable parallel development, incremental delivery, and true MVP identification. Story independence reduces integration risk and allows flexible prioritization.

### III. Template-Driven Consistency

All artifacts MUST conform to their canonical templates in `.specify/templates/`:

- `spec-template.md` for feature specifications
- `plan-template.md` for implementation plans  
- `tasks-template.md` for task breakdowns
- `checklist-template.md` for quality checklists

Templates define mandatory sections, structure, and metadata. Deviations require explicit justification in the artifact.

**Rationale**: Consistent structure enables automation, reduces cognitive load, ensures completeness, and allows reliable parsing by AI agents and tooling.

### IV. Test-Optional Flexibility

Tests are OPTIONAL unless explicitly requested in the specification. When tests are required:

- Tests MUST be written before implementation (test-first)
- Tests MUST fail before implementation begins (red-green-refactor)
- Test tasks clearly marked with `⚠️ OPTIONAL` indicators in templates
- Contract, integration, and unit test categories explicitly separated

**Rationale**: Not all features require the same testing rigor. Explicit test requirements prevent over-testing low-risk code and under-testing critical paths. Test-first discipline applies only when testing is in scope.

### V. AI Agent Collaboration

AI agents operate through defined commands with clear inputs, outputs, and templates:

- Each agent has a single, well-defined responsibility
- Agent prompts stored in `.github/prompts/speckit.*.prompt.md`
- Agent implementations in `.github/agents/speckit.*.agent.md`
- Agents MUST NOT reference specific AI model names (e.g., "Claude") in generic guidance
- Agent context updated via `.specify/scripts/powershell/update-agent-context.ps1`

**Rationale**: Clear agent boundaries prevent overlap, enable substitution, and ensure consistent behavior. Generic guidance allows portability across AI platforms.

### VI. Constitution Authority

This constitution is **NON-NEGOTIABLE** and supersedes all other practices. All artifacts and processes MUST comply:

- `plan.md` includes mandatory "Constitution Check" gate
- `/speckit.analyze` validates constitution compliance
- Violations require explicit justification in "Complexity Tracking" tables
- Constitutional amendments follow semantic versioning and require approval

**Rationale**: Constitution establishes project governance boundaries. Systematic enforcement prevents drift. Justified exceptions preserve flexibility while maintaining visibility.

## Development Workflow

### Phase Execution Order

1. **Specification** (`/speckit.specify`) → `spec.md` with prioritized user stories
2. **Planning** (`/speckit.plan`) → `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`
3. **Task Breakdown** (`/speckit.tasks`) → `tasks.md` organized by user story
4. **Quality Verification** (`/speckit.analyze`) → Consistency and coverage analysis
5. **Implementation** (`/speckit.implement`) → Code following tasks in priority order

### Artifact Dependencies

- `plan.md` requires `spec.md`
- `tasks.md` requires `plan.md` and `spec.md`
- `/speckit.analyze` requires all three artifacts
- Implementation requires passing constitution check

### Review Gates

- **Post-Specify**: User approves user stories and priorities
- **Post-Plan**: Constitution check passes and technical approach validated  
- **Post-Tasks**: Task coverage verified and dependencies resolved
- **Pre-Implementation**: All gates passed and artifacts consistent

## Governance

### Amendment Process

1. Proposed change documented with rationale
2. Impact analysis on existing templates and agents
3. Version bump determined (MAJOR/MINOR/PATCH):
   - **MAJOR**: Backward-incompatible principle removal/redefinition
   - **MINOR**: New principle or materially expanded section
   - **PATCH**: Clarifications, wording fixes, non-semantic refinements
4. Template updates propagated before constitution merge
5. Sync Impact Report generated and prepended to constitution

### Versioning Policy

Constitution follows semantic versioning (`MAJOR.MINOR.PATCH`). Version appears in footer with ratification and amendment dates (ISO 8601 format YYYY-MM-DD).

### Compliance Review

All code reviews, pull requests, and agent executions MUST verify:

- Specifications include independent, prioritized user stories
- Plans include constitution check gates
- Tasks organized by user story with clear dependencies
- Complexity violations explicitly justified
- Tests marked optional unless spec requires them

**Version**: 1.0.0 | **Ratified**: 2025-12-15 | **Last Amended**: 2025-12-15
