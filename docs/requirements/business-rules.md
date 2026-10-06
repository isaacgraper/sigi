# Business Rules

Each rule is restated in enforceable form: where it is enforced, and how it is
proven. "Enforced in the service layer" alone is insufficient for anything an
auditor will rely on — those rules are also expressed as database constraints.

| ID | Rule | Enforced at | Proof |
| --- | --- | --- | --- |
| RN01 | Only authenticated users with an active profile may access the system | Auth middleware; `usuario.ativo` checked on every token validation, not only at login | Test: deactivating a user invalidates an unexpired token |
| RN02 | An NF may only bind to an NE whose status is `ne_emitida`; the ATA link is inherited through the NE | Service + DB `CHECK` via trigger on `NOTA_FISCAL` insert | Test per invalid NE status (5 cases) |
| RN03 | An NE status may only advance; reversal requires a recorded justification | Service state machine + `HISTORICO_MOVIMENTACAO` row with non-null `motivo` | Test: reversal without justification → 422 |
| RN04 | Only `gestor` may issue and close ATAs | Endpoint dependency | Test per role (3 cases) per endpoint |
| RN05 | Every NF must include número, data de emissão, valor and fornecedor | Pydantic schema + DB `NOT NULL` | Schema test |
| RN06 | Changes to auditable records preserve the original history | Append-only table; `REVOKE UPDATE, DELETE` + `BEFORE UPDATE OR DELETE` trigger raising an exception | Test: direct UPDATE raises |
| RN07 | Servidores may only view insumos within their area of competence (RBAC) | *(2026-09-10)* No longer blocked. OQ-04 is resolved: the "área de competência" is two axes the data does carry — **unidade** and **grupo de materiais**. Enforced by the shared authorisation rule SPEC-0001 owns, applied to the first scoped resource in **SPEC-0003**; out-of-scope reads return 404, not 403, so existence is not disclosed. The scope columns land with SPEC-0003, because neither `UNIDADE` nor `GRUPO_MATERIAL` exists yet. | Test: a scoped servidor sees only its unidade and grupo; a servidor with no scope sees nothing |
| RN08 | The NE flow is sequential and mandatory: `demanda → validacao_saldo → pre_empenho → envio_fornecedor → ne_emitida`. Steps may not be skipped | Explicit transition table in `services/ne_state_machine.py` | Test: all 25 (from, to) pairs, 4 valid + 21 rejected |
| RN09 | An NE must carry Processo SEI, ATA, insumo, quantity and estimated value before it can be opened | Pydantic schema + DB `NOT NULL` | Schema test |
| RN10 | ATA saldo is validated automatically before pré-empenho; NEs exceeding available saldo are blocked | Service, inside a transaction with `SELECT ... FOR UPDATE` on the ATA row | Test: concurrent NEs, only one passes |

## Rules the RFC implies but never states

| ID | Rule | Why it is needed |
| --- | --- | --- |
| RN11 | An NE may only be opened against an ATA whose vigência covers the current date and whose status is not `cancelada`/`encerrada` | Otherwise a closed ATA can accrue new commitments — an audit finding waiting to happen. Nothing in RN01–RN10 forbids it. |
| RN12 | The sum of NF values bound to an NE may not exceed the NE value without a recorded justification | Prevents silent over-invoicing; the RFC checks saldo at NE level but never at NF level. |
| RN13 | An ATA may only be closed (`encerrada`) when no NE is in a non-terminal state | Otherwise in-flight commitments are orphaned. |
| RN14 | `insumo.sku` is globally unique and immutable once referenced by an `ITEM_ATA`. A substituted item is never rewritten: the old insumo stays as it was and points to its substitute (`substituido_por_id`) | Changing it retroactively breaks the correspondence with the CAME and DOMS sheets in historical records. The SKU is the identity because the stakeholder chose it (OQ-29, 2026-10-02). |
| RN15 | An aditivo may not increase an ATA's quantity beyond 25% of the original | Stated in the mockup ("Aditivo máximo permitido: 25% do quantitativo") but in no rule. |
| RN16 | Deactivating a user anonymises personal data while preserving audit rows (LGPD art. 16, I) | Stated in the LGPD section; must be a rule, since it constrains RN06. |
| RN17 | An NE reserves saldo from `pre_empenho` and commits it at `ne_emitida`; both subtract from `saldo_disponivel`, so issuing the NE does not change it. Delivery is tracked on the NE as `quantidade_faltante`, counted when an NF is launched, and never changes the ATA's saldo | The stakeholder's own example: 300 of 1.000 reads `700 (300)` until the empenho is issued, then `700`; an NF of 100 against an NE of 300 leaves 200 missing (2026-10-06, OQ-03, ADR-0015). Derived on every read (SPEC-0006 §2.1); proven by SPEC-0006 AC-0006-13 to -15, SPEC-0004 AC-0004-15 and SPEC-0005 AC-0005-10. |

## Reserved vs. committed saldo

RN10 validates saldo at `validacao_saldo`, before the NE has claimed anything. If
the claim waited for emission, two concurrent NEs could both pass validation and
jointly exceed the ATA. The system therefore reserves from `pre_empenho` and
recognises these quantities, defined in SPEC-0006:

- **`valor_contratado`** — ATA total, plus aditivos.
- **`valor_reservado`** — sum of NEs in `pre_empenho` or `envio_fornecedor`.
- **`valor_empenhado`** — sum of NEs in `ne_emitida`.
- **`saldo_disponivel` = `valor_contratado` − `valor_reservado` − `valor_empenhado`.**

RN10 validates against `saldo_disponivel`, which closes the gap. The same holds in
quantity, per item. A reserved NE reads `700 (300)`; once issued, `700`.

**Delivery is a different thing and never enters that formula.** For each item of
an NE, `quantidade_faltante` is the quantity ordered less the quantity of the NFs
launched against it, except an NF that is in quarantine or `devolvida`
(ADR-0015, RN17).

*(2026-10-06.)* A first version of this section, dated 2026-10-02, added a third
term, `valor_consumido`, counted from an approved NF. The stakeholder's example
showed that was a misreading and it was removed before review.
