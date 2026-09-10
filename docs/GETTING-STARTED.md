# Getting started with this scaffold

## 1. Drop it into your repo

```bash
# from your project root (github.com/isaacgraper/sigi)
cp -r sigi/docs .
cp -r sigi/.claude .
cp sigi/CLAUDE.md .
git add docs .claude CLAUDE.md && git commit -m "docs: spec-driven scaffold from RFC v1.6"
```

`.claude/` is committed on purpose: agents, commands and skills are team
configuration, not personal preference. Add `.claude/settings.local.json` to
`.gitignore` for individual overrides.

## 2. Before writing any code

*(Updated 2026-09-10. Three of the original four gates are closed; keeping the
list as written would have sent you to ask questions the data already answered.)*

**Still open, and the only one left here:**

1. **Revoke the prototype JWT** published in RFC Appendix 9.1. It is a live token
   in a distributed document (OQ-17). Nothing in the build depends on it, which
   is exactly why it keeps getting deferred.

**Closed, and how:**

2. ~~OQ-05 — can one NE cover multiple insumos?~~ **Yes, measured: 27,8% of 482
   real empenhos, the largest covering 37.** ADR-0007 splits `NOTA_EMPENHO` into
   header and `ITEM_NOTA_EMPENHO`. The risk this gate existed to catch landed,
   and was absorbed before a line of code existed.
3. ~~OQ-04 — what is an "área de competência"?~~ **Two axes the data does carry:
   unidade and grupo de materiais.** Adopted in SPEC-0003, not SPEC-0001 — RN07
   restricts which *insumos* a servidor sees, so it needs a scoped resource to
   be observable.
4. ~~OQ-07 — is cancelling an NE administratively permitted?~~ `Assumed` and
   implemented as AC-0004-16. If the entity says otherwise, that is the
   criterion to revisit.

**Added since:** OQ-09 and OQ-10 are `Assumed` under ADR-0010 — institutional
OIDC as primary, local credentials as a switchable contingency, Gov.br cut, CPF
not collected. OQ-09 leaves one ask for the entity's TI: tenant ID, client ID
and redirect URI. It blocks the first real login, not the build.

## 3. First session with Claude Code

```
claude

> Read docs/README.md and docs/product/glossary.md, then review
> docs/specs/SPEC-0004-notas-de-empenho.md with /spec-review SPEC-0004
```

`SPEC-0001` reached `Approved` at v0.3 on 2026-09-10 and is the spec being
implemented. `SPEC-0004` is still `Draft`. Once a spec is `Approved`:

```
> /plan SPEC-0001
> /implement SPEC-0001
> /trace
```

## 4. The commands

| Command | Purpose |
| --- | --- |
| `/spec-new <capability>` | Draft a new spec from the RFC and existing docs |
| `/spec-review SPEC-XXXX` | Completeness gate before approval |
| `/plan SPEC-XXXX` | Migration, modules, endpoints, test map |
| `/implement SPEC-XXXX [AC-...]` | Build it, in the right order |
| `/trace [SPEC-XXXX]` | Requirement → AC → test audit |
| `/adr-new <decision>` | Record a decision with real alternatives |

## 5. The agents

`spec-author`, `domain-modeler`, `backend-implementer`, `frontend-implementer`,
`test-author`, `security-reviewer`, `traceability-auditor`.

Claude invokes them automatically when their description matches, or you can
name one: `use the security-reviewer to check this diff`.

## 6. Tuning it

These files are a starting position, not scripture. In particular:

- `.claude/settings.json` permissions assume `uv` and `npm`; adjust to your tooling.
- The specs are `Draft` for a reason — they contain assumptions marked in
  `docs/open-questions.md` that only your stakeholder can confirm.
- If a rule in `CLAUDE.md` keeps getting in your way, change it deliberately
  rather than ignoring it. An instruction file people work around is worse than
  no instruction file, because it still costs tokens on every request.
