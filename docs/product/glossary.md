# Glossary

Domain terms stay in Portuguese everywhere: code, database, API, UI. This table
is the authority on spelling and meaning. If a term is not here, it is not a
domain term yet — add it before using it.

| Term | Code identifier | Meaning |
| --- | --- | --- |
| **ATA de Registro de Preços** | `ATA`, `ata_id` | Price-registration agreement fixing supplier, items, unit prices and a total contracted value for a validity period. The root of every supply cycle. |
| **Vigência** | `vigencia_inicio`, `vigencia_fim` | The period during which an ATA can generate new empenhos. Distinct from lifecycle status. |
| **Aditivo** | `aditivo` | Amendment increasing an ATA's quantity/value, capped at 25% of the original quantity under Brazilian procurement practice. Changes available `saldo`. |
| **Reajuste** | `reajuste` | Price revision of an ATA's items within a window. Changes unit prices, therefore future `saldo` consumption. |
| **Item da ATA** | `ITEM_ATA` | A specific `insumo` inside an ATA, with quantity and unit price. The join entity between ATA and Insumo. |
| **Insumo** | `INSUMO`, `insumo_id` | A catalogued supply item (paper, toner, gloves). Identified by a `codigo` compatible with DOMS. |
| **Nota de Empenho (NE)** | `NOTA_EMPENHO` | The commitment of budget against an ATA for a given item and quantity. The core entity of SIGI. |
| **Empenhar / Empenhado** | `valor_empenhado` | To commit budget. The cumulative committed value of an ATA. |
| **Nota Fiscal (NF)** | `NOTA_FISCAL` | The supplier's invoice, evidencing delivery. Always bound to an NE, never directly to an ATA. |
| **Liquidação** | — | The administrative act of verifying delivery against the NF. Modelled here as the NF conference status; payment itself is out of scope. |
| **Saldo** | `saldo_disponivel` | ATA total value minus committed NEs. **Derived, never stored as mutable state.** |
| **Processo SEI** | `processo_sei` | Identifier of the administrative process in the SEI system, e.g. `00301.000451/2026-12`. Mandatory on every NE. |
| **Fornecedor** | `FORNECEDOR` | Supplier, identified by CNPJ. |
| **Servidor** | `USUARIO` with `perfil='servidor'` | Public employee. Registers insumos and NFs, advances NE steps. Cannot reverse. |
| **Gestor** | `perfil='gestor'` | Manager. Full CRUD on ATAs/NEs/members; the only role that may reverse a step or close an ATA. |
| **Auditor** | `perfil='auditor'` | Read-only. History, reports, exports. |
| **DOMS** | — | Third-party platform whose item nomenclature SIGI must remain compatible with. **No API integration**; compatibility via `codigo` format validation and CSV import. |
| **e-Publica** | — | State government platform for administrative processes. **No API integration.** *(2026-09-02: the entity's export contract contains **no ATA report at all** — ATAs are registered manually and only their items are imported by CSV. See `data-sources.md` §1.)* |
| **Histórico de movimentação** | `HISTORICO_MOVIMENTACAO` | Append-only audit trail of every mutation, with actor, timestamp, action and prior state. |
| **Prestação de contas** | — | Public accountability reporting. The reason the audit trail must be immutable. |
| **CAME** | — | The legacy spreadsheet ("Controle CAME 2026") SIGI replaces. Under ADR-0009 it is also a **source of truth** for how the operation works, not merely a field mapping. |
| **Cobertura** | `cobertura`, `dias_estoque` | How long current stock lasts at the current consumption rate. The figure that triggers a purchase: below three months, buy. Imported from DOMS, never computed by SIGI. |
| **Estoque** | `estoque_atual` | Physical stock held at a unidade, **imported as a dated snapshot** from DOMS. Distinct from `saldo`; never summed with it. SIGI is not its system of record (ADR-0008). |
| **Curva ABC / XYZ** | `curva_abc`, `curva_xyz` | Value and predictability classification of an insumo, computed by DOMS and imported. Drives which items deserve attention first. |
| **Ponto de pedido** | `ponto_pedido` | Stock level at which a purchase should start, computed by DOMS and imported. SIGI reads it; it does not calculate one. |
| **Unidade** | `UNIDADE`, `unidade_id` | A health facility served by CAME (UBSF, UPA, hospital), with its own population and teams. Every stock and fulfilment figure is keyed by it. |
| **Solicitação / Requisição** | `SOLICITACAO` | A unidade's request for insumos, raised inside a cronograma window and passing through autorização → aprovação → finalização. |
| **Cronograma** | `cronograma` | The calendar of request and delivery windows per unidade (e.g. `PEDIDO QUINZENAL`). A request outside its window is `Administrativa`; inside it, `Manual`. |
| **Grupo / Subgrupo de materiais** | `GRUPO_MATERIAL` | Three-level classification of insumos (grupo → subgrupo → classificação). Compradores own grupos; alerts and lists are segmented by them. |
| **Comprador** | `perfil='comprador'` | The role that works the purchase list for its grupo de materiais. Present throughout the operation; not yet in the RBAC model (OQ-26). |
| **Cincatarina** | — | Shared-purchase consortium through which some ATAs are acquired without the entity running the pregão itself. |
| **Atesto** | — | Formal attestation that a delivery was received and conforms, with an SLA (`Normal 48H`). Exists in the source; not modelled in the MVP (OQ-22). |

## Terms deliberately avoided

| Avoid | Because | Use instead |
| --- | --- | --- |
| Using "estoque" and "saldo" as synonyms | They are different quantities from different sources: `saldo` is budget derived from the NE ledger, `estoque` is physical stock imported from DOMS. Conflating them produces a number that is true of neither | Name whichever you mean. Never sum them |
| "Estoque" for something SIGI computes | *(2026-09-02: the earlier rule avoided the word entirely, which no longer holds — see ADR-0008.)* SIGI imports stock; it never calculates or mutates it | "Snapshot de estoque", always with its `data_referencia` |
| "Integração" for DOMS/e-Publica | Implies an API contract that does not exist | "Consistência operacional" / "importação CSV" |
| "Quantidade mínima" as a stock threshold | It is a process alert, not a reorder point | "Quantidade de referência" |
| "Inventory", "invoice", "purchase order" | English translations of legal instruments create ambiguity in audit | `insumo`, `nota fiscal`, `nota de empenho` |
