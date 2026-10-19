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

## After the MVP — "Zero to Intelligent Governance" (v2)

*(Product owner, 2026-10-15.)* Not in scope until the MVP is delivered. Recorded
here so the MVP keeps what v2 will need, and so v2 starts from a decision rather
than a memory.

**Narrative.** *"You don't need a history to have a future."* Traditional systems
need years of data before they are useful; SIGI is useful on day one by closing
the data gap itself: `[no data] → [benchmarks and onboarding] → [governance]`.

**Target.** Organisations moving from spreadsheets and paper to digital
governance: medium-sized autarquias, hospitals, growing groups. Not mature
organisations already served by large ERPs. The current entity is that profile.

**Capabilities, in build order** (value first, risk last):

| # | Capability | What it does | Conditions |
| --- | --- | --- | --- |
| 1 | ATA ingestion from PDF | An LLM reads an ATA PDF or scan and fills items, prices, fornecedor, vigência and clauses | The result lands as `rascunho`; a gestor reviews it against the file and activates it. Never activated by software. The audit row names the source file. Pitch "extracted in seconds, reviewed by you", not "instant" |
| 2 | ATA depletion insight | "ATA 05 is consuming 40% faster than its vigência" | Deterministic: saldo committed against vigência elapsed. Needs SPEC-0004's NEs, not a model. Ship it as a feature, not as AI |
| 3 | Price benchmarks | Reference prices from public ATAs (PNCP, Painel de Preços) for the price research Lei 14.133 already asks for | Shown as a range with its sources. Reading public data is not a DOMS or e-Publica integration, but it needs its own ADR next to ADR-0002 |
| 4 | Quantity benchmarks ("pre-ATA") | A reference range for an ATA quota from comparable organisations | Public data shows what was registered or bought, not consumed, and quotas are often padded: a range with sources, never a recommendation. A new module before the ATA, where SIGI's scope starts today |
| 5 | Consumption anomaly alerts | A department asking for an unusual quantity compared with its peers | Per department, never per person (LGPD). Every alert shows its reasons. Named "alertas de consumo atípico", not "shadow auditor": the users are the people observed |
| 6 | Forecasting | Consumption per item, then fornecedor lead time from the NE → NF history | Statistical baselines first, backtested; one model across items second; incremental (online) learning only if nightly retraining cannot keep up with drift. Lead time is what only SIGI knows: DOMS already knows consumption |

In every stage a prediction is a suggestion with its reasons. It never buys,
never moves saldo and never writes estoque (invariant 5).

**Decisions v2 needs first:**

- An ADR lifting "ML forecasting" from the out-of-scope list in `CLAUDE.md`.
- An ADR for reading public procurement data (capabilities 3 and 4).
- Multi-tenancy. SIGI is built for one entity; selling to many is an
  architectural change, cheaper decided before v2 than retrofitted.
- Whether "pre-ATA" planning (demand, the estudo técnico preliminar) becomes a
  module, since today SIGI starts at the ATA.
- Market research. That an organisation without history wants traceability and
  prediction in one platform is the product owner's hypothesis, not yet
  evidence: who buys, what they use today, what they would pay, and whether
  prediction or traceability is what makes them buy.

**What the MVP keeps for v2, at no extra cost:** history. A model can only
learn from what the MVP did not throw away: every dated DOMS snapshot, and the
NE and NF dates as columns, not only as audit rows. The DOMS import spec
carries this as a requirement when it is written.

### Research notes (forecasting, capabilities 4 and 6)

*(2026-10-15, from the product owner's PhD advisors.)* To be explored further;
nothing here is decided.

- **The problem is regression**: consumption per item, the quota to register,
  a fornecedor's lead time. Consumption is a count and often zero, so Poisson or
  negative binomial regression is the baseline before anything heavier.
- **Neural networks for regression** are one candidate. On small tabular data,
  gradient-boosted trees usually win, so the study compares a count regression,
  gradient boosting and a neural network on the same data and reports which
  wins.
- **The core question is the cold start**: an organisation with no history
  borrows from a population of similar ones. Hierarchical (multilevel) models
  and transfer learning are the usual answers.
- **Real or synthetic data.** The algorithm learns from any sample, but it
  learns that sample's relationship: a model trained on generated data returns
  the generator's assumptions, and a sample that does not represent the target
  population predicts it badly. Synthetic data serves the pipeline, simulation
  studies with a known ground truth, privacy and rare cases. Real data is
  required for any reported accuracy and any claim about real organisations.
- **Candidate public sources**, coverage and granularity to verify: DATASUS
  (SIA/SIH, what each unit produces), Banco de Preços em Saúde (public purchases
  with price and quantity), IBGE (population served).
- **Study design sketch**: target consumption per item, unit and month;
  features population served, unit type, region, item class, season; a
  simulation study on synthetic data, then validation on public data; MAE and
  MASE, not MAPE, which breaks on months with zero demand.
