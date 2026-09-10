# ADR-0009 — Operational data supersedes the RFC as the source of truth

- **Status:** Accepted
- **Date:** 2026-09-02
- **Deciders:** Isaac Kleimann Graper (product owner)
- **Related:** ADR-0002, ADR-0003, ADR-0007, ADR-0008, `docs/architecture/data-sources.md`, `CLAUDE.md`

## Context

Until now the hierarchy was: **RFC v1.6 → vision.md → specs → code**, with the
RFC frozen and contradictions routed to `open-questions.md`. `sdd-workflow.md`
states it plainly: *"RFC_SIGI v1.6 is the frozen problem statement. It is not
edited during implementation."*

That hierarchy was sound while the RFC was the best available description of the
problem. It no longer is. Two sources now describe the operation directly rather
than by report:

- the **17/08/2026 meeting** with Anderson and Eduardo, in which the operating
  loop was demonstrated live;
- the **workbooks supplied on 02/09/2026**, including
  `CSVs_disponeis_para_SIGI.xlsx` — an export contract annotated by Eduardo with
  the usefulness of each report — and `Controle CAME 2026`, the system the team
  actually runs.

Cross-checking them against the documentation (`data-sources.md`) found the RFC
wrong on points that are not cosmetic: an NE covers many insumos, not one; there
is no ATA export at all; the entity's stock parameters are already computed
upstream; eleven of sixteen columns in the coverage report have nowhere to land.

Where a document and the operation disagree, the operation is not the exception.
It is the requirement. A specification that describes something the entity does
not do is not a contract — it is a wish.

## Options considered

| Option | Pros | Cons |
| --- | --- | --- |
| Keep the RFC supreme; route every conflict to `open-questions.md` | Stable, auditable, already in place; the RFC is also the committee deliverable | Every finding becomes a question nobody is positioned to answer, because the answer is already visible in the data. The backlog of "Open" grows while the product drifts from the operation |
| Rewrite the RFC to match the data | One document again | The RFC is a dated academic artifact with an evaluation panel attached; rewriting it retroactively destroys the record of what was known when. And it would be rewritten again after the next meeting |
| Re-anchor: operational data governs; the RFC becomes historical context | The specification describes what the entity does; conflicts resolve by evidence rather than by discussion | The frozen contract stops being frozen, so "the RFC says so" is no longer an argument. Scope grows, and the roadmap built on the RFC's scope no longer holds |

## Decision

**The shared operational sources are the source of truth for what SIGI must do.**
In descending authority:

1. **Operational data** — the workbooks and CSV exports the entity supplies,
   mapped in `docs/architecture/data-sources.md`.
2. **Direct stakeholder statements** — meeting transcripts and annotations, such
   as Eduardo's notes in the `HUB` sheet.
3. **This repository's specs and ADRs** — which must be revised when 1 or 2
   contradict them.
4. **RFC v1.6** — historical context. It records the problem as understood in
   May 2026 and remains the artifact submitted to the evaluation panel. It is no
   longer the arbiter of scope.

Consequences that follow immediately:

- **A conflict between the data and a spec is a defect in the spec.** It is
  fixed in the spec, with a changelog line citing the evidence — not filed as an
  open question. `open-questions.md` returns to its proper purpose: things the
  data genuinely does not answer.
- **Evidence must be reproducible.** A claim about the operation cites a file,
  sheet and column, and where it is a figure, it is reproducible with
  `scripts/analise-planilhas.py`. Re-anchoring to data is only an improvement if
  the data is checkable; otherwise it is re-anchoring to memory.
- **`ADR-0008` is accepted** by this decision. Its question — may SIGI read the
  stock signals DOMS already computes — is answered by the hierarchy above: the
  entity's coverage-driven loop is the operation, so SIGI must represent it.
  Its safeguards (import-only, no write path, dated snapshots) stand.
- **The scope boundary moves.** `vision.md`'s "no physical inventory control"
  and `CLAUDE.md` invariant 5 were written from the RFC. They are reworded to
  forbid what actually matters — SIGI computing or mutating stock — rather than
  forbidding it from reading what the entity measures.
- **The RFC's silence is not a prohibition.** Previously, absence from the RFC
  meant out of scope. Now, presence in the operation means in scope, subject to
  milestone prioritisation like anything else.

## Consequences

**Positive** — The specification can describe the product the entity would
actually adopt. Findings resolve by measurement instead of by opinion, which is
faster and less arguable. The `UNIDADE`/fulfilment gap — the widest distance
between what the entity measures and what SIGI represents — stops being blocked
on a question nobody was going to answer.

**Negative** — This is a real scope increase, and it invalidates the 16-week
plan built on the RFC's narrower scope; `roadmap.md` is updated to say so rather
than absorb it silently. It also removes a discipline that was doing useful
work: "the RFC does not say so" was a cheap way to stop scope creep, and its
replacement — "the data does not show it" — requires someone to actually check
the data. Reviewers must now be able to read `data-sources.md`, not just the
specs. Finally, the evidence is a **snapshot**: the workbooks are dated
10/07/2026 and 01/04/2026, so re-anchoring to them freezes a moment, and the
next export may move again.

**Follow-up**

- `CLAUDE.md` — scope source, invariant 5, and the scope-creep list.
- `product/vision.md` — "What SIGI is not"; `product/glossary.md` — the
  "Estoque" avoidance and the new domain terms.
- `process/sdd-workflow.md` — the RFC step in the loop.
- `.claude/skills/sigi-domain/SKILL.md` — the "recurring mistakes" list.
- `architecture/data-model.md` — the entities recorded as missing become
  entities to model.
- `open-questions.md` — those blocked on a product decision are resolved here.
- `roadmap.md` — state the impact honestly.
