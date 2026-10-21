# User Map

Every screen SIGI has or will have, who reaches it, and what each perfil may do
there. Read it before building a screen; update it in the same PR that adds,
moves or changes one.

The API decides what a perfil may do (invariant 8). This map records what the
screens show, which must match it.

## Perfis

| Perfil | Who | In short |
| --- | --- | --- |
| `gestor` | Manages the unit's supply cycle and its members | Reads everything, writes everything |
| `servidor` | Works the cycle day to day | Reads ATAs; registers insumos and NFs and advances NE steps (glossary), never reverses; sees only the insumos of its unidade and grupo (RN07) |
| `auditor` | Oversees, never operates | Reads everything, writes nothing |

## Screens

`✓` sees it · `W` sees it and writes · `—` not shown, and the API refuses it.

Every path through a screen, its fields, validation and screenshots, is in
[`user-flows/`](user-flows/): [ATAs](user-flows/atas.md).

### Public, no session

| Route | Screen | Spec | Status |
| --- | --- | --- | --- |
| `/login` | Entrar: e-mail and password, or institutional login | SPEC-0010 §4.1 | Implemented |
| `/auth/callback` | Completing institutional login | SPEC-0010 §4.2 | Implemented |
| `/invite?token=` | Activating an invitation | SPEC-0010 §4.4 | Implemented |
| `/reset-password?token=` | Choosing a new password | SPEC-0010 §4.5 | Implemented |
| any unknown path, any failure | Not found and error pages, with the gestor contact | SPEC-0010 §4.12 | Implemented |

### Inside the shell, signed in

| Route | Screen | Sidebar | gestor | servidor | auditor | Spec | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `/dashboard` | Painel: the CAME report, four tabs | Painel (1st) | ✓ | ✓ | ✓ | SPEC-0012 | Approved, built |
| `/atas` | ATAs: vencimentos e reajustes, list | ATAs (2nd) | W | ✓ | ✓ | SPEC-0013 | Approved, built |
| `/atas/{id}` | One ATA: aditivos, reajustes, moves; its items (SPEC-0014 §4.7, Draft) | under ATAs | W | ✓, items of its grupos | ✓ | SPEC-0013, SPEC-0014 | Approved, built; items Draft |
| `/atas/nova` | Nova ATA: the registration, in sections | under ATAs | W | — | — | SPEC-0013 | Approved, built |
| `/atas/{id}/editar` | Editar ATA: the edit, in sections | under ATAs | W | — | — | SPEC-0013 | Approved, built |
| `/atas/{id}/itens/importar` | Importar itens: an ATA's items file, checked first | under ATAs | W | — | — | SPEC-0014 §4.6 | Draft |
| `/insumos` | Insumos: the catalogue, searched and filtered | Insumos (3rd) | W | W, its grupos | ✓ | SPEC-0014 §4.2 | Draft |
| `/insumos/{id}` | One insumo: its ATAs, SKU, discontinue, substitute, reactivate | under Insumos | W | ✓, its grupos | ✓ | SPEC-0014 §4.4 | Draft |
| `/insumos/novo` | Novo insumo | under Insumos | W | W, its grupos | — | SPEC-0014 §4.3 | Draft |
| `/insumos/{id}/editar` | Editar insumo | under Insumos | W | W, its grupos | — | SPEC-0014 §4.3 | Draft |
| `/insumos/grupos` | Grupos de materiais: the tree, create, rename | under Insumos | W | ✓, its grupos | ✓ | SPEC-0014 §4.5 | Draft |
| `/insumos/importar` | Importar catálogo: the file, checked first | under Insumos | W | — | — | SPEC-0014 §4.6 | Draft |
| `/members` | Membros: invite, block, unblock, reset, deactivate | Membros (last) | W | — | ✓ | SPEC-0010 §4.7–4.8, SPEC-0014 §4.8 | Implemented; a servidor's grupos Draft |

### Planned, with no screen spec yet

Each needs its own screen spec, as SPEC-0013 is for SPEC-0002, before it is built.
The sidebar slot is where it goes between ATAs and Membros.

| Area | Backend spec | Likely route | Sidebar slot |
| --- | --- | --- | --- |
| Notas de Empenho | SPEC-0004 | `/notas-de-empenho` | after Insumos |
| Notas Fiscais | SPEC-0005 | `/notas-fiscais` | after Notas de Empenho |
| Saldo por ATA | SPEC-0006 | inside `/atas/{id}` | none, a block of the ATA page |
| Histórico | SPEC-0007 | `/historico` | before Membros |
| Notificações | SPEC-0008 | the header bell | none |
| Relatórios | SPEC-0009 | `/relatorios` | before Membros |

## Adding or changing a screen

1. **Spec.** A screen spec with its ACs, approved, and its row in this map.
2. **Navigation.** A top-level screen is a `Module` in `NAV_MODULES`
   (`frontend/lib/constants.ts`), in the sidebar order above, with `visibleTo` matching the perfil columns.
   The sidebar, the mobile menu and the breadcrumb all read that list, so
   nothing else needs to change. A child route (`/atas/{id}`) is not a module;
   it inherits its parent's entry.
3. **Perfil.** Hide what a perfil cannot do (cosmetic), and let the API refuse
   it anyway (invariant 8). Never let the screen be the only check.
4. **States.** Loading skeleton (`loading.tsx`), empty, and error with the
   gestor contact (DESIGN.md §6).
5. **Tests.** `frontend/e2e/<screen>.spec.ts`, one test per AC, in Chromium,
   Firefox and WebKit, plus the accessibility check of AC-0010-44.
6. **This map.** Update the row: route, sidebar slot, perfis, spec, status.
