# ADR-0013 — Language is chosen by who reads the string, not by the glossary

- **Status:** Accepted
- **Date:** 2026-09-19
- **Deciders:** Isaac Kleimann Graper
- **Supersedes:** ADR-0006
- **Related:** SPEC-0001, invariant 1, `docs/product/glossary.md`

## Context

ADR-0006 settled the language question with a single test: *is this word in the
glossary?* If yes, Portuguese, wherever it appears. If no, English for a
developer and pt-BR for a user. That test is easy to state and it is wrong at
the edges, in both directions.

It is wrong about the database. Under ADR-0006 the schema is Portuguese only
where it happens to carry glossary vocabulary, so `usuario` and `perfil` stay
while `tentativa_login`, `limite_taxa`, `bloqueado_ate`, `sessao_familia` and
`geracao` have no protection at all. Nothing in the glossary covers them, and a
strict reading of ADR-0006 would anglicise every one. That is the wrong outcome
for a reason ADR-0006 never considered: a DBA and a data analyst work in the
schema directly, they are Portuguese speakers, and they do not read the
application code that would explain a translated column to them.

It is wrong about exception classes for the mirror reason. ADR-0006 lists
`SaldoInsuficienteError` under domain vocabulary and concludes that exception
class names are Portuguese. But `CredenciaisInvalidas`, `UsuarioInativo`,
`RefreshInvalido`, `RotaIndisponivel` and `TentativasExcedidas` carry no glossary
word, exist only in Python, and are read only by developers. PR #19 renamed them
to English, and was correct to, which is how the gap surfaced.

The glossary test also cannot answer the questions that actually come up. It has
nothing to say about a config key, a log line, a branch name, a folder, a
migration helper function or a test fixture, because none of those is
vocabulary. Every one of them has a reader.

## Options considered

| Option | Pros | Cons |
| --- | --- | --- |
| Keep ADR-0006's glossary test | Already written, already cited | Silent on config keys, logs, folders, filenames and test names; anglicises two thirds of the schema, which no DBA asked for; forces `CredenciaisInvalidas` to stay Portuguese |
| Portuguese everywhere except third-party interfaces | One rule, no judgement calls | Puts the whole codebase in a language the team does not write, and gives the servidor nothing they did not already have |
| Choose by reader, with the glossary as a standing exception | Answers every case including the ones ADR-0006 cannot reach; matches what the schema and the code already are | The reader has to be identified, which is a judgement call for a handful of names on the API boundary |

## Decision

**Ask who reads the string.**

| Layer | Language | Reader |
| --- | --- | --- |
| Database schema: tables, columns, constraints, indexes, DDL identifiers, `historico_movimentacao.acao` values, `dados_anteriores` keys | Portuguese | A DBA, a data analyst, anyone querying the database directly |
| User-facing text: all UI copy, `message`, `fields` values, tooltips and hovers | pt-BR | The servidor using the platform |
| Everything else: folders, filenames, Python identifiers, comments, docstrings, log messages, JSON payload fields, error codes, route paths, config and environment keys, branch names, commit messages, pull request titles and bodies | English | A developer |

**Glossary vocabulary stays Portuguese wherever it appears, in every layer.**
Invariant 1 is unchanged and this ADR does not narrow it. `ATA`, `empenho`,
`saldo`, `insumo`, `fornecedor`, `vigencia`, `aditivo`, `reajuste`,
`processo_sei`, `perfil`, `usuario`, `gestor`, `servidor`, `auditor` and the
rest of `docs/product/glossary.md` are never translated, including inside an
otherwise English identifier.

**The tie-break for compounds.** A name built around a glossary noun keeps the
whole Portuguese expression. A name with no glossary noun becomes English. Never
translate a compound word by word.

```
SALDO_INSUFICIENTE            stays      built on saldo
USUARIO_INATIVO               stays      built on usuario
/notas-empenho/{id}/avancar   stays      built on nota de empenho
CREDENCIAIS_INVALIDAS         becomes    INVALID_CREDENTIALS
TENTATIVAS_EXCEDIDAS          becomes    ATTEMPTS_EXCEEDED
/convites/{token}/ativar      becomes    /invites/{token}/activate
```

The alternative, translating the non-glossary half of each compound, produces
`SALDO_INSUFFICIENT` and `/usuarios/{id}/block`. Those read as neither language
and help no one.

## Consequences

**Positive** — Every question has an answer, including the ones ADR-0006 was
silent on. The schema is protected as a whole rather than word by word, so no
migration follows from this decision and the DBA's world does not change. The
code on `dev` after PR #19 becomes compliant rather than an unexplained
deviation from a written rule.

**Negative** — The reader has to be identified, and for a handful of names on
the API boundary that is a judgement rather than a lookup. A single JSON object
still mixes languages by design, now along a different seam than ADR-0006 drew:
`{"error": {"code": "SALDO_INSUFICIENTE", "message": "Saldo insuficiente..."}}`
beside `{"password": "..."}`.

**The API surface on `dev` does not yet comply.** `schemas/auth.py` ships
`senha`, `expira_em` and `nome`, and nine error codes are Portuguese without a
glossary noun to justify it. This ADR is the decision; a follow-up branch
carries the rename together with the SPEC-0001 revision that documents it, so
the spec never describes a contract the code is not serving.

**Follow-up**

- `docs/architecture/api-conventions.md` — §Base, §Responses and §Pagination
  restated against this rule.
- `CLAUDE.md` — Code conventions → Both.
- ADR-0006 — status set to `Superseded by ADR-0013`, file retained.
- The API rename and the remaining `usuario_id` Python rename, with SPEC-0001
  moving in the same branch.
- The ten ADRs with Portuguese filename slugs are grandfathered. Renaming them
  would break every inbound link and no reader is better off; new ADRs use
  English slugs, starting with this one.
