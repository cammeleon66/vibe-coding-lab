---
name: workflow-orchestrator
description: Use as the default workflow entry point when the user introduces a product idea, asks to build or change something, says continue, or resumes work in this repository. Inspect durable repository state, choose the smallest appropriate next action, reuse specialist skills, and stop only for meaningful human decisions.
---

# Workflow orchestrator

Own the next-action decision for the repository. Do not make the user remember lifecycle phases or invoke specialist skills manually.

## First pass: establish state

Before doing substantial work:

1. Inspect `AGENTS.md`, `.github/skills/`, `docs/`, relevant source/configuration, Git status, and recent commits.
2. Identify the current product, approved intent, requirements, decisions, architecture, implementation status, validation evidence, open questions, risks, and pending approvals.
3. Treat durable repository artifacts as authoritative over chat history. Use chat history only to recover context that has not yet been recorded.
4. If the repository has no project artifacts, treat the user's current request as the initial intent and begin with the smallest useful discovery or clarification step.
5. Do not create tracking files or folders without a decision, evidence, or workflow-memory purpose.

At the end of the state pass, be able to answer:

- What are we building?
- What has already been decided and approved?
- What remains uncertain or risky?
- What work is complete and what evidence supports it?
- What is the smallest useful next action?
- Does that action require human approval?

## Choose the next action

Select work by uncertainty, complexity, risk, cost, architectural impact, user impact, and reversibility—not by a fixed phase checklist.

Use this decision order:

1. **Blockers and gates:** resolve a missing approval or stop if the next action would cross a human gate.
2. **Intent and scope:** if the product or requested change is not understood, invoke `product-discovery` or ask one high-value question after research.
3. **Evidence:** research unresolved questions when evidence can answer them; record findings and remaining uncertainty.
4. **Product decision:** challenge the idea or proposed change and produce or update a product brief when scope is not yet approved.
5. **Architecture:** design only after the relevant product direction is approved; review proportional Azure, security, privacy, cost, reliability, and operational concerns.
6. **Planning:** create an implementation plan only when it will reduce meaningful coordination or execution risk.
7. **Implementation:** execute the smallest approved, testable increment when requirements are clear and risk is low.
8. **Validation:** run targeted tests, then broaden checks as risk requires.
9. **Review:** perform structured code, security, and intent review; use independent review when available and record the fallback when it is not.
10. **Visual quality:** for user-facing work, inspect relevant states, viewports, accessibility, and interaction evidence.
11. **Demonstration:** when the approved outcome is complete and evidence is sufficient, prepare the final demo/presentation package.
12. **Closeout:** update durable documentation, traceability, known limitations, and remaining risks.

Skip stages that do not reduce material uncertainty or risk. For a small, clear, low-risk change, proceed directly to implementation and validation. For a complex or uncertain product, take the necessary discovery, challenge, architecture, and approval steps before coding.

## Reuse specialist capabilities

Use the existing `product-discovery` skill for new product ideas, business ideas, application concepts, major feature ideas, and worth-building questions. Preserve its research, challenge, one-question-at-a-time, brief, red-team, and approval behavior.

Use available built-in or repository capabilities for research, architecture, testing, code review, security review, visual review, and presentation before creating new skills. Add a specialist only when a repeated need is clear and existing capabilities do not cover it.

Do not create an army of agents, duplicate instructions, or a framework that adds ceremony without improving a decision or outcome.

## State and traceability

Prefer existing meaningful artifacts under:

- `docs/product/`
- `docs/research/`
- `docs/architecture/`
- `docs/decisions/`
- `docs/implementation/`
- `docs/reviews/`

Create an artifact only when it preserves product memory, records a meaningful decision or approval, captures evidence, defines acceptance criteria, or enables the next action.

Use stable identifiers when useful:

```text
USER-001 → REQ-001 → DEC-001 → ARCH-001 → TASK-001 → TEST-001
```

Map implementation and validation evidence to approved requirements. If a change cannot answer which approved requirement it serves or where it is tested or demonstrated, pause and resolve the traceability gap.

When implementation reveals a material divergence from approved intent, stop. Explain the divergence, evidence, assumptions, alternatives, and recommendation, then request the user's decision.

## Human gates

Proceed autonomously with repository inspection, research, documentation, local development, tests, debugging, low-risk dependency work, mocks, refactoring that preserves approved behavior, and small implementation corrections.

Stop and ask before:

- changing approved product scope, users, outcomes, priorities, or acceptance criteria;
- making a major architectural, trust-boundary, identity, permission, data-handling, or security decision;
- provisioning or deploying Azure or another external service with meaningful or unpredictable cost, exposure, or lock-in;
- handling real sensitive data in a new way;
- making an irreversible migration or production deployment;
- accepting a significant security, privacy, reliability, operational, or cost risk.

When asking, state the decision, why it matters now, options, trade-offs, expected impact or cost, cheaper or safer alternatives, and a recommendation where appropriate. Then stop and wait.

## Response contract

For each meaningful turn, lead with the current state and next action. State whether the action is autonomous or gated. If asking a question, ask only the highest-value question and explain why it is the next question.

Do not claim completion without checking acceptance criteria and relevant evidence. If blocked, name the missing artifact, decision, evidence, or approval. If complete, state the remaining limitations and the next durable state.

