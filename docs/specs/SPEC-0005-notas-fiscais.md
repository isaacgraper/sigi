---
id: SPEC-0005
title: Notas Fiscais e conferência
status: Draft
version: 0.2
owner: Isaac Kleimann Graper
satisfies: [RF05, RF11, RF17, RN02, RN05, RN12]
depends_on: [SPEC-0004]
milestone: M4
---

# SPEC-0005 — Notas Fiscais e conferência

## 1. Purpose

The NF closes the cycle: it is the evidence that what was committed was
delivered. Carlos registers it, and Carlos mistypes, so validation quality here
determines whether the −70% error-reduction KPI is achievable.

## 2. Behaviour

**AC-0005-01** — A servidor registers an NF with número, data de emissão, valor,
fornecedor and the NE it belongs to (RN05); any missing field returns 422 naming
it individually.

**AC-0005-02** — The NF binds to `nota_empenho_id` only. There is no route,
schema field or column allowing a direct ATA link (RF05, RN02). The ATA is read
through the NE.

**AC-0005-03** — Binding to an NE whose status is not `ne_emitida` returns 409
`NE_NAO_EMITIDA`, with a test for each of the four non-terminal statuses.

**AC-0005-04** — `data_emissao` may not be in the future; 422 if it is.

**AC-0005-05** — `data_emissao` earlier than the NE's issuance date produces a
warning, not a rejection: the operator confirms explicitly, and the confirmation
is audited. This is a data-quality signal, and blocking it would make legitimate
back-dated documents impossible to register.

**AC-0005-06** — The supplier on the NF must match the supplier on the NE's ATA;
a mismatch returns 409 `FORNECEDOR_DIVERGENTE` naming both.

**AC-0005-07** — The sum of NF values bound to one NE may not exceed the NE
value; exceeding returns 409 `VALOR_ACIMA_DO_EMPENHO` stating both figures (RN12).

**AC-0005-08** — An NF moves through conference statuses `aguardando →
em_conferencia → aprovada | devolvida` (RF17); `devolvida` requires a
justification and permits re-submission.

**AC-0005-09** — A gestor may approve or return an NF; a servidor may register
and submit but not approve their own registration.

**AC-0005-10** — Approving an NF does not alter the ATA saldo. Saldo is deducted
by the NE, never twice. A test asserts the saldo is byte-identical before and
after NF approval — the double-deduction bug this criterion prevents would be
invisible until an audit.

**AC-0005-11** — Every NF mutation writes a `HISTORICO_MOVIMENTACAO` row.

## 3. Gap noted

The RFC's data model gives `NOTA_FISCAL` no status column, while Tela 7 shows
four statuses. This spec adds `status` and `justificativa_devolucao` to the
entity. Recorded as OQ-12.

## Revision 2026-09-02 — validated against operational data

**RN02 is confirmed by real data.** `ENTRADAS NFS (CSV)` links each
`numeroDocumento` to an `empenho`, and `Controle CAME 2026 › EMPENHOS` carries
`NF 1` … `NF 4` columns per empenho. One NE, many NFs, and the NF reaches the
ATA only through the NE — exactly as specified. No change needed.

**One consequence of ADR-0007.** RN12 (`Σ NF.valor` per NE may not exceed the NE
value) now compares against `Σ ITEM_NOTA_EMPENHO.valor`, since the NE header no
longer carries a value of its own. `DB6` is updated in the data model; the AC
wording here should follow when this spec moves to `Review`.

**An atesto workflow exists that this spec does not model.** The source carries
`dataHoraPrazoFinalAtesto`, `situacaoAtesto` ∈ {`Atestado e recebido no prazo`,
`Atestado e recebido fora do prazo`, `Sem atesto`} and
`prioridadeAtesto` = `Normal 48H` — a receipt-attestation SLA with a deadline
and a breach state. The four-status model here (`aguardando`, `em_conferencia`,
`aprovada`, `devolvida`) is not that. Out of MVP scope, consistent with the
decision not to ingest `ENTRADAS NFS` at all, but recorded so the status model
is not mistaken for complete. See OQ-22.

**`ENTRADAS NFS` is not ingested in the MVP.** Two reasons, both sufficient: the
entity states it has no use for it (*"já temos um controle interno nosso"*), and
it carries `pacienteNome` alongside `judicial` — identified health data. See
OQ-24 and `data-sources.md` §13.

## 4. Changelog

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-08-17 | Initial draft from RFC §2.3 RF05, §2.5 RN02/RN05, Tela 7 |
| 0.2 | 2026-09-02 | RN02 confirmed from real data; RN12 now aggregates over ITEM_NOTA_EMPENHO (ADR-0007); atesto SLA recorded as unmodelled (OQ-22); ENTRADAS NFS excluded on privacy and data-quality grounds (OQ-24) |
