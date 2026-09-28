# SIGI — Design

The style authority for every SIGI screen (ADR-0014). A spec says what a screen
does; this file says how it looks and moves. Where this file and a spec
disagree, the spec wins. `docs/product/design-reference.md`, the Lovable
prototype's notes, is history and no longer decides anything.

Before building or reviewing a screen, read this file. For motion, also use the
`emil-design-eng` skill; its rules are summarised under [Motion](#motion).

---

## 1. Principles

1. **A work tool, not a portal.** Servidores spend the day in tables and forms.
   Density and speed beat decoration; the institutional look comes from colour,
   type and restraint, not from heroes, slogans or photographs.
2. **One meaning per colour.** Navy is SIGI and its actions. Green is success
   and health, amber is attention, red is error and destruction, slate is in
   progress. Never borrow a status colour for decoration.
3. **Text carries the meaning.** A status is always written; its colour only
   supports it. A control's purpose is always in its label or `aria-label`.
4. **Every state is designed.** Loading, empty, error and not found are screens
   in their own right, never a blank area or a framework default.
5. **pt-BR on screen, English in code** (ADR-0013). Glossary words stay
   Portuguese everywhere.

---

## 2. Tokens

Defined once in `frontend/app/globals.css` as CSS variables and exposed to
Tailwind through `@theme inline`. Components use the Tailwind names in the last
column and never hard-code a colour.

### Colour

| Token | OKLCH | Hex (approx.) | Tailwind | Use |
| --- | --- | --- | --- | --- |
| `--background` | `0.985 0.004 255` | `#f8fafd` | `bg-background` | Page background |
| `--card` | `1 0 0` | `#ffffff` | `bg-card` | Cards, tables, dialogs, header |
| `--foreground` | `0.24 0.03 262` | `#171f2e` | `text-foreground` | Body text |
| `--muted-foreground` | `0.50 0.025 262` | `#5c6472` | `text-muted-foreground` | Secondary text, captions |
| `--border` | `0.91 0.01 262` | `#dee1e8` | `border-border` | Hairlines, table rules |
| `--primary` | `0.33 0.08 262` | `#1e345e` | `bg-primary` | Navy: brand, primary buttons, links, focus ring |
| `--primary-hover` | `0.39 0.09 262` | `#294375` | `hover:bg-primary-hover` | Primary button hover |
| `--sidebar` | `0.26 0.065 262` | `#122343` | `bg-sidebar` | Sidebar background |
| `--sidebar-foreground` | `1 0 0` | `#ffffff` | `text-sidebar-foreground` | Active and hovered sidebar items |
| `--sidebar-muted` | `0.80 0.03 262` | `#b3bed2` | `text-sidebar-muted` | Idle sidebar items |
| `--sidebar-accent` | `0.33 0.07 262` | `#213459` | `bg-sidebar-accent` | Active and hovered sidebar item background (white on it 12.3:1) |
| `--success` | `0.50 0.12 152` | `#1a763f` | `text-success` | `ativo`, `vigente`, `aprovada`, completion |
| `--attention` | `0.52 0.12 70` | `#945a00` | `text-attention` | `bloqueado`, "a vencer", pending action |
| `--danger` | `0.53 0.2 27` | `#c51e21` | `text-danger` | Errors, destructive actions, `vencida` |
| `--neutral` | `0.50 0.03 262` | `#5a6475` | `text-neutral` | `pendente`, in progress, waiting |

Measured contrast (WCAG 2.1): foreground on background 15.8:1; white on primary
12.3:1; white on sidebar 15.6:1; idle sidebar items 8.4:1; muted text 5.8:1;
every status colour between 5.6:1 and 6.0:1 on white and at least 4.9:1 on
its own 10 % badge tint (amber was darkened from `0.55 0.13 70` because it
failed there at 4.4:1). Any new colour is checked
the same way before it is used, and the axe suite (AC-0010-44) guards the result.

### Type

The system sans-serif stack: no web font to download, and it matches the
operating system the servidor already reads all day. Monospace for codes, links,
Processo SEI, NE and NF numbers.

| Role | Classes |
| --- | --- |
| Page title (one per page, `h1`) | `text-2xl font-semibold tracking-tight` |
| Section and card title | `text-base font-semibold` |
| Body and table text | `text-sm` |
| Caption, metadata, table header | `text-xs` or `text-sm text-muted-foreground` |
| Figures in tables and stats | `tabular-nums` |
| Codes and identifiers | `font-mono text-xs` |

### Space, radius, depth

- Spacing follows Tailwind's 4 px scale. Page padding `p-4` on mobile, `p-6`
  from `sm`; `gap-6` between page sections, `gap-4` inside them.
- Content width is capped at `max-w-7xl`.
- Radius `0.5rem` (`rounded-md`) for controls, `rounded-lg` for cards and
  dialogs. Nothing fully rounded except avatars and status dots.
- Depth is a border first, `shadow-sm` on cards, `shadow-lg` only on dialogs and
  menus that float above the page.

---

## 3. Layout

### Shell

```
┌──────────────┬───────────────────────────────────────────┐
│  SIGI        │  Painel / Membros                 [● Ana] │  white header, sticky
│              ├───────────────────────────────────────────┤
│  ▣ Painel    │                                           │
│  ▣ Membros   │  <main>                                   │
│              │                                           │
│  (navy)      │                                           │
│              ├───────────────────────────────────────────┤
│  «           │  SIGI v0.x · Contato                      │  footer
└──────────────┴───────────────────────────────────────────┘
```

- **Sidebar**: navy, 240 px wide, collapsible to 64 px showing icons only, with
  the label as a tooltip and `aria-label`. The collapse choice is remembered per
  browser. Items are the modules the perfil may open, in a fixed order: Painel,
  then the business modules as their specs are approved, then Membros last.
  The active item has a white label and a lighter navy background, and carries
  `aria-current="page"`.
- **Below 1024 px** the sidebar is hidden; a menu button in the header opens it
  as a drawer from the left, which closes on navigation, on Escape and on the
  backdrop.
- **Header**: white, sticky, bottom border. Breadcrumb on the left, the user
  menu on the right (initial, name or e-mail, perfil; "Sair" inside).
- **Skip link**: "Ir para o conteúdo" is the first focusable element on every
  page, visible on focus, moving focus to `<main>` (eMAG).
- **Footer**: one line, muted: "SIGI", the version, and the support contact.

### Page template

Every authenticated page follows the same order:

1. Breadcrumb in the header, ending in the current page.
2. Page header: the `h1` title, one line of description in muted text, and the
   page's primary action on the right (stacked below on mobile).
3. Content in sections: cards or a table, `gap-6` apart.

The document title is "<Page> · SIGI".

### Signed-out pages

Login, invitation, reset and the institutional callback use a split frame: a
navy panel on the left (from `lg`) with "SIGI", one sentence and the login
illustration; the form on the right, `max-w-sm`. Below `lg` only the form shows.

### Status pages

Not found and error pages centre an illustration, a title, one sentence, the
actions and the gestor contact, `max-w-md`.

---

## 4. Components

Built on shadcn/ui primitives in `frontend/components/ui`, restyled with the
tokens above. Prefer extending one of these to adding a new one.

| Component | Rules |
| --- | --- |
| **Button** | Variants: `default` (navy), `outline`, `ghost`, `destructive`, `link`. One `default` button per view. Press feedback `scale(0.97)`. Label is a verb in pt-BR: "Convidar", "Salvar", not "OK". |
| **Input, Select, Label** | Label above the field, always visible, never a placeholder in its place. Error text below the field in `text-danger`, linked with `aria-describedby`, field marked `aria-invalid`. |
| **Form** | One column. Primary action at the end, right-aligned on desktop, full-width on mobile. A submitting form disables its button and changes the label ("Entrando...", "Enviando..."). |
| **Table** | White card, `text-sm`, header row in muted text on a light tint, rows separated by hairlines, row hover tint. Scrolls sideways inside its own frame, never the page. Pagination below, state in the URL. Row actions behind a "⋯" menu labelled "Ações para <name>". |
| **Badge** | Status only. Tint of the status colour at 10 %, text in the status colour, 1 px border at 30 %. Always a word. |
| **Card** | White, border, `shadow-sm`, `rounded-lg`. Title `text-base font-semibold`, optional muted description. |
| **Module tile** | Dashboard entry point: card with a line icon in navy, the module name and one line of description; the whole tile is the link. Hover raises the border to navy, never scales. |
| **Stat tile** | Number in `text-3xl font-semibold tabular-nums`, label above in muted text, optional change below. Only for figures the API provides. |
| **Dialog** | Centred, `max-w-xl` for forms, `max-w-md` for confirmations. Destructive confirmations use `AlertDialog` and name the consequence ("não pode ser desfeita"). |
| **Error notice** | Red-tinted box with the API's message, followed by the gestor contact when the servidor cannot fix it alone (AC-0010-57). |
| **Notice** | Success or information after an action, in a tinted box with `role="status"`. |
| **Toast** | Sonner, top right, for confirmations that need no reading ("Convite criado"). Never for errors a person must act on: those stay on the page. |
| **Icons** | `lucide-react`, 16 px in controls, 20 px in tiles and the sidebar, `aria-hidden` next to a label. |

---

## 5. Illustrations

From [unDraw](https://undraw.co), stored as static SVG in
`frontend/public/illustrations/` and shown with `alt=""` because they are
decorative. The accent colour is the brand navy `#1e345e`, except on the navy
login panel, where it is `--sidebar-muted` `#b3bed2` so the drawing stays
visible.

**Source.** undraw.co is not reachable from the build environment, so the files
were rendered once from [`react-undraw-illustrations`](https://www.npmjs.com/package/react-undraw-illustrations)
2.0.3, MIT licensed, which republishes unDraw's illustrations from when the
collection itself was MIT. The package is not a dependency. A newer file from
undraw.co may replace any of these under unDraw's current licence, which allows
commercial use without attribution and forbids only redistributing the
collection.

| Where | Illustration | File | Accent |
| --- | --- | --- | --- |
| Login panel | Secure data | `login.svg` | `#b3bed2` |
| Not found | Lost | `not-found.svg` | `#1e345e` |
| Error page | Maintenance | `error.svg` | `#1e345e` |
| Empty table or list | No data | `empty.svg` | `#1e345e` |

One illustration per screen, at most 240 px tall on status pages and 160 px in
empty states, never above the page title. Illustrations are never used as the
only carrier of a message.

**Photography.** Only on the login panel, only once licensed (for example the
Unsplash or Pexels licence), and only after its source and licence are recorded
here. None is licensed yet.

| Photograph | Source | Licence |
| --- | --- | --- |
| — | — | — |

---

## 6. States

| State | How it looks |
| --- | --- |
| **Loading a page** | A skeleton of the page's own layout (title bar, cards, table rows) in `bg-muted` blocks with a slow pulse, `role="status"` and "Carregando..." for screen readers. Never a blank page, never a centred spinner for a whole page. |
| **Loading an action** | The button disables and relabels; the rest of the page stays usable. |
| **Empty** | Inside the table or card: the empty illustration, one sentence ("Nenhum membro encontrado."), and the action that fills it when the perfil has one. |
| **Error** | The error notice, in place, without clearing what the person typed except passwords. |
| **Not found** | The not-found status page (AC-0010-55). |
| **Crash** | The error status page (AC-0010-56). |

Pages are split by route, so each page's code loads when it is opened, and each
authenticated route has a `loading.tsx` skeleton shown while its data arrives.

---

## 7. Motion

From the `emil-design-eng` skill. SIGI is a professional work tool: motion is
crisp, fast, and only where it explains something.

| Rule | Value |
| --- | --- |
| Should it animate? | Only occasional actions: dialogs, drawers, menus, toasts. Never navigation between pages, table rows, or anything keyboard-driven. |
| Easing | `--ease-out: cubic-bezier(0.23, 1, 0.32, 1)` for entering and exiting; `--ease-in-out: cubic-bezier(0.77, 0, 0.175, 1)` for on-screen movement. Never `ease-in`. |
| Duration | Button press 120 ms; menus and selects 150–200 ms; dialogs 200 ms; the mobile drawer 250 ms. Nothing over 300 ms. The desktop collapse changes the sidebar's width, so it snaps; only the labels fade, in 150 ms. |
| Properties | `transform` and `opacity` only. Never `transition: all`, never width or height. |
| Entrances | From `scale(0.97)` and `opacity: 0`, never from `scale(0)`. Menus scale from their trigger; dialogs from the centre. |
| Exits | Faster than entrances. |
| Hover | Colour and border only, behind `@media (hover: hover) and (pointer: fine)`. Tiles do not scale. |
| Reduced motion | Under `prefers-reduced-motion: reduce`, no movement: opacity fades only. |

---

## 8. Writing on screen

- pt-BR, sentence case, no full stop in buttons, titles or labels.
- Say what happened and what to do next. Errors that only a gestor can fix name
  the contact (AC-0010-57).
- Dates `dd/MM/yyyy` in `America/Sao_Paulo`; money `R$ 1.234,56`.
- Domain words as the glossary writes them: ATA, Nota de Empenho, NE, NF,
  saldo, insumo, perfil, gestor, servidor.

---

## 9. Changing this file

A change to a token, a component rule or the shell is a design decision: it goes
in a pull request of its own, with before and after screenshots, and updates
SPEC-0011 when it changes observable behaviour.
