---
id: SPEC-0011
title: Estrutura da interface
status: Approved
version: 1.0
owner: Isaac Kleimann Graper
satisfies: [RNF06, RNF14]
depends_on: [SPEC-0010]
milestone: M2
---

# SPEC-0011 — Estrutura da interface

## 1. Purpose

Every business screen still to come (ATAs, insumos, NEs, NFs, saldo, reports)
will copy whatever the shell looks like when it starts. This spec settles the
frame once, before those screens exist: the sidebar and header every
authenticated page sits in, the page template, the dashboard as a set of entry
points, and how a page looks while it loads, when it is empty and when it
fails. ADR-0014 records why; `DESIGN.md` records how it looks. This spec is what
can be tested.

## 2. Scope

**In scope** — the application shell (sidebar, header, breadcrumb, user menu,
skip link, footer); the drawer below 1024 px; the page template; the dashboard's
module tiles; the signed-out frame; illustrations on the login, not-found,
error and empty states; loading skeletons; loading each page's code only when
it is opened; reduced motion; moving the SPEC-0010 screens into this shell.

**Out of scope**

- Any business screen. SPEC-0002 to SPEC-0009 are `Draft`; each adds its own
  sidebar entry and tile when it is approved, following this spec.
- Stat tiles with figures. The API serves no aggregate yet, and a tile with an
  invented number is worse than none (`DESIGN.md` §4).
- A photograph on the login panel. None is licensed (OQ-39).
- A dark theme (ADR-0014, decision 6).
- Any change to what SPEC-0010's screens do. Only where they sit and how they
  look changes (§4.7).

## 3. Domain model touched

None. This spec reads nothing the API does not already serve to SPEC-0010, and
owns no invariant beyond SPEC-0010's C1 to C4, which it keeps. One more, about
the client:

- **C5** — the shell never decides what a perfil may do. It shows the entries
  SPEC-0010 §6 shows, and the API still refuses what the perfil may not do
  (invariant 8). A module absent from the sidebar is not thereby protected.

## 4. Behaviour

Every criterion below applies at 1024 px and wider unless it names a narrower
width.

### 4.1 The shell

**AC-0011-01** — The sidebar lists the perfil's modules in a fixed order
```gherkin
Given a signed-in usuario of any perfil
When  any authenticated page is shown
Then  a navigation landmark lists "Painel" first, then "Membros" for a gestor or an auditor
And   the entry for the current page is marked as the current page for assistive technology
```

This moves AC-0010-27's navigation into the sidebar without changing its
entries. Business modules take their place between "Painel" and "Membros" as
their specs are approved.

**AC-0011-02** — The sidebar collapses to icons without losing its names
```gherkin
Given a signed-in usuario with the sidebar expanded
When  they activate the control that collapses it
Then  each entry shows only its icon
And   each entry keeps its name as its accessible name, and shows it on hover or focus
```

**AC-0011-03** — The collapse is remembered
```gherkin
Given a usuario who collapsed the sidebar
When  they reload the page, or open another authenticated page in the same browser
Then  the sidebar is still collapsed
```

The choice is a display preference kept in the browser. It carries no token or
personal data, so C1 does not reach it.

**AC-0011-04** — Below 1024 px the sidebar becomes a drawer
```gherkin
Given a signed-in usuario at 360 or 768 px
When  any authenticated page is shown
Then  no sidebar is visible and the header shows a menu button named "Abrir menu"
And   activating that button shows the same entries as AC-0011-01 in a drawer
```

**AC-0011-05** — The drawer closes where a person expects
```gherkin
Given the drawer is open
When  the usuario follows an entry, presses Escape or activates the backdrop
Then  the drawer closes
And   after Escape or the backdrop, focus returns to the menu button
```

**AC-0011-06** — Focus stays in the open drawer
```gherkin
Given the drawer is open
When  the usuario presses Tab or Shift+Tab repeatedly
Then  focus moves only among the drawer's controls
```

**AC-0011-07** — The header shows where the usuario is
```gherkin
Given a signed-in usuario on any authenticated page
When  the page is shown
Then  the header holds a breadcrumb that starts at "Painel" and ends at the current page
And   its last item is marked as the current page and is not a link
```

On `/dashboard` the breadcrumb is the single item "Painel".

**AC-0011-08** — The user menu names who is signed in
```gherkin
Given a signed-in usuario
When  they open the user menu in the header
Then  it shows their name when the API returns one and their e-mail otherwise, and their perfil
And   it offers "Sair", which ends the session as AC-0010-14 describes
```

**AC-0011-09** — A skip link comes first
```gherkin
Given any page, signed in or not
When  the usuario presses Tab once after it loads
Then  a link "Ir para o conteúdo" is focused and visible
And   activating it moves focus to the page's main content
```

**AC-0011-10** — The footer names the version and the contact
```gherkin
Given a signed-in usuario on any authenticated page
When  the page is shown
Then  the footer shows "SIGI", the version the frontend was built from, and the gestor contact as AC-0010-57 words it
```

### 4.2 The page template

**AC-0011-11** — Every page has one title, and the tab says it
```gherkin
Given any authenticated page
When  it is shown
Then  it has exactly one level-one heading
And   the document title is that heading followed by " · SIGI"
```

**AC-0011-12** — The page's primary action sits with its title
```gherkin
Given an authenticated page that has a primary action, such as "Convidar membro" on /members
When  it is shown
Then  that action is inside the page header that holds the level-one heading
```

### 4.3 The dashboard

**AC-0011-13** — The dashboard offers one tile per module
```gherkin
Given a signed-in usuario on /dashboard
When  the page is shown
Then  it shows one tile for each sidebar entry except "Painel", with the module's name and one line of description
And   each whole tile is a single link to that module
```

AC-0010-28 still holds: the dashboard also states who is signed in. Today a
gestor or an auditor sees one tile, "Membros", and a servidor sees none.

**AC-0011-14** — A perfil with no module is told so
```gherkin
Given a signed-in servidor on /dashboard, while no business module is approved
When  the page is shown
Then  in place of tiles it says "Os módulos do SIGI aparecerão aqui conforme forem liberados."
```

### 4.4 Signed-out pages and status pages

**AC-0011-15** — The signed-out frame shows the brand beside the form
```gherkin
Given /login, /invite, /reset-password or /auth/callback
When  it is shown at 1024 px or wider
Then  a brand panel with "SIGI", one sentence and the login illustration sits beside the form
And   at 360 and 768 px only the form is shown
```

**AC-0011-16** — The status pages carry their illustration
```gherkin
Given the not-found page of AC-0010-55 or the error page of AC-0010-56
When  it is shown
Then  it shows its own illustration above its title, sentence, actions and gestor contact
```

**AC-0011-17** — Illustrations are decoration only
```gherkin
Given any page that shows an illustration
When  it is read by assistive technology
Then  the illustration is skipped, having an empty text alternative
And   everything it stands beside is also stated in text on the page
```

### 4.5 Loading and empty states

**AC-0011-18** — A loading page shows its shape, not a blank
```gherkin
Given a signed-in usuario opening an authenticated page whose data has not arrived
When  the page is waiting
Then  the shell is shown with a placeholder of the page's layout in place of its content
And   a status message "Carregando..." is announced to assistive technology
```

**AC-0011-19** — An empty table says so
```gherkin
Given a table on any authenticated page with no rows to show
When  it is shown
Then  in place of rows it shows the empty illustration and one sentence saying what is missing
And   it offers the action that would add a row, when the usuario's perfil has one
```

**AC-0011-20** — A page's code loads when the page is opened
```gherkin
Given a visitor opening /login
When  the page has loaded
Then  no code belonging only to /members or /dashboard has been requested
```

### 4.6 Motion

**AC-0011-21** — Reduced motion removes movement
```gherkin
Given a browser that asks for reduced motion
When  a dialog, the drawer or a menu opens or closes
Then  nothing moves or changes size, and at most its opacity changes
```

**AC-0011-22** — Navigation does not animate
```gherkin
Given a signed-in usuario
When  they follow a sidebar entry or a breadcrumb link
Then  the new page is shown without a transition between the two pages
```

### 4.7 Moving SPEC-0010 into the shell

**AC-0011-23** — The SPEC-0010 screens keep their behaviour
```gherkin
Given the screens SPEC-0010 specifies, now inside this spec's shell and frames
When  every SPEC-0010 criterion is checked again
Then  each still holds, with only its selectors changed where a test named the old shell
```

**AC-0011-24** — The shell holds at every width and state (RNF06, RNF14)
```gherkin
Given each authenticated page with the sidebar expanded, collapsed, and at 360 px with the drawer open
When  it is checked as AC-0010-43 and AC-0010-44 describe
Then  both criteria hold
```

## 5. Errors and edge cases

| Condition | What the servidor sees |
| --- | --- |
| The browser refuses to store the collapse choice | The sidebar starts expanded on every page; nothing fails |
| A page's code fails to load | The error page of AC-0010-56 |
| A module's tile is followed and the API refuses the perfil | That page's refusal message (C3); the tile is cosmetic (C5) |

No new API error. Every message remains the API's (C3) or SPEC-0010 §5's.

## 6. Permissions

The shell shows what SPEC-0010 §6 shows, in new places:

| Screen element | gestor | servidor | auditor |
| --- | --- | --- | --- |
| "Painel" in the sidebar | ✅ | ✅ | ✅ |
| "Membros" in the sidebar and its tile | ✅ | ❌ | ✅ |
| "Convidar membro" in the page header | ✅ | ❌ | ❌ |
| User menu, "Sair" | ✅ | ✅ | ✅ |

## 7. Pages

No new page. Every SPEC-0010 page moves into a frame:

| Page | Frame | AC |
| --- | --- | --- |
| `/dashboard`, `/members` | Shell | 01–14, 18, 19, 22, 24 |
| `/login`, `/invite`, `/reset-password`, `/auth/callback` | Signed-out frame | 09, 15, 17, 20 |
| not found, error | Status page | 16, 17 |

## 8. Audit events

None. No screen in this spec writes anything.

## 9. Design

`DESIGN.md` is the style authority (ADR-0014): tokens, the shell's measurements,
components, the illustrations and their files, states and motion. Where it and
this spec disagree, this spec wins and `DESIGN.md` is corrected. SPEC-0010 §9 is
superseded by it.

The libraries that implement this are named in the implementation plan, added
by `/plan` after approval.

## 10. Open questions

- **OQ-39** — which photograph, if any, replaces the login illustration, and
  under what licence. Blocks nothing: the illustration is the default.

## 11. Implementation plan

### Migration

None. No backend change.

### New dependencies

None. The drawer is the dialog primitive already installed, and the collapsed
sidebar's names are a CSS tooltip, so no tooltip package is added. The
illustrations are static files (below), not a package.

### Font

Inter replaces the system stack (product owner, 2026-09-28). One variable
woff2, Latin subset, committed to `frontend/app/fonts/` with its OFL licence and
loaded with `next/font/local`; no package is installed and nothing is fetched
at build or run time.

### Illustrations

undraw.co is not reachable from the build environment. The four files come from
`react-undraw-illustrations` 2.0.3 on npm, MIT licensed, which republishes
unDraw's illustrations from when the collection itself was MIT. The package is
not installed: each component was rendered once to a static SVG, with the
accent colour set, and committed to `frontend/public/illustrations/`. The source
and licence are recorded in `DESIGN.md` §5.

| File | Illustration | Accent |
| --- | --- | --- |
| `login.svg` | Secure data | `#b3bed2`, because it sits on the navy panel |
| `not-found.svg` | Lost | `#1e345e` |
| `error.svg` | Maintenance | `#1e345e` |
| `empty.svg` | No data | `#1e345e` |

### Modules

| Module | Change | AC |
| --- | --- | --- |
| `app/globals.css` | Navy tokens from `DESIGN.md` §2, sidebar and status tokens, easing variables, the dialog, menu and drawer keyframes, and their reduced-motion variants | 21 |
| `lib/modules.ts` | One list of modules (path, name, description, icon, who sees it), read by the sidebar, the breadcrumb and the dashboard, so the three cannot disagree | 01, 07, 13 |
| `components/shell/sidebar.tsx` | Navy sidebar, collapse control, CSS tooltip when collapsed | 01–03 |
| `components/shell/mobile-nav.tsx` | Menu button and the drawer, built on the dialog primitive, which traps focus, closes on Escape and the backdrop, and returns focus to its trigger | 04–06 |
| `components/shell/breadcrumb.tsx`, `user-menu.tsx`, `footer.tsx` | Header and footer parts | 07, 08, 10 |
| `components/app-shell.tsx` | Assembles the above; `<main id="content">` | 01–10 |
| `components/skip-link.tsx` | First element of `<body>` in the root layout; focuses the element with id `content` | 09 |
| `components/page-header.tsx` | `h1`, description and primary action; every authenticated page uses it | 11, 12 |
| `components/illustration.tsx`, `empty-state.tsx` | The illustration with `alt=""`; the empty table row | 16, 17, 19 |
| `components/skeleton.tsx`, `app/(app)/*/loading.tsx` | Page-shaped placeholders with `role="status"` | 18 |
| `components/session-provider.tsx` | While the session is restored, render the shell's frame with a skeleton instead of a bare "Carregando..." | 18 |
| `app/(app)/dashboard`, `app/(app)/members` | `page.tsx` becomes a server component that exports the page's title and renders the existing client component, so the document title comes from the router's metadata and not from an effect | 11 |
| `app/layout.tsx` | Title template `%s · SIGI`; the skip link | 09, 11 |
| `components/auth/auth-layout.tsx`, `components/status-page.tsx` | Illustration in the navy panel and on the status pages; `<main id="content">` | 15–17 |
| `next.config.ts` | Exposes `package.json`'s version at build time for the footer | 10 |

**The collapse preference is a cookie, not `localStorage`.** The authenticated
layout is a server component, so it reads the cookie and renders the sidebar
in the right state on the first paint. `localStorage` is only readable after
hydration, so a collapsed sidebar would flash open on every page load. The
cookie holds `collapsed` or nothing, carries no token and is not httpOnly
because the page writes it (C1 is about credentials).

### Tests

One Playwright file, `e2e/interface.spec.ts`, named after the criteria.

| AC | How |
| --- | --- |
| 01 | Sidebar links in order per perfil; `aria-current` on the current one |
| 02 | Collapse; link text hidden, accessible name kept, tooltip visible on hover |
| 03 | Collapse, reload, still collapsed |
| 04–06 | At 360 px: no sidebar, "Abrir menu" opens the drawer; Escape and the backdrop close it and focus returns; following a link closes it; Tab cycles inside |
| 07 | Breadcrumb items on `/dashboard` and `/members`; the last is not a link |
| 08 | User menu shows identity and perfil; "Sair" ends at `/login` |
| 09 | First Tab on `/login` and `/dashboard` focuses the skip link; Enter focuses `#content` |
| 10 | Footer text contains "SIGI", the version and the contact |
| 11 | One `h1`; `document.title` is the `h1` followed by " · SIGI" |
| 12 | "Convidar membro" is inside `[data-testid=page-header]` |
| 13, 14 | Tiles for a gestor; the message for a servidor |
| 15 | Panel with illustration at 1440 px, hidden at 360 px |
| 16, 17 | Status pages show their illustration; every illustration has `alt=""` |
| 18 | The members request is held with `page.route`; the skeleton's status is announced inside the shell |
| 19 | The members request answers an empty page; the empty illustration, the sentence and the invite action show |
| 20 | On `/login`, no loaded script contains "Convidar membro"; on `/members`, one does (the control) |
| 21 | Under `reducedMotion: "reduce"`, open a dialog, the drawer and the user menu; every running animation's keyframes touch only `opacity` |
| 22 | After following a sidebar link, no animation is running on `main` |
| 23 | The whole SPEC-0010 suite passes; `shell.spec.ts` keeps its assertions |
| 24 | `responsive.spec.ts` and `accessibility.spec.ts` extended to the collapsed sidebar and the open drawer |

### Sequence

1. Illustrations and tokens.
2. The shell parts and the skip link.
3. Page header, titles, dashboard tiles.
4. Signed-out frame and status pages.
5. Skeletons and the empty state.
6. Motion.
7. Tests, and the SPEC-0010 suite on the new shell.

### Risks

- A test in the SPEC-0010 suite that relied on the old shell's markup changes
  its selector, never its assertion (AC-0011-23).
- The illustrations are a 2019 snapshot of unDraw. A newer one, fetched from
  undraw.co by someone who can reach it, replaces a file without touching code.

## 12. Changelog

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-09-28 | Initial draft from ADR-0014 and the product owner's references: navy sidebar shell, page template, dashboard tiles, signed-out frame, unDraw illustrations, loading and empty states, reduced motion. |
| 1.0 | 2026-09-28 | Approved by the product owner after #46 merged. No criterion changed. |
| 1.0 | 2026-09-28 | §11 implementation plan added. |
| 1.0 | 2026-09-28 | §11: Inter bundled as the interface font. No criterion changed. |
