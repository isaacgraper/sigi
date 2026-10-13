# Design references

Patterns the product owner collected as references for SIGI's screens. They
are **candidates, not rules**: `DESIGN.md` is the rulebook, and a pattern here
reaches it only through a design PR with before and after screenshots
(DESIGN.md §9). The original images are third-party work and are not kept in
the repository; each entry credits its author.

## 1. Profile, grouped into cards (Seva Kogaev, "Profile UX/UI Redesign")

**Before:** one long white column of label and value pairs under bold section
titles, separated only by spacing.

**After:**
- The page background is a light grey and each group is a white card with
  generous rounding, so groups separate without lines.
- Every row has a line icon inside a soft square tile on the left.
- The label is small and muted *above* the value; the value is the larger,
  darker text.
- A group of like items (Passport, Social Security, TIN) becomes a row of small
  cards, each with its icon, name and masked number, scrolling sideways.
- The header is centred: avatar with an edit affordance on it, name below.

**For SIGI:** "Dados da ATA" could use icon, muted label and value rows inside a
white card on the grey page, the way the ATA page already reads. Aditivos or
documents of an ATA could become a short row of cards when there are few.

## 2. Settings, sectioned (Abraham John, @ui.abraham, "Profile Settings Redesign")

**Before:** nine identical rows in one flat list, each an icon, a label and an
arrow.

**After:**
- The same rows split into labelled groups (Account, Preferences, Support),
  each an inset white card on a grey page, with hairlines between rows.
- The group label is small, muted, outside the card.
- A row that holds a setting shows its **current value** in muted text before
  the arrow ("Language English", "Theme Light"), so the screen answers without
  a tap.

**For SIGI:** any list of more than about five entries is grouped by meaning
with a small label above each group. A row that leads to a choice shows the
current choice inline. Candidates: the user menu, a future settings page, and
the ATA page's actions if they grow.

## 3. Status with a progress glyph (author not credited in the image)

A status chip whose **icon** carries the stage, so it reads without colour:

| State | Glyph | Tint |
| --- | --- | --- |
| Draft | Dashed empty circle | Grey |
| In progress | Half-filled circle | Orange |
| In review | Three-quarter circle | Blue |
| Completed | Filled circle with a check | Green |

The chip is a soft tint with no border and a large radius; the icon alone also
works as a compact form.

**For SIGI:** this conflicts with the current DESIGN.md §4 rule (status as text,
never a pill) only in the chip; the glyph itself is the useful idea. It fits a
**sequential flow** best: the NE's five steps (`demanda → validacao_saldo →
pre_empenho → envio_fornecedor → ne_emitida`, RN08) could show a circle that
fills by step, with the check at `ne_emitida`, next to the status word. If
adopted, it would be a glyph before the text, not a tinted chip, unless the
product owner revises §4.

## 4. Dialogs by intent (Material X dialogs)

Four intents, each with two variants:
- **Default** (information), **Positive** (success), **Error** (destructive or
  data loss) and **Action** (start something).
- **Variant A:** a header bar tinted by intent with the dialog's kind and a
  close button; a white body with a large icon in a circle beside the title and
  text; a footer separated by a hairline with "Secondary" outlined and the
  primary action filled in the intent colour.
- **Variant B:** the whole dialog tinted by intent, no icon, the title in the
  intent colour, and buttons named by their action ("Save" / "Discard",
  "Skip" / "Add New", "Got it") instead of "Primary" / "Secondary".

**For SIGI:**
- Buttons named by their action is already a DESIGN.md rule ("Convidar",
  "Salvar", not "OK"); variant B shows why.
- An intent colour on the confirm button already exists for destructive moves
  (Encerrar, Cancelar). A tinted header or an intent icon is a candidate for
  the destructive confirmations only, where the consequence matters most.
- Fully tinted dialogs would spend colour on every dialog; against §4's
  restraint, so not a candidate as the default.

## 5. Across all four: space and grouping

- A grey page with white grouped cards separates content better than lines or
  bold headings.
- Labels small and muted, values larger: the eye lands on the data.
- Fewer, larger touch targets with more vertical space per row.
- Group first, then decorate: every "after" here is mostly regrouping, and
  only a little new styling.
