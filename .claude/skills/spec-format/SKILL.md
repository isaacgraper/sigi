---
name: spec-format
description: How to write and revise specifications in this repository — structure, acceptance-criteria style, IDs and traceability. Use when creating, editing or reviewing anything under docs/specs/, or when asked whether behaviour is specified.
---

# Spec Format

## Files and IDs

- One spec per capability: `docs/specs/SPEC-XXXX-<slug-pt-br>.md`.
- Numbers are permanent. A retired spec becomes `Superseded`; its number is never reused.
- Acceptance criteria are `AC-XXXX-NN`, numbered within their spec, never renumbered.
  Tests reference these IDs, so renumbering silently breaks traceability.

## Status

`Draft → Review → Approved → Implemented → Superseded`

Only `Approved` specs may be implemented. Changing an `Approved` spec requires a
version bump and a changelog line.

## What makes an acceptance criterion valid

It must be **observable** — assertable from an API response, a database row, an
e-mail, or the DOM — **atomic**, and written Given/When/Then.

Good:
```gherkin
Given an NE in status "demanda"
When  a transition directly to "ne_emitida" is requested
Then  the response is 409 with error code "TRANSICAO_INVALIDA"
And   the NE status is unchanged
```

Not valid, and why:
- "The system must be performant." — not observable; give a number and a method.
- "Validate the NE correctly." — "correctly" is doing all the work.
- "Create and advance an NE and send an e-mail." — three criteria wearing one ID.
- "The service calls `validate_saldo()`." — asserts implementation, not behaviour.

## Coverage rule

For each happy path, the spec must also state:
- the validation failure (which field, which code, which pt-BR message);
- the permission denial (per profile);
- the domain conflict (invalid transition, insufficient saldo, ineligible ATA);
- the audit row produced.

Specs that describe only success produce systems that work only on success, and
in an auditability product the failure paths *are* the product.

## Sections a spec must not contain

File names, class names, SQL, library choices. Those live in the
`## Implementation plan` section, added by `/plan` after approval, so that the
behavioural contract stays readable by a non-developer stakeholder.

## On finishing

Update `docs/requirements/traceability.md` and add any new contradictions to
`docs/open-questions.md`. A spec that resolves an ambiguity without recording
that it did so has made a decision nobody agreed to.
