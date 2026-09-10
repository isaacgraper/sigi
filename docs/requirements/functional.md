# Functional Requirements

Verbatim intent from RFC v1.6 §2.3, with the implementing spec and an
implementability note where the RFC is ambiguous. **Do not edit the "Requirement"
column** — it is the frozen contract. Clarifications go in the notes column and
in `open-questions.md`.

| ID | Requirement | Spec | Note |
| --- | --- | --- | --- |
| RF01 | Secure authentication with institutional credentials or Gov.br | SPEC-0001 | Gov.br OAuth requires entity registration with the federal portal; treat as M4 risk. **2026-09-02:** the 17/08 meeting names **Entra ID**, not Gov.br — servidores already hold TI-provisioned credentials. Gov.br was never mentioned. See OQ-09 and SPEC-0001 v0.2. |
| RF02 | Gestor registers and manages entity members/servidores | SPEC-0001 | |
| RF03 | Servidor registers insumos referenced in ATAs with DOMS-compatible `codigo`, linked ATA, name, category, unit; reference quantity optional, for process alerts only | SPEC-0003 | **Conflict:** RF03 puts an ATA on the insumo, but the data model uses `ITEM_ATA` for the N:N. Resolved in SPEC-0003: insumo is catalogue-global; the ATA link is `ITEM_ATA`. See OQ-01. **2026-09-02:** four identifiers exist, not one, and categoria is a three-level hierarchy. See OQ-29. |
| RF04 | Gestor registers an ATA manually or by importing via e-Publica process number | SPEC-0002 | Mockup 9.2.2.1 shows a **CSV upload**, not a lookup by process number. Resolved as CSV. See OQ-02. **2026-09-02:** superseded by data — there is **no ATA export at all**. Manual registration + CSV of items. Some ATAs come via Cincatarina. OQ-19. |
| RF05 | Servidor registers NFs bound to an NE (not directly to an ATA); the ATA link is inherited | SPEC-0005 | |
| RF06 | Any authenticated user views the current cycle status of an insumo (ATA → NE → NF) | SPEC-0007 | Subject to RN07 scoping. |
| RF07 | Operational consistency with DOMS by validating item codes; no automatic API integration | SPEC-0003 | Format validation + in-app guidance only. ADR-0002. |
| RF08 | Operational consistency with e-Publica by validating process numbers; no automatic API integration | SPEC-0002 | Format validation only. ADR-0002. |
| RF09 | E-mail notification to the responsible party on supply status change | SPEC-0008 | **2026-09-02:** the entity's TI will block per-event e-mail as spam; RF09 needs aggregated digests per comprador. SPEC-0008 v0.2. |
| RF10 | Immutable auditable history of all insumo, NE and NF movements | SPEC-0007 | Enforced at database level, not application level. |
| RF11 | Validate mandatory fields on insumo, ATA, NE and NF registration | SPEC-0002/3/4/5 | |
| RF12 | Auditor consults exportable reports (PDF/CSV): insumo lifecycle, budget execution per ATA, consolidated balance, supplier indicators | SPEC-0009 | |
| RF13 | Manage the NE flow through five sequential steps, with indicators for issued, in-progress and total | SPEC-0004 | The core requirement. **2026-09-02:** an NE covers **many** insumos (27,8%, up to 37). ADR-0007. SPEC-0004 v0.3. |
| RF14 | Show current saldo per ATA derived from issued NEs, deducting automatically and flagging ATAs ≥ 80% consumed | SPEC-0006 | **Gap:** deduction timing vs. RN10 validation timing. Resolved via reservation semantics in SPEC-0006. See OQ-03. **2026-09-02:** confirmed empirically — the source spreadsheet's stored saldo diverges from its derived one in 32,5% of rows. Aggregation moves to ITEM_NOTA_EMPENHO. SPEC-0006 v0.3. |

## Requirements implied by the mockups but absent from RF01–RF14

The RFC's screens describe behaviour no requirement covers. These are real scope
and must be either specified or explicitly deferred — silently implementing them
is how a 16-week plan becomes a 24-week one.

| ID | Behaviour | Evidence | Disposition |
| --- | --- | --- | --- |
| RF15 | Register an **aditivo** to an ATA (quantity/value increase, max 25%) | Tela 4 "Ações: Aditivo"; alternative flow "solicitar aditivo à ATA" | **Must specify** — it changes saldo, so SPEC-0006 is incomplete without it. |
| RF16 | Register a **reajuste** of ATA prices with an availability window | Tela 4 "Reajuste (disponível/expirado + dias)" | **Must specify** — changes unit prices and therefore future consumption. |
| RF17 | NF conference workflow with statuses (Aprovada, Em conferência, Aguardando, Devolvida) | Tela 7 status badges | **Must specify** — the data model has no NF status field. |
| RF18 | Invite a user by e-mail with a pending-activation state; block/unblock accounts | Mockup 9.2.3 (Pendente, Bloqueado, "Convidar usuário") | **Must specify** — SPEC-0001 covers it. |
| RF19 | Renewal alert for ATAs expiring within 90 days without an aditivo | Tela 4 alert banner | Specified in SPEC-0002. |
| RF20 | Coverage-profile alerts ("sem demanda há ≥ X meses", "cobertura < X dias") | Tela 8 sliders | ~~Defer to post-MVP — requires consumption-rate history that will not exist at launch.~~ **2026-09-02: that premise is false.** The entity exports `COBERTURA DE ESTOQUE (CSV)` (5.290 rows, monthly) and keeps `MÉDIA DE CONSUMO POR ITENS` (15.721 rows). **In scope** under ADR-0008/ADR-0009: the coverage view is the loop the entity actually runs. |
| RF21 | Saldo runway projection per ATA (burn-rate to exhaustion vs. days of vigência) | Colleague contribution, Appendix | **Defer to post-MVP**, but design SPEC-0006 so it is a pure read-model addition. **2026-09-02:** consumption history exists (see RF20); the 17/08 meeting asked for exactly this — *"quanto tempo de estoque essa ata vai durar"*. Gated on ADR-0008. |

## Requirements the operational data implies but no RF covers

*(2026-09-02)* Found by cross-checking the entity's workbooks against this list.
Recorded, not adopted — each needs a scope decision. See
`docs/architecture/data-sources.md`.

| Behaviour | Evidence | Blocked on |
| --- | --- | --- |
| Fulfilment rate per unidade (solicitada / autorizada / atendida / pendente / pendente-sem-estoque) | `TRANSFERENCIA CONSOLIDADO (CSV)`, 8.461 rows — the report the entity rates most important | OQ-26 (no `UNIDADE` entity) |
| Solicitation workflow with cronograma windows (autorização → aprovação → finalização) | `REQUISIÇÃO ENTRE UNIDADES (CSV)`, 30 columns, 12.658 rows | OQ-26 |
| Acquisition-process tracking (9 stages, planned vs. actual) | 12 of 17 `STATUS DA ATA` values; `STATUS PREGÃO` | OQ-21 |
| Action-in-progress on a critical item (11 values, incl. `SEM ATA`, `SEM SALDO DE ATA`, `AGUARDANDO RETORNO SAP`) | `ESTOQUE <3 › STATUS` | OQ-21, OQ-26 |
| Lote and validade per movement | `TRANFERENCIA DE MERCADORIA (CSV)` | OQ-23 |
| NF atesto SLA | `ENTRADAS NFS (CSV)` | OQ-22 |
