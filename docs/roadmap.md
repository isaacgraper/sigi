# Roadmap

> **This plan no longer covers the scope.** *(2026-09-02)* It was built on RFC
> §7.1's 16 weeks, sized against the RFC's scope. ADR-0009 makes the operational
> data the source of truth, and the data carries entities the RFC never
> mentioned: `UNIDADE`, `CENTRO_CUSTO`, `SOLICITACAO`/`ITEM_SOLICITACAO`,
> `CRONOGRAMA`, `POSICAO_ESTOQUE_SNAPSHOT`, `PROCESSO_LICITATORIO` and its two
> children, `ACAO_ITEM` — plus `ITEM_NOTA_EMPENHO` from ADR-0007, which changes
> the spine.
>
> Nine new entities, two new roles and a second approval state machine
> (`SOLICITACAO`) do not fit in the same sixteen weeks. Re-plan with the
> stakeholders before committing to a date. The sequencing below is the honest
> ordering; the week numbers are not.

16 weeks from kickoff, per RFC §7.1. Note that §7.2 states there is no schedule,
contradicting §7.1 — treated as an editing leftover (OQ-16).

Milestones are reframed here as spec sequences, so progress is measurable as
"specs Implemented" rather than "weeks elapsed".

## M1 — Setup and PoC (weeks 1–2)

Repository, Docker Compose, CI, `/health`, `/auth` skeleton, Alembic baseline,
testcontainers harness.

Specs: none implemented. **Deliverable: this `docs/` tree reviewed and at least
SPEC-0001 and SPEC-0004 promoted to `Approved`.** Also: revoke the leaked
prototype token (OQ-17) and add `gitleaks`.

*(2026-09-02)* OQ-05 and OQ-04 no longer need the stakeholder — the data
answered both. What does need them: re-planning the milestones against the new
scope, confirming a 37-item empenho is ordinary (ADR-0007), and OQ-24, the
patient data in the export, which is a privacy matter and should not wait.

## M2 — Backend core (weeks 3–6)

SPEC-0001 (auth, RBAC, members) → SPEC-0002 (ATAs) → SPEC-0003 (insumos) →
SPEC-0007 (audit trail) → SPEC-0006 (saldo) → SPEC-0004 (NE flow).

*(2026-09-02)* SPEC-0003 now carries `GRUPO_MATERIAL` and the four item
identifiers; SPEC-0004 carries `ITEM_NOTA_EMPENHO`. Both grew.
`UNIDADE`/`CENTRO_CUSTO` and `POSICAO_ESTOQUE_SNAPSHOT` belong here too — the
coverage view is the highest-value addition and the cheapest of the new
entities, since it is import-only with no write path.

Order matters: the audit trail lands **before** the NE flow, because
retrofitting transactional history onto an existing state machine means
revisiting every write path. Saldo lands before the NE flow because the NE guard
depends on it.

Exit criteria: every AC in these specs has a passing test; `/trace` reports no
unmapped criteria; coverage ≥ 70%.

## M3 — Frontend MVP (weeks 7–10)

Login, Dashboard, ATAs, Insumos, Saldo por ATA, Notas de Empenho.

Ship the NE pipeline screen first, not the dashboard. It is the core of the
product and the screen most likely to reveal a wrong model, and finding that in
week 7 is survivable in a way that finding it in week 12 is not.

Prerequisite: interview a receiving clerk (OQ-14) and take the baseline
measurements the KPIs depend on (OQ-15).

## M4 — Complete features (weeks 11–13)

SPEC-0005 (NFs + conference) → SPEC-0008 (notifications, now aggregated digests)
→ SPEC-0009 (reports) → LGPD conformance pass.

*(2026-09-02)* Gov.br is **cut**, not deferred: the 17/08 meeting shows the
entity uses Entra ID and nobody asked for Gov.br (OQ-09). New specs needed here
for `SOLICITACAO`/fulfilment and `PROCESSO_LICITATORIO`, neither of which
existed when this milestone was sized.

## M5 — Testing and deploy (weeks 14–16)

UAT with PROCON/CAC users, OWASP checklist, load tests (RNF01, RNF05), backup and
**rehearsed restore** (RNF11), technical documentation, production deploy with
monitoring.

## Schedule risks

| Risk | Effect | Response |
| --- | --- | --- |
| ~~OQ-05 answered "NEs are multi-item" after M2~~ | ~~Data-model change through the system's core~~ | **Resolved 2026-09-02, before any code: NEs *are* multi-item (27,8%, up to 37). ADR-0007. The risk landed and was absorbed at its cheapest possible moment.** |
| ~~Gov.br registration lead time~~ | ~~M4 slips~~ | **Retired 2026-09-02.** The risk was imaginary: nobody asked for Gov.br. The 17/08 meeting names Entra ID, against which servidores already hold credentials (OQ-09). Cut from M4 rather than deferred. |
| On-premise operations (TLS, backups, uptime) | Invisible in the plan; consumes M5 | Budget explicitly in M1 and M5, not as a rounding error. |
| Single developer, two stacks | Frontend and backend compete for the same weeks | The vertical-slice order above keeps a working system at every milestone rather than a complete backend and no UI. |
| RF15/RF16/RF17 (aditivo, reajuste, NF conference) appear only in mockups | Hidden scope discovered mid-build | Already surfaced in `requirements/functional.md`; decide in/out at M1. |
| **Scope re-anchored to operational data (ADR-0009)** | Nine new entities, two new roles, a second state machine. The 16-week plan does not hold | Re-plan with stakeholders. Sequence by value: coverage view first (import-only), fulfilment second, processo licitatório third |
| **The evidence is a snapshot** | The workbooks are dated 10/07 and 01/04/2026. Re-anchoring freezes a moment; the next export may differ | Re-run `scripts/analise-planilhas.py` against each new export and diff the findings before treating them as settled |
