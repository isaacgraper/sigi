# Coding Standards — Standard Operating Procedure

> How code is laid out in this repository: where a value lives, what a file
> holds, and in which order. This document is normative. `CLAUDE.md` states
> the architecture and the language rules; this file is the house style that
> sits under them.

A value a reader has to hunt for is a value that gets written twice. Every
rule below exists so that a page size, a threshold, a status label or an error
message has exactly one home, and that home is obvious from the feature's name.

**Status:** the frontend part applies to all frontend code: the refactor in
§6 is done and the ESLint rule in §5 guards it. The backend part is a draft,
applied in its own refactor.

## 1. What counts as a constant

A **constant** is any value fixed at build time that code reads:

- domain lists and maps: the statuses of an ATA, their labels, the moves each
  status allows, a perfil's label;
- presentation tied to a domain value: the tone of a status, the class set of
  an urgency level;
- numbers that encode a decision: page sizes, thresholds (`SOON_DAYS`), how many
  rows a block shows;
- structure: the sections and field order of a form, a table's columns;
- wiring: API route segments per action, storage keys, cookie names, which
  error code lands on which field;
- **labels and messages**: dialog titles and bodies, confirmation texts, error
  and success messages, field labels, empty-state sentences used in more than
  one place.

**Not** constants:

- a one-off sentence written in a page's JSX, read in context and used nowhere
  else ("As Atas de Registro de Preços, o que vence e o reajuste a pedir.");
- a value derived at run time from props or state (`const lastPage = ...`):
  that is a variable, `camelCase`, and lives where it is used;
- Tailwind classes written once on the element they style.

## 2. Where it lives (frontend)

By feature, with one file for what the whole application shares:

```
frontend/lib/
  constants.ts          # app-wide: navigation, cookie and storage keys, generic messages
  types.ts              # app-wide: Perfil, Me, Module, StatusTone
  format.ts             # pure helpers with no domain
  atas/
    constants.ts        # STATUS_LABEL, MOVES, SOON_DAYS, DUE_LIST_FIRST, FORM_SECTIONS…
    types.ts            # Ata, AtaDetail, Status, Situacao, DueRow…
    status.ts           # ataStatus(), urgency()      ← logic, one concern per file
    due.ts              # dueRows(), dueText()
  members/
    constants.ts        # MEMBERS_PAGE_SIZE, STATUS_LABEL, ACTION_CONFIRM…
    types.ts
  dashboard/
    constants.ts        # the four report sections
    types.ts
    filters.ts          # select(), search()
    sections.ts         # sectionFor()
frontend/components/<feature>/   # components only: import from lib/<feature>
frontend/app/                    # routes only: import from components and lib
```

Rules:

1. A **feature** is a domain area with its own screens: `atas`, `members`,
   `dashboard`, and each new module from `docs/product/user-map.md`. Its
   constants live in `lib/<feature>/constants.ts`; its types in
   `lib/<feature>/types.ts`; its logic in `lib/<feature>/<concern>.ts`.
2. A value used by two or more features, or by the shell, lives in
   `lib/constants.ts`.
3. **No constant is declared in a component, a page, a hook or a test helper
   file.** A component imports what it needs. This includes maps of copy, class
   sets keyed by state, and field orders.
4. **No constant is declared inside a function.** A literal table rebuilt on
   every render is a constant in disguise.
5. No barrel files (`index.ts` re-exporting a folder): imports name the file
   they come from, so a reader can follow them.

## 3. How it is written

- **Name:** `SCREAMING_SNAKE_CASE` for every constant; types and components in
  `PascalCase`; functions and variables in `camelCase`. Glossary words stay
  Portuguese and whole (`SITUACAO_LABEL`, not `SITUATION_LABEL`), per
  ADR-0013 and invariant 1.
- **Exhaustive maps** are `Record<Union, T>`, so adding a status without its
  label fails the type check.
- **Literal tables** end in `as const`, and a type is derived from them when
  it is needed elsewhere (`type Kind = keyof typeof KIND`).
- **Grouping:** within a `constants.ts`, constants are grouped by the screen
  or concern they serve, each group under a one-line comment.
- **Provenance:** a constant that mirrors a rule or records an assumption says
  where it comes from in its comment: `// Mirrors AC-0002-22`,
  `// Assumed, OQ-47`. A reader must be able to tell a decision from a guess.
- **Copy:** labels and messages are pt-BR (ADR-0013); everything else in the
  file is English.

## 4. Order inside a file

Every `.ts` and `.tsx` file follows the same order, so the eye knows where to
look:

1. `"use client"`, when needed.
2. Imports, grouped by the lint rule (packages, then `@/` paths, then relative).
3. Types and interfaces local to the file, when they are used nowhere else.
4. Exported functions and components, the main one first.
5. Private helpers below what uses them.

Nothing in `UPPER_CASE` appears between steps 2 and 4: it lives in a
`constants.ts` and is imported in step 2.

**Exceptions**, because the framework requires the name in the route file
itself: Next.js route exports (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`),
`metadata`, `dynamic`, `revalidate` and `runtime`. Fixtures inside a test file
may be local to that test.

## 5. Enforcement

| Rule | Enforced by | Fires at |
| --- | --- | --- |
| No `UPPER_CASE` constant outside a `constants.ts` (exceptions in §4) | ESLint `no-restricted-syntax` in `frontend/eslint.config.mjs` | `npm run lint` locally · PR (`frontend-ci`) |
| Exhaustive maps are `Record<Union, T>` | TypeScript, through the maps that use them | build · PR |
| No constant inside a function, constants grouped and commented | — **a reviewer, reading** | never, automatically |

The rule fires in `frontend-ci`, not at commit: pre-commit runs only the
backend hooks, and the frontend has no hook of its own yet. Run `npm run lint`
before pushing.

## 6. Frontend refactor (done)

Done after PR 60 and PR 63 merged: one atomic commit per feature, each building
and passing its tests, and the ESLint rule last, once nothing broke it. The
table records where each value went.

| Today | Moves to |
| --- | --- |
| `lib/atas.ts`: types | `lib/atas/types.ts` |
| `lib/atas.ts`: `STATUSES`, `SITUACOES`, `STATUS_LABEL`, `SITUACAO_LABEL`, `MOVES`, `MOVE`, `SOON_DAYS` | `lib/atas/constants.ts` |
| `lib/atas.ts`: `ataStatus`, `urgency` | `lib/atas/status.ts` |
| `lib/atas.ts`: `dueRows`, `dueText` | `lib/atas/due.ts` |
| `app/(app)/atas/atas.tsx`: `SIZE`, `ALL`, `COLUMNS` | `lib/atas/constants.ts` (`ATAS_PAGE_SIZE`, `FILTER_ALL`, `LIST_COLUMNS`) |
| `components/atas/ata-form.tsx`: `SECTIONS`, `FIELDS`, `ORDER`, `CODE_FIELD`, `EMPTY`; types `Key`, `FieldSpec`, `Values` | `lib/atas/constants.ts` (`FORM_SECTIONS`, `FORM_FIELDS`, `FORM_ORDER`, `FORM_CODE_FIELD`, `FORM_EMPTY`); `lib/atas/types.ts` (`FormKey`, `FormField`, `FormValues`) |
| `components/atas/record-dialogs.tsx`: `ADITIVO_ORDER`, `ADITIVO_CODES`, `REAJUSTE_ORDER`, `REAJUSTE_CODES` | `lib/atas/constants.ts` |
| `components/atas/upcoming.tsx`: `KIND`, `LOUDNESS`, `FIRST` | `lib/atas/constants.ts` (`DUE_KIND_LABEL`, `URGENCY_CLASSES`, `DUE_LIST_FIRST`) |
| `components/members/types.ts`: `STATUS_LABEL`, `STATUS_TONE` | `lib/members/constants.ts`; types to `lib/members/types.ts` |
| `components/members/member-actions.tsx`: `ENDPOINT`, `CONFIRM`, `LINK_DIALOG`; type `Action` | `lib/members/constants.ts` (`ACTION_ENDPOINT`, `ACTION_CONFIRM`, `LINK_DIALOG`); `lib/members/types.ts` (`MemberAction`) |
| `components/members/invite-dialog.tsx`: `INVITE_FIELDS` | `lib/members/constants.ts` |
| `app/(app)/members/members.tsx`: `SIZE` | `lib/members/constants.ts` (`MEMBERS_PAGE_SIZE`). Not one shared value: AC-0013-03 fixes the ATA list at 25 and no spec fixes the member list, which stays at 20 |
| `lib/dashboard.ts`: `ATENDIMENTO`, `CONSUMO`, `PROCESSOS`, `ITENS_EM_FALTA`, `SECTIONS` | `lib/dashboard/constants.ts`; types to `lib/dashboard/types.ts`; `select`, `search` to `lib/dashboard/filters.ts`; `sectionFor` to `lib/dashboard/sections.ts` |
| `lib/me.ts`: `PERFIL_LABEL`; types `Perfil`, `Me` · `lib/modules.ts`: type `Module` | `lib/constants.ts`; types to `lib/types.ts` |
| `lib/modules.ts`: `DASHBOARD`, `MODULES` | `lib/constants.ts` (`NAV_DASHBOARD`, `NAV_MODULES`) |
| `lib/errors.ts`: `GENERIC_FAILURE` · `components/error-notice.tsx`: `NEEDS_GESTOR` | `lib/constants.ts` (`GENERIC_FAILURE`, `NEEDS_GESTOR_CODES`) |
| `lib/flash.ts`: `KEY`, `NEXT` · `lib/session.ts`: `LOCK` · `lib/sidebar.ts`: `SIDEBAR_COOKIE` · `lib/return-path.ts`: `HOME` | `lib/constants.ts` (`FLASH_STORAGE_KEY`, `NEXT_STORAGE_KEY`, `REFRESH_LOCK_NAME`, `SIDEBAR_COOKIE`, `HOME_PATH`); `lib/sidebar.ts` deleted |
| `components/session-provider.tsx`: `SESSION_OVER` · `components/auth/token-password-form.tsx`: `MISMATCH` · `app/auth/callback/callback-handler.tsx`: `CANCELLED` | `lib/constants.ts` (`SESSION_OVER_CODES`, `PASSWORD_MISMATCH`, `OIDC_CANCELLED`) |
| `components/shell/footer.tsx`: `VERSION` · `components/illustration.tsx`: `FILES` · `components/ui/status.tsx`: `TONE` | `lib/constants.ts` (`APP_VERSION`, `ILLUSTRATIONS`, `STATUS_TONE_CLASSES`); `IllustrationName` and `StatusTone` to `lib/types.ts` |
| `lib/format.ts`: `DATE` (an `Intl` formatter) | stays: a formatter instance is not a value a reader looks up; renamed `dateFormatter` |
| `app/api/v1/[...path]/route.ts`: `GET`…`DELETE` | stay (§4 exception); `DROPPED` moves to `lib/constants.ts` (`PROXY_DROPPED_HEADERS`) |

Behaviour does not change: the full Vitest and Playwright suites must pass
unchanged after every commit, which is the proof that nothing moved but code.

## 7. Backend (draft, after the frontend)

The same principle, adapted to the layered backend (`api → services →
repositories → models`):

- **Configuration is not a constant.** A value an operator may tune without a
  deploy (alert windows, rate limits, token lifetimes) stays in
  `app/core/config.py` as a `Settings` field.
- **Fixed values** move out of the modules that use them into
  `app/constants/<domain>.py` (`atas.py`, `auth.py`, `members.py`), with
  app-wide ones in `app/constants/__init__.py`. Examples today:
  `services/atas.py`'s `MOVES` and `LOCKED_AFTER_DRAFT`, `core/processo_sei.py`'s
  `FORMAT`, the permission matrix.
- `SCREAMING_SNAKE_CASE`, typed with `Final` or as frozen mappings, with the
  same provenance comments as the frontend.
- **Enforced** by a ruff rule set or a small check in `scripts/`, chosen when
  the backend refactor is planned.
