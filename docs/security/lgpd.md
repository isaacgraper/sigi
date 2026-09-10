# LGPD — Personal Data Handling

Source: RFC §6.4. This document is the register a DPO would ask for.

## Data inventory

| Category | Fields | Legal basis (Lei 13.709/2018) | Retention |
| --- | --- | --- | --- |
| Servidor identification | nome, e-mail institucional, perfil/cargo | Art. 7, II and V — legal obligation / contract execution | While active + 5 years in audit rows (pseudonymised) |
| Authentication | senha (hash), tokens, IP, user-agent | Art. 7, IX — legitimate interest, system security | Tokens until expiry; access logs 12 months |
| Audit and traceability | usuario_id, timestamp, ação, dados anteriores | Art. 7, II — legal obligation, public transparency | ≥ 5 years (RNF08) |
| Operational | ATA, NE, NF, insumo data | Art. 7, V — contract execution. **Not personal data.** | Indefinite |

## Health data in the source exports *(2026-09-02)*

This register was written from the RFC, which places `fórmulas e suplementos`
(150–200 administrative and judicial cases) **out of scope** and therefore
records no health data. The entity's export contract contradicts that
assumption: `ENTRADAS NFS (CSV)` carries **`pacienteNome`** alongside a
`judicial` flag and a `processo` number.

A named individual receiving a judicially mandated supply is health data about
an identified person — the most sensitive category this project could touch, and
one requiring a legal basis this register does not have.

Controls, in force now:

1. **`ENTRADAS NFS` is not ingested.** Independently decided on data-quality
   grounds (the entity has no use for it), and now also a privacy control.
2. If it is ever ingested, `pacienteNome` is dropped **at the importer**, before
   any persistence, and never written to a log, an error report or a validation
   message.
3. The workbooks themselves must not be committed to this repository. The
   analysis script reads them from a path outside the repo and emits only
   aggregates and column names.
4. Should the entity ever ask for the judicial flow to be in scope, this
   register needs a new row with an explicit legal basis under art. 11 (dados
   sensíveis) — not art. 7. That is a different conversation from the one the
   RFC had.

Tracked as OQ-24.

## Minimisation issues to resolve

The profile mockup (9.2.1) shows **CPF** and **matrícula SIAPE**. Neither appears
in the RFC's data model, and neither is required by any functional requirement.

- **CPF** — collecting it needs a stated purpose; "it was on the mockup" is not
  one. Recommendation: **do not collect**. E-mail plus SIAPE already identify a
  servidor uniquely within the entity. Tracked as OQ-10.
- **SIAPE** — justifiable as institutional identification; document the basis if kept.

Under art. 6, III (minimisation), the cheapest compliance measure available is
not collecting data you do not need. Every field removed here is a field that
cannot leak.

## Data subject rights

| Right | Implementation |
| --- | --- |
| Confirmation and access | Account settings screen shows all stored personal fields |
| Correction | Gestor edits via member management; servidor requests it |
| Anonymisation / deletion | Request to the entity's DPO; executed as AC-0001-14 |
| Portability | CSV export of personal data on DPO request |
| Revocation | Gestor deactivates; identifiable data anonymised, audit rows preserved under art. 16, I |

## The erasure / immutability tension

Art. 16, I permits retaining data to fulfil a legal obligation, which covers the
5-year audit retention. But an immutable table (ADR-0004) cannot be edited to
anonymise a name that was written into `dados_anteriores`.

**Resolution:** personal data is never written literally into
`dados_anteriores`. Audit rows reference `usuario_id` and store a stable
pseudonym. Anonymising a user rewrites the `USUARIO` row only; audit history
remains complete and immutable, and no longer resolves to a natural person.

This is a design constraint on every service that writes audit rows, not a
cleanup task — which is why it is fixed here, at AC-0007-06, rather than
discovered in M4.

## Operational obligations

- Name an encarregado (DPO) at the entity before production. Not an engineering
  task, but a blocker for go-live.
- Incident response: LGPD requires communicating relevant incidents to the ANPD
  and to data subjects. Write the procedure before M5, not after the first incident.
- Data is stored on-premise at the entity; no international transfer occurs.
