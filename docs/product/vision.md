# Product Vision

Status: Approved · Author: Isaac Kleimann Graper
Source: the entity's operational data and stakeholder statements (ADR-0009).
RFC SIGI v1.6 (22/05/2026) is retained as historical context.
Revised 2026-09-02.

## Problem

State government entities run the supply cycle across fragmented tools: the
"Controle CAME" spreadsheet, e-mail threads, and legacy systems. No single place
shows the state of a process. The consequences are concrete: no consolidated
auditable history for prestação de contas, duplicate manual entry of NEs and NFs
across systems, nomenclature drift against DOMS and e-Publica, and no way to
anticipate an ATA running out of saldo or vigência before it happens.

## Solution in one sentence

A web platform that makes the full administrative cycle — `ATA → NE → NF →
conclusão` — traceable and auditable, and that surfaces the **coverage** figure
the team already uses to decide what to buy, before an item runs out.

*(2026-09-02)* The second half was added after observing the operation. The
entity's daily decision is not "what is the state of this process" but "this
item's coverage fell below three months — do I have an ATA with saldo to buy
against?". A platform that answers only the first question would be adopted
alongside the spreadsheet rather than instead of it.

## What SIGI is not

Explicitly out of scope (RFC §2.6). Treat any request in these areas as scope
creep and route it to the post-MVP backlog:

- Financial or accounting module; payment execution.
- Payroll integration.
- Machine-learning forecasting.
- Native mobile application.
- Any integration beyond DOMS and e-Publica.
- Public transparency portal.
- **Being the system of record for physical stock.** DOMS owns stock. SIGI
  imports a **dated snapshot** of what DOMS already computes (`estoque_atual`,
  `dias_estoque`, `curva_abc`, `estoque_minimo`, `ponto_pedido`) and never
  computes, adjusts or recounts it. There is still no "entrada de estoque"
  operation, and the importer is the only writer. *(2026-09-02: revised under
  ADR-0008/ADR-0009. The earlier wording forbade SIGI from reading what the
  entity measures, which would have left the coverage decision outside the
  product.)*
- **Payment execution.** Liquidação is modelled as NF conference; paying is not.

## Users

Internal public servants with basic IT literacy, comfortable with spreadsheets
and corporate web systems.

*(2026-09-02)* The three personas below were written from the RFC. The
operational data shows two further roles the model does not carry, both visible
in every export: the **comprador**, who owns a grupo de materiais and works a
purchase list, and the **gestor de unidade**, who raises requests within a
cronograma window and has no visibility of central stock. Both entered the data
model under OQ-26, and between them they answer what RN07 called "área de
competência" (OQ-04): the two axes are **unidade** and **grupo de materiais**.
SPEC-0001 still has to adopt them as roles.

### Mariana — Gestora de Aquisições (`gestor`)

38, eight years in the role. Issues ATAs, opens NE requests, tracks the cycle.
Today juggles stale spreadsheets and scattered e-mail. Her measure of success is
answering an audit question in minutes rather than days.
**Design implication:** dashboard-first, exceptions surfaced (ATAs a renovar,
saldo crítico) rather than requiring her to go looking.

### Carlos — Servidor de Recebimento (`servidor`)

45, twelve years of service. Registers NFs, advances NE steps. Dislikes complex
systems; frequently mistypes when transcribing between systems.
**Design implication:** the transcription error is the enemy. Inline validation
with specific per-field messages, dropdowns over free text, format masks on
`codigo` and `processo_sei`, and never a silent failure.

### Ana — Auditora Interna (`auditor`)

32, periodic audits of public spending. Needs complete and immutable history and
exportable reports.
**Design implication:** read-only by construction, not by convention. Every
report must be reproducible: an export must state the moment it reflects.

## Origin and evidence

Demand identified at PROCON/CAC, Santa Catarina, through Anderson Viebranz,
Gerente de Insumos, Materiais e Medicamentos. Exploratory research with two
servidores (A.V. and E.R.) validated the `ATA → NE → NF` flow, the need for an
immutable audit trail, the KPI dashboard, and the NE stage pipeline.

**Known evidence weakness:** n=2, single unit, both participants combining
gestor and auditor duties. The `servidor` persona (Carlos) is inferred, not
observed. Validating with an actual receiving clerk is the highest-value
research action before M3. See `open-questions.md` OQ-14.

## Differentiators

Against SIAD, SIGMAT, spreadsheets, Totvs Protheus and Comprasnet/PNCP, none
covers post-ATA cycle traceability for a state entity. SIGI's specific claim is:
structured NE flow as the product core, operational consistency with the tools
the entity already uses, and an immutable per-process history.

## Success metrics

| Metric | Target | Instrument | Baseline needed? |
| --- | --- | --- | --- |
| API latency | < 300 ms p95 | APM | No |
| NE/NF registration time | ≥ 50% reduction | Timed task vs. current flow | **Yes — measure before M3** |
| ATA tracking coverage | 100% of active ATAs | Coverage report | No |
| Availability | ≥ 99.5% monthly | Uptime monitoring | No |
| Active MVP users | ≥ 5 | Access logs | No |
| NF entry errors | −70% | Compare with history | **Yes — measure before M3** |
| ATA entry errors | −70% | Compare with history | **Yes — measure before M3** |

Three of these targets are relative to a baseline that does not exist yet. A
timed observation session with Carlos-equivalent users during M1–M2 is a
prerequisite for claiming them. Tracked as OQ-15.
