# Open Questions

Contradictions, gaps and decisions that need a human — mostly the stakeholder at
PROCON/CAC or the orientador. Each has a proposed answer so the project is never
blocked waiting for one, and a blast radius so you know which ones to chase first.

**Do not silently resolve these in code.** If you implement the proposal, say so
in the spec's changelog and mark the question `Assumed`.

*(2026-09-02, ADR-0009)* This file's scope narrowed. Operational data now governs
scope, so a contradiction the **data answers** is a defect in the spec — fixed
there, with the evidence cited in its changelog. Only what the data genuinely
does not answer belongs here: policies, lead times, intentions and priorities.
Several rows below were resolved that way rather than by asking anyone.

| ID | Question | Blocks | Proposed answer | Status |
| --- | --- | --- | --- | --- |
| OQ-01 | Is an insumo owned by one ATA (RF03: "ATA vinculada") or shared across ATAs via `ITEM_ATA` (data model)? | SPEC-0003 | Catalogue-global insumo; ATA link only via `ITEM_ATA`. Ownership would break DOMS code uniqueness. | Assumed |
| OQ-02 | Does e-Publica import work by process-number lookup (RF04) or CSV upload (mockup 9.2.2.1)? | SPEC-0002 | **Neither.** The 2026-09-02 export contract contains no ATA report at all — ATAs do not come from DOMS. The 17/08 meeting names *República*; the data names **Cincatarina** as a purchase channel (22 items `COMPR. CINCATARINA`, 49 `Compra CINCATARINA`). ATAs are entered manually; only their items are imported by CSV. | **Resolved** |
| OQ-03 | Saldo is validated at `validacao_saldo` but deducted at `ne_emitida`. What happens in between? | SPEC-0004, SPEC-0006 | Three-state model: reserved from `pre_empenho`, committed at `ne_emitida`. | Assumed |
| OQ-04 | RN07 requires an "área de competência" that exists on no entity. What is it — órgão, setor, categoria de insumo? | SPEC-0001, RN07 | **Answered by the data:** the operation scopes by **unidade** and by **grupo de materiais** — compradores own grupos, gestores de unidade own units. Both entities now exist (OQ-26), so RN07 becomes implementable as a two-axis scope on `USUARIO`. Needs SPEC-0001 to adopt it. | **Resolved — spec change pending** |
| OQ-05 | Can one NE cover multiple insumos? Real empenhos usually do. | SPEC-0004 | **Yes — 27,8%.** Measured on `Controle CAME 2026 › EMPENHOS`: 482 distinct empenhos, 134 multi-item, largest covering **37** insumos. The one-item assumption is withdrawn; `ITEM_NOTA_EMPENHO` added. See ADR-0007. | **Resolved** |
| OQ-06 | `NOTA_EMPENHO` carries `ata_id`, `insumo_id` and `item_ata_id`. Keep the redundancy? | data-model | **Narrowed by ADR-0007.** `insumo_id` and `item_ata_id` moved to `ITEM_NOTA_EMPENHO`, so the three-way redundancy is gone. `ata_id` is kept on the header on purpose — it carries the invariant that all items of an NE share one ATA — guarded by the trigger now specified as DB2. | **Resolved** |
| OQ-07 | The RFC has no way to cancel an NE opened in error. Is cancellation permitted administratively? | SPEC-0004 | Add `cancelada`, gestor-only, justification mandatory. Without it, an erroneous NE holds reserved saldo forever. **Implemented in SPEC-0004 v0.3 (AC-0004-16).** If the entity says otherwise, that is the criterion to revisit. | **Assumed** |
| OQ-08 | What is the entity's reajuste policy (index, window, who approves)? | RF16 | Partially answered by the data: `Controle de ITENS` carries **`DATA LIMITE REAJUSTE` per item**, so the window is per-item and already tracked. Index and approver still unknown. RF16 stays unspecified pending those two. | **Open** |
| OQ-09 | Will the entity register with Gov.br for OAuth, and by when? | SPEC-0001, RF01 | **Wrong question.** In the 17/08 meeting nobody mentioned Gov.br; servidores already hold credentials provisioned by the entity's TI, and the discussion was about **Entra ID**. Gov.br is citizen-to-state federation and does not fit an internal-servidor audience. Proposal: institutional SSO (Entra ID) as the primary mechanism, Gov.br dropped from scope. **Needs confirmation** with the entity's TI. | **Open** |
| OQ-10 | Why does the profile screen collect CPF? | SPEC-0001, LGPD | Do not collect. No requirement needs it, and it raises the LGPD burden. | **Open** |
| OQ-11 | Can an ATA have more than one fornecedor? | data-model | **Yes, but rarely.** 29 of 456 ATAs (6,4%) carry more than one fornecedor, up to three. The single-`fornecedor_id` model is wrong for those. Modelling response deferred to SPEC-0002 — most likely fornecedor moves to `ITEM_ATA`. | **Resolved — model change pending** |
| OQ-12 | The NF entity has no status, but Tela 7 shows four. | SPEC-0005 | Add `status` + `justificativa_devolucao`. | Assumed |
| OQ-13 | Is an external e-mail SaaS (Resend) acceptable for a state entity, and can it reach internal `.gov.br` addresses? | SPEC-0008 | Institutional SMTP as default, transport behind a port interface. | Assumed |
| OQ-14 | The `servidor` persona (Carlos) is inferred, not observed; research covered two gestor/auditor users. | vision | Interview one receiving clerk before M3. The whole UX argument rests on this persona. | **Open** |
| OQ-15 | Three KPIs are relative to a baseline that has never been measured. | vision, KPIs | Partially unblocked: the workbooks give real volumes (coverage bands 156/167/102/71/278 items, 135 sem giro, 250 zerados, ~1.425 SKUs). Those are *stock* baselines. The three KPIs that still lack a baseline are the **time-and-error ones** (NE/NF registration time, entry-error rates), which no export contains — they still need the timed observation. | **Open** |
| OQ-16 | RFC §7.2 says "não há cronograma", while §7.1 defines 16 weeks across five milestones. Which governs? | roadmap | §7.1 governs; §7.2 appears to be an editing leftover. Fix in the next RFC revision. | **Open** |
| OQ-17 | The RFC appendix publishes a live prototype JWT. | security | Revoke it. Do not copy it into the repository. | **Open — act now** |
| OQ-18 | Who is the entity's DPO for LGPD data-subject requests? | LGPD | Required before go-live. | **Open** |
| OQ-19 | If no ATA export exists, how do ATAs enter SIGI — and what is Cincatarina's role? | SPEC-0002 | Manual ATA registration + CSV import of items. Cincatarina appears to be a shared-purchase channel producing ATAs the entity did not run itself. **Needs stakeholder answer** — it may be a distinct ATA origin with its own rules. | **Open** |
| OQ-20 | Saldo is modelled per ATA in value; the operation tracks it per item in quantity. Which drives the block in RN10? | SPEC-0006 | **Both, and the model carries both.** Quantity per `ITEM_ATA` drives the purchase decision; value per ATA answers the audit question. RN10 blocks on whichever is exhausted first. Resolved under ADR-0009 — the operation tracks quantity, so the model must. | **Resolved** |
| OQ-21 | 12 of the 17 `STATUS DA ATA` values describe the acquisition process, not the ATA. Does SIGI model the processo licitatório? | SPEC-0002, data-model | **Yes.** `PROCESSO_LICITATORIO`, `ETAPA_PROCESSO` and `ITEM_PROCESSO` added to the data model, with the 9 stages and planned-vs-actual the CAME dashboard tracks. `canal` records Cincatarina. Milestone placement in `roadmap.md`. | **Resolved** |
| OQ-22 | `ENTRADAS NFS` carries an atesto SLA (`prazoFinalAtesto`, `Atestado e recebido no prazo/fora do prazo`, `Normal 48H`) that SPEC-0005's NF status model lacks. In scope? | SPEC-0005 | Out of MVP scope, consistent with not ingesting that report. Record it so the four-status model is not mistaken for complete. | **Open** |
| OQ-23 | Items are substituted and discontinued (`ITEM SUBSTITUIDO POR ITEM 43204`); RN14 declares `codigo` immutable once referenced. | SPEC-0003, RN14 | Keep `codigo` immutable and add `substituido_por_id` — substitution becomes a link, never a rewrite, so historical NEs stay correct. RN14 needs rewording to say so. | **Open** |
| OQ-24 | `ENTRADAS NFS` contains `pacienteNome` alongside `judicial` — identified health data, in a flow the RFC places out of scope. | lgpd.md, security | Do not ingest that report (already the decision on data-quality grounds). If ever ingested, drop `pacienteNome` at the importer, before persistence and before any log. `lgpd.md` maps no health data today and must say why none is collected. **Act before any import work.** | **Open** |
| OQ-25 | Coverage is refreshed **monthly**, not daily. Can any requirement promise a daily shortage view? | RF20, ADR-0008 | **No.** Monthly is the cadence, so every surface shows `data_referencia` and no requirement promises daily freshness. Whether the entity can export more often is worth asking, but nothing depends on the answer. | **Resolved** |
| OQ-26 | There is no `UNIDADE` entity, yet every stock and fulfilment row is keyed by unit, and fulfilment has five quantities. | data-model, vision | **In scope.** `UNIDADE`, `CENTRO_CUSTO`, `SOLICITACAO`, `ITEM_SOLICITACAO` (all five quantities) and `CRONOGRAMA` added under ADR-0009. The `comprador` and `gestor_unidade` roles follow, which also gives RN07/OQ-04 the two axes it lacked: unidade and grupo de materiais. | **Resolved** |
| OQ-27 | With multi-item NEs, may an item be removed from an NE after `pre_empenho`, when saldo is already reserved? | SPEC-0004, SPEC-0006 | No — itens freeze at `pre_empenho`; correction is cancel-and-reopen, so the reservation trail stays auditable. **Implemented in SPEC-0004 v0.3 (AC-0004-22).** | **Assumed** |
| OQ-28 | `docs/rfc-sigi-v1.7.md` was merged in PR #4 and reuses requirement IDs that already mean something else (`RF05`, `RN11`, and the whole `RF04`–`RF30` range). It is also contradicted by the data on five points. Keep it as history, or delete it? | traceability, `functional.md`, `business-rules.md` | Delete. It is superseded in full: its valid findings live in ADR-0007/0008/0009 and `data-sources.md`, and the analysis that produced it survives in `analise-lacunas-rfc-v1.6.md`. Leaving two definitions of `RF05` and `RN11` in `docs/` breaks the "one test named after each RN" rule and makes `traceability.md` unresolvable. **Needs the author's decision** — it was merged through an approved PR and deleting merged content is not mine to do. A banner marks it Superseded meanwhile. | **Open — decide before any test is written** |
| OQ-29 | An item has four identifiers (`SKU`, DOMS client code, `mercadoriaId`, `Nº ITEM`) and a three-level group hierarchy. Which is canonical, and who owns the mapping? | SPEC-0003, RN14 | `codigo` = DOMS client code (the only one shared across sources); `sku` and `codigo_externo` carried alongside for joins. Hierarchy modelled as self-referencing `GRUPO_MATERIAL`. **Needs the entity to confirm** the DOMS code is stable. | **Open** |

## How to use this file

- Bring the four highest-impact items to the next stakeholder meeting; the rest
  can travel in writing. As of 2026-09-02 those are **OQ-26** (no `UNIDADE`
  entity — the widest gap against what the entity actually measures),
  **OQ-24** (patient data in the export — act before any import work),
  **OQ-28** (two definitions of `RF05`/`RN11` in `docs/` — decide before any
  test is written) and **OQ-19** (how ATAs enter SIGI, and Cincatarina's role).
  OQ-04 and OQ-07 left this list: the data answered the first and the second is
  now `Assumed` in SPEC-0004. OQ-17 remains an act-now security item independent
  of any meeting.
- Questions resolved on 2026-09-02 were resolved **by data**, not by opinion:
  every figure is reproducible with `scripts/analise-planilhas.py`. See
  `docs/architecture/data-sources.md`.
- When one is answered, update the row to `Resolved`, record the answer, and
  amend the affected spec with a changelog entry.
- New contradictions found during implementation are added here, not fixed in
  passing. A quietly resolved contradiction is a decision nobody made.
