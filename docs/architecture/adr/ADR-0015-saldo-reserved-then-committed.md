# ADR-0015 — Saldo is reserved from pré-empenho and committed at emission; delivery is tracked on the NE

- **Status:** Accepted
- **Date:** 2026-10-06
- **Deciders:** Isaac Kleimmann Graper, on the stakeholder's answer
- **Confirms:** ADR-0003 (the formula stands as written)
- **Related:** ADR-0007, ADR-0008, ADR-0009, OQ-03, OQ-40, RN10, RN12, RN17, SPEC-0004, SPEC-0005, SPEC-0006

*(History: a first version of this ADR, dated 2026-10-02, read the answer to
questionnaire question 6 as "saldo is consumed when an NF is approved" and added a
third term, `valor_consumido`, to the formula. The stakeholder's reply of
2026-10-06 showed that reading was wrong. This text replaces it before anyone
reviewed it.)*

## Context

ADR-0003 fixed saldo as `valor_contratado − valor_reservado − valor_empenhado`,
and OQ-03 proposed that an NE reserves from `pre_empenho` and is committed at
`ne_emitida`. It was `Assumed`.

Question 6 asked whether that was right. The answer was: *"Esta correta a afirmação
da reserva a partir do pré-empenho, porém o consumo deve ser considerado apenas
depois desta entrega ser realizada e este volume entrar em estoque."* I read
"consumo" as a third saldo term. A follow-up asked what that meant, and the
stakeholder gave two examples:

> *"se for emitido pré-empenho de 300 unidades para um item com inicial de 1.000
> deve ficar 700(300) até a emissão do empenho, após emissão do empenho o novo
> saldo deve ser apenas 700."*

> *"o empenho emitido tem 300 unidades; chegou uma nota com 100; o empenho só marca
> a quantidade faltante de 200 apenas após o lançamento da nota, salvo casos de
> algum problema com a nota ou material, nesses casos seria interessante uma
> maneira de destacar que o item chegou porém está em quarentena."*

The first is ADR-0003's model exactly: the ATA's saldo is 700 from `pre_empenho`
onward, with the 300 shown as reserved until the empenho is issued. The second
is about something else: what the **NE** still waits for. It is counted in units,
it moves when an NF is **launched** (not when it is approved), and an NF with a
problem must be visible without being counted.

## Options considered

| Option | Pros | Cons |
| --- | --- | --- |
| A. Third saldo term, consumed on NF approval (the first version of this ADR) | Matches the word "consumo" | Contradicts the stakeholder's own example, and ties saldo to an approval they never mentioned |
| **B. Keep ADR-0003's saldo, track delivery on the NE as `quantidade_faltante`** | Matches both examples; saldo stays the one figure the buyer decides on | The NF needs item lines, which it does not have |
| C. B, but counting from NF approval | Uses an existing status | The stakeholder said "lançamento da nota", and was confused by "aprovada" |

## Decision

Option B.

1. **Saldo is derived, never stored** (ADR-0003 stands), and its formula is
   `saldo_disponivel = valor_contratado − valor_reservado − valor_empenhado`.
2. `valor_reservado` is the value of the NEs in `pre_empenho` and
   `envio_fornecedor`. `valor_empenhado` is the value of the NEs in `ne_emitida`.
   Both subtract from saldo, so **issuing the NE does not change it**.
3. **Presentation:** while an NE is reserved, the saldo reads like `700 (300)`,
   the reserved part in parentheses; once it is issued, the saldo reads `700`.
4. **Delivery is tracked on the NE, per item, and never touches the ATA's saldo.**
   `quantidade_faltante = quantidade − quantidade_recebida`, where
   `quantidade_recebida` sums the quantities of the NFs bound to that NE.
5. **An NF counts when it is launched**, that is, registered, and not when it is
   approved. An NF returned (`devolvida`) or in quarantine does not count.
6. **Quarantine:** an NF with a problem in the note or in the material is flagged
   with a reason. Its quantity is not counted, and the NE shows that the item
   arrived and is in quarantine. Releasing it makes it count. The four NF statuses
   are unchanged (OQ-12). This is `Assumed` (OQ-46).
7. **The NF carries item lines** (`ITEM_NOTA_FISCAL`: an NE item and a quantity),
   which is what makes 4 possible. Its total `valor` and RN12 are unchanged.

## Consequences

**Positive** — the saldo a new NE can claim is what ADR-0003 always said, so
nothing that decides a purchase moves, and RN10's guard is unchanged. The NE
answers the question the entity actually asks, *how much is still missing*.

**Negative** — the NF now needs the quantity per NE item, which is more to type at
launch, and a line above the NE's `quantidade_faltante` has no rule yet (OQ-46).
An NE that is issued and never delivered keeps its value committed and `ne_emitida`
is terminal (AC-0004-11), so nothing releases it. That is not new, and it needs its
own instrument, which is not specified.

**Follow-up**

- Invariant 5 in `CLAUDE.md` and RN17 say this in one place each.
- SPEC-0004 v0.4, SPEC-0005 v0.3 and SPEC-0006 v0.4 carry the criteria.
