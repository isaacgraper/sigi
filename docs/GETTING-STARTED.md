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

Four things, in this order:

1. **Revoke the prototype JWT** published in RFC Appendix 9.1. It is a live token
   in a distributed document (OQ-17).
2. **Answer OQ-05** — can one NE cover multiple insumos? If real empenhos are
   multi-item, the data model changes at its core. This costs an e-mail now and
   a rewrite in week 12.
3. **Answer OQ-04** — what is an "área de competência"? Without it, RN07 cannot
   be implemented and the system cannot claim least-privilege access.
4. **Answer OQ-07** — is cancelling an NE administratively permitted?

## 3. First session with Claude Code

```
claude

> Read docs/README.md and docs/product/glossary.md, then review
> docs/specs/SPEC-0004-notas-de-empenho.md with /spec-review SPEC-0004
```

Then, once SPEC-0001 and SPEC-0004 are Approved:

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

- `.claude/settings.json` permissions assume `poetry` and `npm`; adjust to your tooling.
- The specs are `Draft` for a reason — they contain assumptions marked in
  `docs/open-questions.md` that only your stakeholder can confirm.
- If a rule in `CLAUDE.md` keeps getting in your way, change it deliberately
  rather than ignoring it. An instruction file people work around is worse than
  no instruction file, because it still costs tokens on every request.
