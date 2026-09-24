# DEC-010: Hybrid federated referral sharing

**Status:** Approved  
**Date:** 2026-09-24

## Decision

The demonstration uses a hybrid sharing model:

- hospital systems remain the source of truth;
- the platform calls hospital-owned APIs to discover permitted evidence;
- the referral package carries approved structured context and provenance;
- large source files remain at the originating hospital and are retrieved only when authorized;
- every cross-hospital package or update requires an explicit Milan sharing approval;
- Utrecht acknowledges the exact case version it reviews.

## Why

A fully centralized copy would contradict the product promise. A reference-only model would make the receiving workflow fragile and difficult to demonstrate. The hybrid model supports a useful referral package while keeping source ownership, authorization, and retrieval boundaries visible.

## Consequences

- The user interface must distinguish data that stays in Milan from information included in the referral package.
- API activity, sharing approvals, transfers, and acknowledgements must appear in the activity timeline.
- Late evidence creates a new immutable case version rather than changing the package already reviewed by Utrecht.
- The demonstration must not claim that no data moves between hospitals.
