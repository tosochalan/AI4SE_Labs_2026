---
name: architecture-decision-record
description: "Use when analyzing software requirements, proposing or comparing system architectures, choosing architectural approaches, or creating, reviewing, and revising Architecture Decision Records (ADRs)."
argument-hint: "Requirements, decision to evaluate, or ADR path"
---

# Architecture Proposals and ADRs

Guide a user from requirements to a reasoned architecture decision and a usable ADR. Ground the work in the repository and supplied requirements; do not invent constraints or present assumptions as facts.

## Workflow

### 1. Understand the system and decision

1. Read the supplied requirements, relevant repository documentation, and existing architecture/ADR notes before proposing a design. Search for established conventions and existing decisions.
2. Summarize the system purpose, actors, major workflows, domain boundaries, integrations, and data that must be protected or retained.
3. Separate:
   - Explicit functional requirements.
   - Quality attributes and constraints actually stated.
   - Assumptions or inferred priorities.
   - Open questions that could materially change the design.
4. Identify decision scope. Do not silently expand a focused decision into a complete system redesign.
5. Ask a concise clarifying question when a missing choice blocks a sound recommendation or has materially different reasonable outcomes. Otherwise proceed using clearly labeled assumptions and record unresolved questions.

### 2. Establish decision drivers

Derive a consistent set of decision drivers from the evidence. Common drivers include correctness and consistency, security and privacy, reliability, performance and scale, delivery speed, team skills/ownership, operational burden, cost, evolvability, and interoperability. Do not treat every driver as equally important; explain which requirements are decisive and why.

### 3. Propose viable architecture options

1. Present at least **two materially distinct, viable options**. Prefer three when useful and when the user requests it. Options should represent different architectural approaches, not superficial technology substitutions.
2. Make each option concrete enough to understand: deployment shape, major components/modules, data ownership/storage, communication paths, and how the main user workflows work.
3. Evaluate all options against the same decision drivers. For each, include:
   - Benefits and trade-offs.
   - Operational and team feasibility, with conditions that affect feasibility.
   - Low-level implementation pain points and failure modes.
   - Important consistency, security, scaling, and migration concerns that apply to that option.
4. Tie claims to requirements and label assumptions. Avoid declaring a solution “best practice” without a system-specific reason.
5. Use a comparison table when it improves scanability, but do not let a table replace meaningful option analysis.

### 4. Facilitate and record the decision

1. Recommend an option only after comparing the alternatives against the drivers. Explain the decisive trade-offs and what evidence would change the recommendation.
2. If the user must choose among materially different outcomes, ask them directly rather than making an irreversible product decision on their behalf. If they have already chosen, document their choice and assess its implications.
3. Keep decision status accurate:
   - **Proposed** when presenting a recommendation that the user/team has not approved.
   - **Accepted** only when the user/team has confirmed the decision.
   - Use **Rejected**, **Superseded**, or repository-standard status when appropriate, with context.
4. Preserve unresolved questions, assumptions, and revisit triggers. Do not turn open questions into requirements.

### 5. Draft or revise the ADR

Use the companion [ADR template](./assets/ADR-TEMPLATE.md) unless the repository has an established format. Include the relevant standard sections:

- Title/decision identifier, status, date, and decision owners if known.
- Context and problem statement.
- Decision drivers and technical constraints.
- Options considered, including the selected option and alternatives.
- Decision outcome and rationale.
- Consequences: positive, negative, and low-level implementation trade-offs/controls.
- Architectural guardrails and a diagram when they clarify boundaries or flows.
- Assumptions, open questions, and conditions for revisiting the decision.

Adapt section names to fit the repository, but retain the substance. Ensure the ADR is self-contained and records the decision rather than only the discussion.

### 6. Verify and maintain artifacts

1. Check that the selected architecture addresses the key requirements and that the rationale, consequences, and diagram agree.
2. Verify technical claims and qualify guarantees with their preconditions. For example, database locking only prevents overselling when all relevant write paths follow the same transaction protocol and the selected database supports the specified lock semantics.
3. Avoid specifying an implementation technology, cloud vendor, database, or operational policy unless it is required, selected, or explicitly marked as an example/open decision.
4. If asked to keep discussion notes, append concise decisions, trade-offs, assumptions, and open questions; do not overwrite existing notes.
5. Follow the user's requested output path and repository conventions. Validate formatting/frontmatter and run focused checks (such as whitespace/diff checks) appropriate to the change.
6. In the response, summarize the recommendation/status and link the created or revised files.

## Quality bar

- Make trade-offs concrete and specific to the system.
- Distinguish logical modules from separately deployed services.
- Address transaction boundaries, retries, idempotency, ownership, authorization, and operational concerns where relevant.
- Do not claim a decision is final until confirmed.
- Keep diagrams consistent with the architecture description; show boundaries and important data/control flows without implying extra infrastructure.
- Prefer a simple architecture that satisfies demonstrated needs, while explaining a credible evolution path where useful.
