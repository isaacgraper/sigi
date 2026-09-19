# ADR-0006 — Language split: English code and API envelope, Portuguese domain, pt-BR user text

- **Status:** Superseded by ADR-0013
- **Date:** 2026-08-20
- **Deciders:** Isaac Kleimann Graper
- **Related:** SPEC-0003, SPEC-0004, A01

> **Superseded on 2026-09-19 by ADR-0013.** The rule below chooses a
> language by asking whether a word is in the glossary. ADR-0013 asks who
> reads the string instead, which protects the whole database schema rather
> than only its glossary words, and frees exception classes and error codes
> that carry no domain noun. Read this file for the reasoning that led
> there; read ADR-0013 for the rule in force.

## Context

SIGI is built by an English-speaking team for Portuguese-speaking government
users, on top of a domain whose vocabulary — `ATA`, `empenho`, `saldo`,
`fornecedor` — is fixed by invariant 1 and must never be translated, anywhere it
appears. Three different audiences read three different parts of the same
response, and without an explicit rule the natural failure mode is to pick one
language and apply it uniformly, which is wrong for at least one of the three.

A developer reads code, logs and the API envelope's plumbing (`error`, `code`,
`fields`) — this should be English, matching the team. A servidor reads
`message` and every other string a screen shows — this must be pt-BR,
non-negotiably, per the product's users. Both of them, in both contexts, read
domain nouns — `saldo`, `ATA`, `processo_sei` — and those never change language,
because invariant 1 does not carve out an exception for "but this occurrence is
in an English sentence" or "but this field is in the envelope".

The concrete trap: `codigo` is not one word semantically. `erro.codigo` is
plumbing — a stable identifier the frontend switches on, structurally identical
to an HTTP status. `INSUMO.codigo` is the DOMS item code — a domain field that
SPEC-0003's acceptance criteria, the glossary and RF03 are built around. They
look identical in the previous convention and must not be treated identically.

## Options considered

| Option | Pros | Cons |
| --- | --- | --- |
| One language for the whole response | Simple to state | Wrong for at least one audience no matter which language is picked; either the developer reads Portuguese envelope keys or the servidor reads English prose |
| Translate `message` to English, keep field names Portuguese | Read literally from "let's use English for errors" without asking which layer | Puts the *only* string a real user reads in the wrong language, and does nothing for the field names a developer actually types against every day |
| English envelope/plumbing + English source, Portuguese domain vocabulary everywhere, pt-BR only in user-facing strings | Each of the three audiences gets the layer meant for them; matches invariant 1 exactly, which scopes to vocabulary, not to "the response" as a whole | A single JSON object mixes two languages (`"error"` beside `"valor_estimado"`) — looks inconsistent until the rule is known |

## Decision

Three layers, and the test for which one a given string belongs to:

1. **Source code** — identifiers, comments, docstrings, log messages: English.
   `def calcular_saldo(ata)`, not `def calculate_balance(minutes)` — the
   function name is English, the parameter is a domain noun and stays
   Portuguese.
2. **API envelope and plumbing**: English. `error`, `code`, `message`, `fields`,
   `items`, `page`, `size`, `sort`. These are structural, not domain — nothing
   here is in the glossary.
3. **Domain vocabulary**: Portuguese, unconditionally, wherever it appears —
   payload field names (`valor_total`, `data_emissao`, `processo_sei`), resource
   paths (`/notas-empenho/{id}/avancar`), error codes (`SALDO_INSUFICIENTE`),
   exception classes (`SaldoInsuficienteError`), database tables and columns.
   Invariant 1 already says this; this ADR does not change it, only makes the
   boundary against the envelope explicit.
4. **User-facing strings** — `message`, `fields` values, all UI copy: pt-BR,
   unconditionally.

The reviewer's test for any new string: *is this a domain term from the
glossary?* If yes, Portuguese, no matter what layer it sits in. If no and a
developer reads it, English. If no and a user reads it, pt-BR.

## Consequences

**Positive** — Each audience reads the layer meant for them: the servidor never
sees an English sentence, the developer never grep's for a Portuguese log line
or an envelope key spelled `mensagem`. The rule is a single test, not a table of
exceptions, so it extends to new endpoints without a fresh decision each time.

**Negative** — A single error response mixes languages by design —
`{"error": {"code": "SALDO_INSUFICIENTE", "message": "Saldo insuficiente..."}}`
— which reads as inconsistent to someone who has not seen this ADR. That
inconsistency is the price of keeping the domain-vocabulary mapping 1:1 with the
glossary instead of introducing a second, English name for the same concept.

**Follow-up**

- `docs/architecture/api-conventions.md` — envelope and pagination examples
  updated to English field names with pt-BR content.
- `CLAUDE.md` — convention recorded under Code conventions → Both.
- Any future spec's §5 error table keeps `Message (pt-BR, user-facing)` per
  `SPEC-TEMPLATE.md`; this ADR does not touch that column, only the JSON key it
  travels under.
