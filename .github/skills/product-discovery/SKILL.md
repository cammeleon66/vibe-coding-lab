---
name: product-discovery
description: Use when the user introduces a new product, business, application, or major feature idea, asks whether something is worth building, or asks to explore and validate an idea. Investigate the domain and existing solutions before extensive questioning; challenge assumptions with evidence; ask one highest-value question at a time; produce and red-team a product brief; stop for the user's approval before architecture.
---

# Product discovery

Determine whether an idea deserves to exist and, if so, discover its strongest credible version. Optimize for reduced uncertainty and product improvement, not agreement or momentum.

## Operating rules

- Treat the user's intent as the source of truth, but do not treat the user's first solution as validated.
- Research questions that reliable sources, repository evidence, experiments, or available tools can answer before asking the user.
- Ask only one question at a time. Choose the question whose answer is most likely to change the product direction, target user, desirability assessment, risk profile, or next investigation.
- Make progress between questions: summarize what is known, what changed, what remains uncertain, and why the next question has the highest value.
- Separate facts, evidence-backed inferences, assumptions, hypotheses, user decisions, recommendations, and unknowns.
- Challenge ideas directly and respectfully. Do not protect enthusiasm at the expense of truth.
- Tell the user clearly when the idea appears weak, why, how confident the assessment is, and what evidence could change it.
- Never silently change the idea. If proposing a different product, explain the gap from the original intent and ask for approval before treating the alternative as the new direction.
- Do not turn discovery into a giant questionnaire, speculative architecture exercise, or premature implementation plan.

## Discovery loop

Run the following loop, adapting the order to the uncertainty already present:

1. **Capture intent.** Restate the idea, intended users, desired outcome, proposed value, constraints, non-goals, and what the user currently believes. Mark missing information as unknown rather than filling it in.
2. **Research the landscape.** Investigate the relevant domain, user context, existing products, direct competitors, adjacent substitutes, failed or abandoned approaches, market signals, and authoritative constraints. Prefer primary sources and record sources, dates, findings, and confidence.
3. **Model the problem.** Identify candidate users, their actual jobs or problems, current workarounds, urgency, frequency, consequences, willingness and ability to adopt, and who decides or pays. Distinguish a stated preference from demonstrated behavior.
4. **Map risks and constraints.** Identify business, adoption, technical, regulatory, security, privacy, operational, dependency, distribution, and Azure cost risks. Highlight risks that could invalidate the idea or require approval.
5. **Expose assumptions.** Maintain an explicit assumption register. For each important assumption, state its impact, confidence, evidence, and the cheapest useful test or research action.
6. **Challenge and compare.** Test the problem, user, value proposition, differentiation, feasibility, timing, distribution, economics, and risks. Compare the proposed solution with doing nothing, existing solutions, simpler alternatives, and stronger product variants.
7. **Ask one high-value question.** Ask only when the answer cannot be responsibly obtained through research and would materially reduce uncertainty. After the answer, research again if it introduces a new important uncertainty.
8. **Converge.** Decide whether the evidence currently supports: stop, continue discovery, test a narrower hypothesis, pursue a stronger alternative, or draft a product brief. Do not manufacture certainty.

## Research standard

Research is sufficient for the next decision when:

- the leading user/problem and strongest alternatives are identified;
- important claims have appropriate sources or are explicitly marked uncertain;
- the assumptions most capable of invalidating the idea are visible;
- material constraints, risks, and cost drivers are understood enough to choose the next test or decision;
- additional research is unlikely to change the immediate next step.

When sources conflict, show the conflict, assess source quality and applicability, and state what remains unresolved. Stop researching when the stopping condition is met; do not research for volume.

## Weak-idea and alternative handling

When an idea appears weak, report:

1. the specific weakness;
2. the evidence;
3. the assumptions behind the assessment;
4. the likely consequence;
5. the confidence and what could change the conclusion;
6. stronger alternatives, narrower wedges, or validation tests.

Keep alternatives separate from the user's original idea. An alternative becomes the working direction only after the user chooses it.

## Product brief

Draft a product brief only when discovery has reduced the most important uncertainty enough to make the product definition useful. Mark it **Proposed** until the user approves it.

The brief must include:

- **Status and decision:** Proposed, Approved, Rejected, or Superseded; current recommendation and rationale.
- **Problem:** target user, context, job or pain, current alternatives, urgency, and consequences.
- **Outcome:** the measurable or observable change the product should create.
- **Product concept:** the smallest credible solution and why it is stronger than alternatives.
- **Users and stakeholders:** primary user, secondary users, buyer, approver, operator, and affected parties.
- **Value proposition and differentiation:** why users would switch, adopt, or pay.
- **Scope:** must-have capabilities, explicit non-goals, and initial boundaries.
- **Success measures:** behavioral, product, business, and quality indicators.
- **Evidence:** research findings and sources supporting important claims.
- **Assumption register:** assumption, impact, confidence, evidence, and validation plan.
- **Risks and constraints:** business, adoption, technical, regulatory, security, privacy, operational, Azure, and cost concerns.
- **Alternatives considered:** including doing nothing and simpler approaches.
- **Open questions:** only questions that still affect a material decision.
- **Approval record:** exact approved scope, rejected alternatives, approver, date, assumptions, and re-approval conditions.

## Product red-team

Before requesting approval, independently red-team the proposed brief. Look for:

- a real problem being confused with an interesting idea;
- weak urgency, frequency, willingness, or adoption path;
- an existing product or workaround that is good enough;
- differentiation that is easy to copy or not valuable;
- an untested user, buyer, or distribution assumption;
- economics that do not support the effort or operating cost;
- hidden technical, regulatory, security, privacy, reliability, or operational risk;
- scope that is too broad to validate;
- success measures that reward activity instead of user value;
- contradictions between the user's intent and the proposed brief.

For each finding, state severity, evidence, confidence, affected brief section, recommendation, and whether the user must decide. Present objections and responses explicitly; do not bury accepted risks.

## Handoff gate

Stop before architecture begins unless the user explicitly approves the product direction. The approval must identify the approved brief or version, scope, non-goals, success measures, accepted risks, rejected alternatives, assumptions, approver, date, and conditions requiring re-approval.

If the user has not approved the brief, remain in discovery, research, challenge, or clarification. Do not design architecture, select Azure resources, estimate implementation tasks, or write application code merely to create momentum.

## Completion criteria

Product discovery is complete only when one of these outcomes is explicit and documented:

- **Stop:** evidence does not justify building the idea.
- **Continue discovery:** a material uncertainty remains and has a named next research action or question.
- **Validate a hypothesis:** a narrower test is defined with success and failure criteria.
- **Pursue an alternative:** the user selected a stronger product direction.
- **Approve product direction:** the product brief and red-team findings are resolved or accepted, the approval record is complete, and the work may hand off to architecture.
