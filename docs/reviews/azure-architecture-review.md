# Azure architecture review

**Reviewed artifact:** `docs/architecture/architecture-proposal.md` version 0.1
**Status:** Conditions accepted with architecture approval
**Date:** 2026-09-23

## Executive assessment

The proposal is proportionate for a synthetic stakeholder demonstration. It preserves institutional heterogeneity, avoids production-healthcare infrastructure that does not serve the demo, keeps Fabric aligned to analytics and research, and limits the operational design to one application plus storage and events.

Architecture approval should require explicit cost limits, bounded telemetry, synthetic authorization labeling, and a clinical-fidelity review before the final presentation.

## Azure Well-Architected review

### Reliability

**Strengths**

- Deterministic rehearsal is independent of live AI.
- Source records and collaboration state are durable.
- Version checks and idempotency protect state transitions.
- The small single-replica design matches the one-presenter requirement.

**Risks**

- Scale-to-zero cold start may affect presentation timing.
- Event delivery and source refresh could fail immediately before a demo.
- A shared Fabric capacity may be throttled or unavailable.
- The narrative MDO handoff is an external dependency.

**Required controls**

- Warm the application before presentation.
- Provide a preflight command and presenter health screen.
- Preserve a manual, clearly labeled replay of the evidence-arrival event.
- Cache the research epilogue for rehearsal.
- Verify the MDO link and matching case before each presentation.

### Security

**Strengths**

- Synthetic data removes real-patient exposure.
- Managed identity avoids storage credentials in code.
- Clinical and research contexts are separated.
- Original evidence and state-changing actions are auditable.

**Risks**

- Synthetic role switching could be mistaken for real authorization.
- Named institutions could imply real integration or governance.
- Blob access and event endpoints could be over-permissive.
- Logs could accidentally include synthetic clinical content or prompts.

**Required controls**

- Label all institutional data, clinicians, permissions, and availability as simulated.
- Authenticate the presenter with Entra.
- Grant managed identities least-privilege container access.
- Keep storage writes private and disable anonymous access.
- Redact workflow content from logs and exports not intended for the presentation.
- Conduct a security review before deployment.

### Cost optimization

**Strengths**

- Consumption compute and scale-to-zero suit intermittent use.
- Blob Storage and Event Grid are low-cost for the expected volume.
- Existing Fabric capacity avoids a new capacity purchase.
- Azure Health Data Services is omitted.

**Risks**

- Log Analytics ingestion can exceed application cost.
- Fabric work may consume shared capacity and affect other workloads.
- Repeated live model runs can create variable cost.
- Leaving minimum replicas or Fabric refreshes running creates avoidable spend.

**Required controls**

- Set a monitoring daily cap and short retention.
- Default Container Apps minimum replicas to zero outside rehearsals.
- Use a fixed Azure OpenAI token budget if live mode is approved.
- Keep Fabric refresh manual or event-bounded.
- Create and approve a pricing-calculator estimate before provisioning.
- Define teardown or pause instructions.

### Operational excellence

**Strengths**

- One deployable reduces operational surfaces.
- Deep modules keep source variation and case preparation local.
- A deterministic mode supports rehearsal and incident isolation.
- Infrastructure can later be represented as code.

**Risks**

- The demo could depend on undocumented presenter actions.
- Scripted and live behavior might become indistinguishable.
- Shared Fabric and MDO dependencies require coordinated readiness.

**Required controls**

- Create an explicit presenter walkthrough and preflight checklist.
- Display the active runtime mode at all times.
- Record verification commands and observed results.
- Use coherent deployment configuration and environment-specific settings.
- Keep application errors visible instead of substituting scripted success.

### Performance efficiency

**Strengths**

- Dataset size and concurrency are intentionally small.
- One application can prepare the case without distributed coordination.
- Prepared snapshots avoid reparsing every source on each UI request.

**Risks**

- DICOM download and rendering may dominate latency.
- Cold starts could interrupt the narrative.
- Large model contexts could make live synthesis slow.

**Required controls**

- Use a small, presentation-specific DICOM dataset.
- Precompute safe derived images and metadata while retaining source links.
- Refresh case preparation on evidence arrival, not on every page load.
- Bound AI evidence packages and timeouts.
- Measure the complete presenter path at realistic network conditions.

## Cloud Adoption Framework considerations

### Strategy and plan

- The business outcome is a persuasive demonstration, not a production clinical platform.
- Architecture choices must remain reversible and avoid implying readiness for clinical adoption.

### Ready / landing zone

- Use separate resource groups for simulated institutions and shared platform ownership.
- Apply consistent tags for owner, environment, demo purpose, expiry, and cost centre.
- Select one EU region only after service availability and event location are known.

### Govern

- Apply budget alerts and resource locks proportionately.
- Record approved services and prohibit unreviewed additions.
- Keep synthetic data classification explicit.
- Set an expiry or review date for all demo resources.

### Secure

- Use Entra, managed identity, least privilege, private storage access, and controlled secrets.
- Do not present synthetic role switching as production identity federation.

### Manage

- Use simple health checks, bounded logs, preflight verification, and teardown documentation.
- Full enterprise operations, multi-region recovery, and clinical support processes are intentionally deferred.

## Deferred concerns

These are intentionally deferred because the approved product is a synthetic demonstration:

- real patient consent and lawful-basis implementation;
- healthcare-professional credential federation;
- production multi-tenancy;
- real hospital connectivity;
- full DICOMweb and FHIR conformance;
- multi-region disaster recovery;
- clinical safety case and medical-device assessment;
- production data retention and records management;
- full EHDS or MyHealth@EU conformance.

Deferral must remain visible in the product and presentation.

## Findings requiring human approval

| ID | Severity | Finding | Recommendation |
| --- | --- | --- | --- |
| ARCH-RT-001 | High | Fabric is valuable for the research epilogue but creates unnecessary coupling as the operational backend. | Approve Fabric as a separate research workspace only. |
| ARCH-RT-002 | High | Azure Health Data Services is not justified by the version-one requirements. | Exclude it until real FHIR/DICOM exchange becomes a requirement. |
| ARCH-RT-003 | High | Presenter identity and synthetic clinician authorization must not be conflated. | Use real Entra authentication only for app access; label in-product cross-border roles as simulated. |
| ARCH-RT-004 | Medium | Monitoring and live AI are the least predictable cost drivers. | Require daily log caps and a separate token budget before deployment. |
| ARCH-RT-005 | Medium | A narrative MDO handoff can undermine credibility if state continuity is weak. | Use a versioned manifest, matching case ID, unresolved issues, and consistent visual transition. |

## Recommendation

Approve architecture proposal version 0.1 subject to:

1. a region-specific cost estimate and explicit provisioning approval;
2. a bounded monitoring configuration;
3. separate approval for any Azure OpenAI live mode;
4. mandatory clinical-fidelity review before presentation;
5. a security review before cloud deployment;
6. preservation of the approved product journey and synthetic-data boundaries.

Architecture version 0.1 was approved by the user on 2026-09-23 for implementation planning only. Provisioning and deployment remain gated.
