# ADR-0014 — Visual identity and application shell

- **Status:** Accepted (2026-09-28)
- **Date:** 2026-09-28
- **Deciders:** Isaac Kleimmann Graper
- **Related:** SPEC-0010, SPEC-0011, `DESIGN.md`, RNF06, RNF14

## Context

SPEC-0010 shipped the first screens with the style of the Lovable prototype:
a dark green primary colour and a thin shell built for two pages. Every module
still to come (ATAs, insumos, NEs, NFs, saldo, reports) will copy whatever the
shell looks like when it starts, so the look has to be settled once, before the
business screens, and not rediscovered per spec.

Three forces make this a decision rather than a default:

- **The reference is a public portal, the product is a work tool.** The product
  owner's references are institutional government portals: navy, a header with
  an emblem, icon tiles, stat tiles, a navy footer. Those pages are landing pages
  for citizens. SIGI is used all day by servidores in tables and forms, so the
  visual language carries over and the landing-page layout (heroes, slogans,
  stock photos) does not.
- **Green meant two things.** `design-reference.md` reserves green for
  completion and health, and the same green was the primary action colour, so a
  "Convidar" button and an "Ativo" badge shared one colour and one meaning.
- **Public-sector accessibility.** RNF14 asks for WCAG 2.1 AA, and Brazilian
  public-sector sites follow eMAG, which expects a skip link to the content.

## Options considered

| Option | Pros | Cons |
| --- | --- | --- |
| Keep the green identity from the prototype | No rework | Primary and success share a colour, contradicting the reference's own rule |
| Navy identity, top navigation (as in the references) | Closest to the references | A horizontal bar fits about seven modules; SIGI has seven planned before any growth, and a work tool's navigation is used constantly |
| **Navy identity, navy sidebar, white header** | Institutional look of the references; room for every module; collapses to icons; standard for work tools | The references' top bar becomes a sidebar, so the resemblance is in colour and components rather than layout |

## Decision

1. **Navy is the identity colour.** Brand, primary actions, focus rings and the
   sidebar are navy. Green is reserved for success and health (`ativo`,
   `vigente`, `aprovada`), amber for attention, red for errors and destructive
   actions, slate for in-progress. Exact values live in `DESIGN.md`, checked for
   AA contrast.
2. **The shell is a navy sidebar and a white header.** The sidebar lists the
   modules the signed-in perfil may open, collapses to icons on desktop, and
   becomes a drawer below 1024 px. The header carries the breadcrumb and the
   user menu. A skip link to the content comes first on every page.
3. **The brand is the word "SIGI" with a simple icon.** No state coat of arms
   or entity emblem: none has been licensed for this use.
4. **Illustrations come from unDraw, exported in the brand navy.** They mark the
   login panel, the not-found page, the error page and empty states. They are
   decorative, served as static files, and hidden from assistive technology.
   unDraw's licence allows commercial use without attribution; it forbids only
   redistributing the collection itself.
5. **No photography inside the application.** A photograph may appear on the
   login panel only, only once it is licensed for this use (for example under
   the Unsplash or Pexels licence), with its source recorded in `DESIGN.md`.
   Until then the panel uses an illustration.
6. **Light theme only.** A dark theme is not in scope until a servidor asks for
   one.
7. **Motion follows Emil Kowalski's design engineering guidance**, vendored as
   the `emil-design-eng` skill: short, `ease-out`, transform and opacity only,
   none on keyboard-driven actions, reduced under `prefers-reduced-motion`.
8. **`DESIGN.md` at the repository root is the style authority.** It supersedes
   `docs/product/design-reference.md`, which stays as history. Where they
   disagree, `DESIGN.md` wins; where `DESIGN.md` and a spec disagree, the spec
   wins, as ADR-0009 ranks them.

## Consequences

**Positive** — every future screen starts from one shell and one set of
patterns, so feature specs describe behaviour and inherit the look. Green
regains a single meaning. The sidebar has room for every planned module. The
illustrations give the error and empty screens warmth without photographs that
nobody has licensed.

**Negative** — the screens already shipped in SPEC-0010 are restyled, and their
screenshots and end-to-end specs change where they touch the old colours or the
old shell. The sidebar resembles the references less than a top bar would. unDraw
illustrations are recognisable as unDraw to anyone who has seen them elsewhere.

**Follow-up**

- SPEC-0011 specifies the shell and page patterns as testable criteria.
- `DESIGN.md` records tokens, components, illustrations, states and motion.
- `CLAUDE.md` points every session at `DESIGN.md` for frontend work.
- `docs/product/design-reference.md` gains a banner: superseded by `DESIGN.md`.
- When a building photograph is licensed, record its source and licence in
  `DESIGN.md` before it is committed.
