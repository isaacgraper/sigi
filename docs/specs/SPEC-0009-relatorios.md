---
id: SPEC-0009
title: Relatórios e exportações
status: Draft
version: 0.1
owner: Isaac Kleimmann Graper
satisfies: [RF12]
depends_on: [SPEC-0006, SPEC-0007]
milestone: M4
---

# SPEC-0009 — Relatórios e exportações

## 1. Purpose

Ana's deliverable. A report that cannot be reproduced six months later cannot be
used in an audit, so reproducibility is the governing requirement, not layout.

## 2. Behaviour

**AC-0009-01** — Four exports are available in PDF and CSV: execução
orçamentária por ATA, posição de saldo consolidada, notas fiscais em conferência,
indicadores de fornecedores (RF12).

**AC-0009-02** — Every export carries a header with the generation timestamp, the
requesting user, the applied filters, and the reference period. An export
without provenance is an anonymous spreadsheet.

**AC-0009-03** — Re-running an export with identical filters and reference date
produces identical figures, even after later data changes, because every report
is computed as-of an explicit instant.

**AC-0009-04** — Generating an export writes an audit row: who exported what, when.

**AC-0009-05** — An auditor can generate every report; no report route accepts a
write.

**AC-0009-06** — CSV uses UTF-8 with BOM and `;` separators so that Excel in
pt-BR locale opens it correctly without an import wizard. Getting this wrong
means every user "fixes" the file by hand, and the fixed copies become the
records people actually circulate.

**AC-0009-07** — Reports exceeding 5.000 rows are generated asynchronously with a
download link, rather than timing out an HTTP request.

## 3. Changelog

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-08-17 | Initial draft from RFC §2.3 RF12, Tela 8 |
