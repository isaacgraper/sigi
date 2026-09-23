# Traceability Matrix

Maintained by `/trace` (agent: `traceability-auditor`). Every row must resolve
to a passing test before its spec can move to `Implemented`. An empty Tests cell
on an `Approved` spec is a merge blocker.

## Requirement → Spec

| RF/RN | Spec | Acceptance criteria | Tests | Status |
| --- | --- | --- | --- | --- |
| RF01, RN01 | SPEC-0001 v0.5 | AC-0001-01..09 | _pending_ | **Approved** |
| RF01 (OIDC) | SPEC-0001 v0.5 | AC-0001-19..22, AC-0001-24 | _pending_ | **Approved** |
| RF02, RF18, RN16 | SPEC-0001 v0.5 | AC-0001-10..14, AC-0001-25, -26, -28, -29 | _pending_ | **Approved** |
| RN04 | SPEC-0001 v0.5 | AC-0001-15..18, AC-0001-23 | _pending_ | **Approved** |
| RN06 (enforcement) | SPEC-0001 v0.5 | AC-0001-27 | _pending_ | **Approved** |
| RF01 (redefinição) | SPEC-0001 v0.5 | AC-0001-30..32 | _pending_ | **Approved** |
| RNF16 | SPEC-0001 v0.5 | AC-0001-33 | _pending_ | **Approved** |
| RF04, RF08, RF19 | SPEC-0002 v0.2 | AC-0002-01..12 | _pending_ | Draft |
| RN11, RN13, RN15 | SPEC-0002 v0.2 | AC-0002-13..17 | _pending_ | Draft |
| RF03, RF07, RN14 | SPEC-0003 v0.2 | AC-0003-01..10 | _pending_ | Draft |
| RF13, RN03, RN08, RN09 | SPEC-0004 v0.3 | AC-0004-01..24 | _pending_ | Draft |
| RF05, RN02, RN05, RN12, RF17 | SPEC-0005 v0.2 | AC-0005-01..11 | _pending_ | Draft |
| RF14, RN10, RN15 | SPEC-0006 v0.3 | AC-0006-01..12 | _pending_ | Draft |
| RF06, RF10 | SPEC-0007 | AC-0007-01..08 | _pending_ | Draft |
| RF09 | SPEC-0008 v0.2 | AC-0008-01..06 | _pending_ | Draft |
| RF12 | SPEC-0009 | AC-0009-01..07 | _pending_ | Draft |

## Unmapped

Requirements with no spec. This list must be empty before M5.

| Item | Reason |
| --- | --- |
| RF16 (reajuste) | Not yet specified — needs the entity's price-revision policy. OQ-08 is now partially answered: `DATA LIMITE REAJUSTE` exists per item, so the window is tracked; index and approver are still unknown. |
| ~~RF20, RF21~~ | ~~Deliberately deferred post-MVP.~~ **2026-09-02: no longer unmapped.** The stated reason (no consumption history at launch) was false — the entity exports it. Both are **in scope** under ADR-0008/ADR-0009 and need specs of their own. |
| RN07 | OQ-04 is resolved and the axes are `unidade` and `grupo de materiais`. **2026-09-10:** moved out of SPEC-0001 to **SPEC-0003**. RN07 restricts which *insumos* a servidor may see, and neither reference table exists yet, so a criterion in SPEC-0001 would have asserted nothing observable. Unmapped until SPEC-0003 is revised. |

## Spec → NFR

| NFR | Verified by |
| --- | --- |
| RNF01 | `tests/perf/k6_hot_endpoints.js` |
| RNF03 | `tests/test_auth_tokens.py` |
| RNF05 | `tests/perf/k6_concurrency.js` |
| RNF06 | `frontend/e2e/responsive.spec.ts` |
| RNF08 | `tests/test_audit_immutability.py` |
| RNF09 | CI job `compose-smoke` |
| RNF10 | CI job `coverage` |
| RNF15 | `tests/test_money_precision.py` |
| RNF16 | `tests/test_rate_limiting.py` *(2026-09-10, ADR-0012)* |

## Acceptance criteria added or revised *(2026-09-02, 2026-09-10)*

No AC has ever been renumbered. Revisions change a criterion's content under a
version bump and a changelog line; additions take the next free number.

### Done — SPEC-0004 v0.3 and SPEC-0006 v0.3

| AC | Change | Driver |
| --- | --- | --- |
| AC-0004-01 | Opens an NE with an `itens[]` list; asserts the derived valor | ADR-0007 |
| AC-0004-02 | RN09 re-read: an empty `itens` list is a missing mandatory field | ADR-0007 |
| AC-0004-12, -13, -14, -16 | Saldo guard, concurrency, reservation and release aggregate over `ITEM_NOTA_EMPENHO`; reservation is all-or-nothing | ADR-0007 |
| AC-0004-19 | **New** — an NE may not be emptied of its last item | RN09 |
| AC-0004-20 | **New** — the same `ITEM_ATA` may not appear twice in one NE | ADR-0007 |
| AC-0004-21 | **New** — every item must belong to the NE's ATA (I2/DB2) | ADR-0007 |
| AC-0004-22 | **New** — itens are frozen from `pre_empenho`; correction is cancel-and-reopen | OQ-27 (Assumed) |
| AC-0004-23 | **New** — `valor_unitario` is snapshotted at opening; a later reajuste does not reach back | I5 |
| AC-0004-24 | **New** — quantity exhaustion blocks even when budget remains | OQ-20, RN10 |
| AC-0006-02, -05, -06, -07 | Aggregate over `ITEM_NOTA_EMPENHO`; performance re-measured across one more join | ADR-0007 |
| AC-0006-10, -11, -12 | **New** — quantity saldo per item; value and quantity disagreeing about exhaustion; 25% aditivo ceiling | OQ-20, RN15 |

### Done — SPEC-0001 v0.5

| AC | Change | Driver |
| --- | --- | --- |
| AC-0001-01..18 | Rewritten Given/When/Then. v0.2 stated them in prose, from which no test derives mechanically. No meaning changed, nothing renumbered | `spec-format` |
| AC-0001-14 | Revised — no longer anonymises `cpf`, a field no entity carries | OQ-10 (Assumed) |
| AC-0001-15, -16, -17 | Split into three criteria; they were three IDs sharing one paragraph | `spec-format` |
| AC-0001-19 | **New** — OIDC authorization request carries PKCE, `state` and `nonce` | ADR-0010 |
| AC-0001-20 | **New** — the provider's identity token is verified before it is trusted | ADR-0010 |
| AC-0001-21 | **New** — authentication never creates an account; no JIT provisioning | ADR-0010, RN01, RF02 |
| AC-0001-22 | **New** — `perfil` comes from the usuario record, never from a provider claim | ADR-0010, 17/08 meeting |
| AC-0001-23 | **New** — a write route with no permission entry fails the build | RN04 |
| AC-0001-24 | **New** — local login is switchable; disabled returns 404, not 403 | ADR-0010 |
| AC-0001-25 | **New** — an invitation is single-use and expires in 72 h | `/spec-review` |
| AC-0001-26 | **New** — the password policy is enforced on activation, and a rejection does not burn the token | `/spec-review` |
| AC-0001-27 | **New** — the history table refuses UPDATE and DELETE at the database level | RN06, RNF08, ADR-0004 |
| AC-0001-28 | **New** — a duplicate or off-domain invitation is refused | `/spec-review` |
| AC-0001-29 | **New** — the last active gestor cannot be blocked or deactivated | `/spec-review` |
| AC-0001-02, -03 | Revised in v0.4 — the lockout moved off the account and onto the submitted address, because keying it on the usuario made AC-0001-02 **false**: six attempts distinguished a real address from an unknown one | persistence review |
| AC-0001-30, -31, -32 | **New** in v0.5 — password reset. A forgotten local credential had no recovery path at all: the scope line promised the flow without a criterion, and AC-0001-28 blocked the only workaround | product owner |
| AC-0001-33 | **New** in v0.5 — rate limiting across every auth route, keyed on the source, independent of the per-address lockout | product owner, ADR-0012 |

**On RN06.** Its *enforcement* — the privilege revocation and the trigger — is
built and proven in SPEC-0001 (AC-0001-27), because four of that spec's criteria
need an audit row and the substrate could not wait. SPEC-0007 keeps what it
always owned: the history queries, the per-entity timeline and the auditor's
screens. The rule is not split, only its proof arrives earlier than its reader.

### Still pending

| Spec | ACs affected | Driver |
| --- | --- | --- |
| SPEC-0002 | AC-0002-* covering ATA import — re-scope to manual registration + CSV of items; ATA status enum | OQ-02, OQ-19, OQ-21 |
| SPEC-0005 | RN12 AC compares against `Σ ITEM_NOTA_EMPENHO.valor` | ADR-0007 |
| SPEC-0003 | Validation ACs gain the concrete import hazards in `data-sources.md` §12; four identifiers; `GRUPO_MATERIAL`; **and RN07's scope by unidade and grupo de materiais, moved here from SPEC-0001** | OQ-29, OQ-23, OQ-04 |

### Capabilities with no spec at all

The entities added on 2026-09-02 are modelled but unspecified. Each needs a spec
before any of it can be built.

| Capability | Entities | Source |
| --- | --- | --- |
| CSV import and validation | — **no RF covers this** | `data-sources.md` §12 |
| Stock coverage snapshot | `POSICAO_ESTOQUE_SNAPSHOT` | ADR-0008, RF20 |
| Unidades and solicitações | `UNIDADE`, `CENTRO_CUSTO`, `SOLICITACAO`, `ITEM_SOLICITACAO`, `CRONOGRAMA` | OQ-26 |
| Processo licitatório | `PROCESSO_LICITATORIO`, `ETAPA_PROCESSO`, `ITEM_PROCESSO` | OQ-21 |
| Action on a critical item | `ACAO_ITEM` | OQ-21, OQ-26 |
| Saldo runway projection | — (RF21) | SPEC-0006 §4 |

**On requirement numbering.** Strict CSV import validation has no `RF` in
`functional.md`, whose contract stops at RF21. It is numbered `RF30` in
`docs/rfc-sigi-v1.7.md`, but that document is **superseded** and its `RF04`–`RF30`
range collides with this one (`RF05` and `RN11` mean different things in each).
Nothing here may cite those numbers. A new RF must be allocated from this file's
sequence when the import capability is specified. See OQ-28.

## Sources → model

*(2026-09-02)* `docs/architecture/data-sources.md` maps every column of the
entity's eight export reports to a destination in the model, or records that it
has none. Eleven of the sixteen columns in the coverage report, and all thirteen
in the fulfilment report, currently have no destination.
