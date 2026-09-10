---
id: SPEC-0008
title: Notificações por e-mail
status: Draft
version: 0.2
owner: Isaac Kleimann Graper
satisfies: [RF09]
depends_on: [SPEC-0004, SPEC-0005]
milestone: M4
---

# SPEC-0008 — Notificações por e-mail

## 1. Behaviour

**AC-0008-01** — Every NE transition sends an e-mail to the NE's responsável
naming the ATA, the insumo, the previous and new stage, and the actor.

**AC-0008-02** — Dispatch is asynchronous and never blocks the transaction. An
SMTP failure does not roll back a state change; the transition is the record of
truth, the e-mail is a courtesy.

**AC-0008-03** — Failed sends are retried with exponential backoff up to 5
attempts, then recorded as failed and surfaced in an admin view. Silently
dropped notifications train users to distrust the system.

**AC-0008-04** — A user may opt out of advisory notifications but not of those
addressed to them as responsável for an action.

**AC-0008-05** — E-mails contain no personal data beyond the recipient's own
name, and no CPF or SIAPE (RNF07).

**AC-0008-06** — In non-production environments, e-mail is written to a local
maildir rather than sent. A test asserts no external SMTP connection is opened
when `APP_ENV != production`.

## 2. Note

The RFC lists Resend as an option. For an on-premise state-government
deployment, an external e-mail SaaS may be prohibited by the entity's data
policy and may not reach internal `.gov.br` recipients. The interface is
abstracted behind a `NotificationSender` port so the transport is a
configuration choice; institutional SMTP is the default. See OQ-13.

## Revision 2026-09-02 — stakeholder constraint from the 17/08 meeting

RF09 asks for an e-mail on every supply status change. The entity's own IT
department has told the stakeholders this will not survive contact: *"e-mail
demais, eles vão bloquear por spam. A gente tem que ser mais cauteloso —
escolher as coisas que realmente são extremamente [importantes]"*.

A per-status-change notification is therefore not merely noisy, it is a design
that gets the sender blocked, after which the system delivers nothing at all.

What the stakeholders asked for instead:

- **Aggregated digests**, grouped by comprador and by grupo de materiais, rather
  than one message per event. Each comprador is responsible for a subset of the
  catalogue and wants that subset's changes together.
- **A configurable criticality threshold**, so the entity — not the code —
  decides what is worth an e-mail.
- The meeting also described the digest's most wanted content: what entered and
  what left the critical list this week, with the net figure. *"10 entraram e 10
  saíram, estamos no zero a zero."*

This does not change RF09's intent (notify the responsible party) but it does
change its mechanism, so it needs an explicit note in `functional.md`'s notes
column rather than a silent reinterpretation here. The ACs are not rewritten in
this revision; the constraint is recorded first so the design is not built twice.

## 3. Changelog

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-08-17 | Initial draft from RFC §2.3 RF09, §5.1 |
| 0.2 | 2026-09-02 | Recorded the IT spam-block constraint from the 17/08 meeting: RF09 needs aggregated, threshold-driven digests per comprador, not per-event e-mail |
