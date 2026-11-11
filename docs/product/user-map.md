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
| `/atas` | ATAs: vencimentos e reajustes, list; Exportar (SPEC-0009 AC-0009-10) | ATAs (2nd) | W | ✓ | ✓ | SPEC-0013 | Approved, built |
| `/atas/{id}` | One ATA: aditivos, reajustes, moves; its items (SPEC-0014 §4.7); its saldo (SPEC-0015); Exportar its items (SPEC-0009 AC-0009-10); its Acompanhamento, gestor and auditor (SPEC-0017) | under ATAs | W | ✓, items of its grupos, no Acompanhamento | ✓ | SPEC-0013, SPEC-0014, SPEC-0017 | Approved, built |
| `/atas/nova` | Nova ATA: the registration, in sections | under ATAs | W | — | — | SPEC-0013 | Approved, built |
| `/atas/{id}/editar` | Editar ATA: the edit, in sections | under ATAs | W | — | — | SPEC-0013 | Approved, built |
| `/atas/{id}/itens/importar` | Importar itens: an ATA's items file, checked first | under ATAs | W | — | — | SPEC-0014 §4.6 | Approved, built |
| `/insumos` | Insumos: the catalogue, searched and filtered; Exportar, a servidor its grupos (SPEC-0009 AC-0009-10, -11) | Insumos (3rd) | W | W, its grupos | ✓ | SPEC-0014 §4.2 | Approved, built |
| `/insumos/{id}` | One insumo: its ATAs, SKU, discontinue, substitute, reactivate; its rastreio, ATA to NF (SPEC-0017) | under Insumos | W | ✓, its grupos | ✓ | SPEC-0014 §4.4, SPEC-0017 | Approved, built |
| `/insumos/novo` | Novo insumo | under Insumos | W | W, its grupos | — | SPEC-0014 §4.3 | Approved, built |
| `/insumos/{id}/editar` | Editar insumo | under Insumos | W | W, its grupos | — | SPEC-0014 §4.3 | Approved, built |
| `/insumos/grupos` | Grupos de materiais: the tree, create, rename | under Insumos | W | ✓, its grupos | ✓ | SPEC-0014 §4.5 | Approved, built |
| `/insumos/importar` | Importar catálogo: the file, checked first | under Insumos | W | — | — | SPEC-0014 §4.6 | Approved, built |
| `/notas-empenho` | Notas de empenho: counters, list by etapa; Exportar (SPEC-0009 AC-0009-10) | Notas de empenho (4th) | W | ✓, advances | ✓ | SPEC-0015 | Approved, built |
| `/notas-empenho/nova` | Abrir NE: ATA, Processo SEI, quantities | under Notas de empenho | W | — | — | SPEC-0015 | Approved, built |
| `/notas-empenho/{id}` | One NE: stages, itens, advance, revert, cancel; its Acompanhamento, gestor and auditor (SPEC-0017) | under Notas de empenho | W | ✓, advances, no Acompanhamento | ✓ | SPEC-0015, SPEC-0017 | Approved, built |
| `/notas-fiscais` | Notas fiscais: list by status and quarentena; Exportar (SPEC-0009 AC-0009-10) | Notas fiscais (5th) | W | ✓, registers, sends, quarantines | ✓ | SPEC-0016 | Approved, built |
| `/notas-fiscais/nova?ne={id}` | Registrar NF: número, data, valor, CNPJ, quantities | under Notas fiscais | W | ✓ | — | SPEC-0016 | Approved, built |
| `/notas-fiscais/{id}` | One NF: itens, send, approve, return, quarantine, release; its Acompanhamento, gestor and auditor (SPEC-0017) | under Notas fiscais | W | ✓, no decisions, no Acompanhamento | ✓ | SPEC-0016, SPEC-0017 | Approved, built |
| `/notas-fiscais/{id}/corrigir` | Corrigir NF: the same form, in Aguardando or Devolvida | under Notas fiscais | W | ✓ | — | SPEC-0016 | Approved, built |
| `/historico` | Histórico: every event, filtered by entity, member and period, rows that open, only values or only statuses; Exportar (SPEC-0009 AC-0009-12) | Histórico (6th) | ✓ | — | ✓ | SPEC-0017 | Approved, built |
| `/members` | Membros: invite, block, unblock, reset, deactivate | Membros (last) | W | — | ✓ | SPEC-0010 §4.7–4.8, SPEC-0014 §4.8 | Implemented; a servidor's grupos Approved, built |

### Planned, with no screen spec yet

Each needs its own screen spec, as SPEC-0013 is for SPEC-0002, before it is built.
The sidebar slot is where it goes between ATAs and Membros.

| Area | Backend spec | Likely route | Sidebar slot |
| --- | --- | --- | --- |
| Notificações | SPEC-0008 | the header bell | none |
| Relatórios, the four reports of AC-0009-01 | SPEC-0009 | `/relatorios` | before Membros |

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
