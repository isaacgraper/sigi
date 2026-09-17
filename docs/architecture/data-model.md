# Data Model

Status: Draft · Source: RFC v1.6 §5.2, with corrections noted inline.

Revised 2026-09-02 against the stakeholders' operational data — see
`data-sources.md`. Changes of that round are marked *(2026-09-02)*.

## Entities

### USUARIO
`id UUID PK`, `nome NULL`, `email UNIQUE NULL`, `senha_hash NULL`,
`perfil ENUM(gestor, servidor, auditor)`, `status ENUM(pendente, ativo,
bloqueado, desativado)`, `criado_em TIMESTAMPTZ`,
`anonimizado_em TIMESTAMPTZ NULL`, `oidc_subject VARCHAR UNIQUE NULL`,
`ativo BOOL GENERATED ALWAYS AS (status = 'ativo') STORED`,
`pseudonimo TEXT GENERATED ALWAYS AS ('USR-' || upper(substr(encode(uuid_send(id), 'hex'), 1, 12))) STORED UNIQUE`.

`status` is added: the mockup shows Pendente and Bloqueado, which a single
boolean cannot express.

***(2026-09-10)* `senha_hash` is nullable, on purpose.** An invited account
exists before it has a credential (AC-0001-10), and an account that
authenticates only through the institutional provider never gets one. `NOT NULL`
here would force whoever accepts an invite to invent a password nobody chose.

***(2026-09-10)* `oidc_subject`** binds the provider's stable subject claim to
the account, so a later change of institutional e-mail does not orphan it. It is
populated on the first successful OIDC login and matched by e-mail only that
once. `UNIQUE` prevents two accounts claiming one identity.

***(2026-09-10)* `ativo` became a generated column.** It was described as "a
derived convenience" and stored as a plain boolean — which is the column that
eventually disagrees with `status`, and here it would disagree about who may
manage members. "Blocked" had three representations and nothing kept them
consistent. Now there is one source (`status`) and one derivation the database
maintains.

***(2026-09-10)* `pseudonimo` is what makes AC-0001-14 possible at all.** The
audit trail must show a stable name for an anonymised user, and every other
route is closed: writing `nome` into `dados_anteriores` is forbidden by
`lgpd.md`; updating audit rows at anonymisation time is forbidden by
AC-0001-27; and a mutable mapping table adds nothing `usuario_id` does not
already give. So the pseudonym is an attribute of the usuario that anonymisation
cannot touch — `GENERATED ALWAYS ... STORED` cannot be the target of an `UPDATE`
at all, so PostgreSQL enforces the immutability with no trigger and no key to
lose. It derives from a random UUID, not from `nome` or `email`, so it is not
reversible to a person. Twelve hex characters rather than eight, because it
carries a `UNIQUE` and 32 bits is not enough to ignore collisions.

`uuid_send` and `encode` are immutable, which the generated expression requires;
an `id::text` cast is not, and PostgreSQL rejects it.

***(2026-09-10)* Anonymisation is a database rule, not a convention:**

```sql
CHECK (anonimizado_em IS NULL
       OR (nome IS NULL AND email IS NULL
           AND senha_hash IS NULL AND oidc_subject IS NULL))
```

AC-0001-14 blanks only `nome` and `email`. A deactivated account that keeps a
live credential is an attack surface with no owner, and `lgpd.md` retains
federated identity only while the account is active — so `senha_hash` and
`oidc_subject` go too, and the constraint refuses a half-done anonymisation.

Consequence worth stating: once `email` is `NULL`, `UNIQUE (email)` no longer
blocks re-inviting that address. That is the intent — the person left the entity
— and AC-0001-28's "in any status" means every status except anonymised.

**The lockout counters are deliberately not here.** They live in
`TENTATIVA_LOGIN`, keyed on the submitted address rather than on the account,
because keying them on the usuario made AC-0001-02 false (SPEC-0001 v0.4).

### TENTATIVA_LOGIN *(new, 2026-09-10)*
`email_hmac BYTEA PK`, `tentativas INT NOT NULL DEFAULT 0`,
`ultima_em TIMESTAMPTZ NOT NULL`, `bloqueado_ate TIMESTAMPTZ NULL`,
`CHECK (tentativas >= 0)`.

The lockout of AC-0001-03. Keyed on an HMAC of the **submitted** e-mail — so a
row exists for addresses that have no account, which is exactly what makes a
known and an unknown address behave identically at the threshold. The pepper
lives in application configuration, never in the database, so a leaked dump does
not reveal which addresses were tried.

`ultima_em` is what makes the fifteen-minute window expressible. Two columns
express only "five failures ever", which would lock an account over failures
spread across days. The decay is applied in a single atomic statement, never a
read-modify-write, and the statement returns the new count so the audit row has
its `{tentativas}`.

Two operational notes: the increment must be **committed on the failure path**,
which is the path that otherwise rolls back and takes the lockout with it; and
no row lock is ever held across a bcrypt verification, or a credential-stuffing
run against one address would serialise on that row and exhaust the pool —
turning the mitigation into the outage.

### CONVITE *(new, 2026-09-10)*
`id UUID PK`, `usuario_id FK → USUARIO`, `token_hash BYTEA UNIQUE`,
`criado_por FK → USUARIO`, `criado_em TIMESTAMPTZ`,
`expira_em TIMESTAMPTZ`, `utilizado_em TIMESTAMPTZ NULL`,
`cancelado_em TIMESTAMPTZ NULL`.

The invitation of RF18 and AC-0001-10/11. Only the **hash** of the token is
stored: a leaked database must not yield usable invitations. `utilizado_em`
being non-null is what makes the token single-use (AC-0001-25), and it is a
column rather than a deletion so the audit trail can still explain how an
account came to exist.

```sql
CHECK (expira_em > criado_em)
CHECK (utilizado_em IS NULL OR utilizado_em <= expira_em)
CREATE UNIQUE INDEX ux_convite_aberto ON convite (usuario_id)
  WHERE utilizado_em IS NULL AND cancelado_em IS NULL;
```

The second `CHECK` is the database expression of the 72-hour rule. Do **not**
write it as `expira_em <= criado_em + interval '72 hours'`: `timestamptz +
interval` is `STABLE`, not `IMMUTABLE`, and PostgreSQL rejects it in a `CHECK`.
The same reason makes `CHECK (ocorrido_em <= now())` impossible on the audit
table — both are worth knowing before someone tries them.

***(2026-09-10)* `cancelado_em` exists because the partial index would otherwise
block the documented remedy.** AC-0001-25 tells a user whose invitation expired
to ask the gestor for a new one, and AC-0001-28 refuses a second invitation. One
outstanding invite per usuario is the right rule, but an *expired* unredeemed
invite still matches `utilizado_em IS NULL` — and `now()` cannot appear in an
index predicate, so the index cannot exclude it. Cancelling the old invite is
what makes reissue possible.

### SESSAO_FAMILIA *(new, 2026-09-10)*
`familia UUID PK`, `usuario_id FK → USUARIO`, `criada_em TIMESTAMPTZ`,
`revogada_em TIMESTAMPTZ NULL`, `UNIQUE (familia, usuario_id)`.

Nothing in the first draft bound a session family to one user, so a family could
have spanned two — and revoking it would have revoked another person's sessions.
A parent table makes that impossible in the schema rather than in a trigger, and
it turns the hot family-revocation write into a single-row update.

### SESSAO *(new, 2026-09-10)*
`id UUID PK`, `usuario_id FK`, `familia UUID`, `geracao SMALLINT NOT NULL`,
`refresh_token_hash BYTEA UNIQUE`, `emitido_em TIMESTAMPTZ`,
`expira_em TIMESTAMPTZ`, `revogado_em TIMESTAMPTZ NULL`,
`revogado_motivo VARCHAR(20) NULL`,
`UNIQUE (familia, geracao)`,
`FOREIGN KEY (familia, usuario_id) REFERENCES SESSAO_FAMILIA (familia, usuario_id)`.

Required by AC-0001-06/07. A refresh token that cannot be invalidated before its
own expiry is not a session, it is a seven-day bearer grant — so refresh state
lives server-side. `familia` groups every token descended from one login: on
rotation the old row is revoked and the new one takes the next `geracao`, and a
replay of an already-revoked row revokes the whole family. That is what turns a
stolen refresh token into a detectable event instead of a silent one.

```sql
CHECK (expira_em > emitido_em)
CHECK (revogado_em IS NULL OR revogado_em >= emitido_em)
CHECK (revogado_motivo IN ('rotacao','logout','replay','desativacao','bloqueio'))
CHECK ((revogado_em IS NULL) = (revogado_motivo IS NULL))

CREATE INDEX ix_sessao_familia_ativa ON sessao (familia)    WHERE revogado_em IS NULL;
CREATE INDEX ix_sessao_usuario_ativa ON sessao (usuario_id) WHERE revogado_em IS NULL;
CREATE INDEX ix_sessao_expira        ON sessao (expira_em);
```

***(2026-09-10)* `geracao` replaced a `substituido_por_id` self-reference.** The
chain was a second representation of what `familia` already carried, able to
disagree with it, and family revocation never walks it — it is one `UPDATE ...
WHERE familia = ? AND revogado_em IS NULL`. `UNIQUE (familia, geracao)` gives
the same forensic ordering, gap-free by construction, with one write instead of
two and no way to represent a cycle.

***(2026-09-10)* `revogado_motivo` is not cosmetic.** `revogado_em` alone cannot
tell the replay handler whether it is looking at a normally rotated token or a
logged-out one, and SPEC-0001 §8's `auth.refresh_replay` row has no reason field
to write without it.

**On hashing the token.** `SHA-256`, or better HMAC-SHA256 with a server-side
pepper, over a token carrying at least 128 bits from a CSPRNG. Explicitly **not**
bcrypt or argon2: stretching buys nothing against a high-entropy random value
and it destroys the index, because a salted hash cannot be looked up — every
refresh would become a table scan plus N verifications. The btree behind
`UNIQUE` is not constant-time, but converting that into a usable token would
mean inverting SHA-256. Same reasoning applies verbatim to `CONVITE.token_hash`.

**The lookup predicate is load-bearing.** Replay detection must query
`WHERE refresh_token_hash = :h` with **no** `AND revogado_em IS NULL`. A revoked
row has to be *found* for the replay to be detected; filtering it out in SQL
yields "not found", a plain 401, no family revocation — AC-0001-07 silently
unmet behind a test that still sees its 401.

### FORNECEDOR
`id UUID PK`, `cnpj UNIQUE`, `razao_social`, `email`, `ativo BOOL`.
CNPJ validated including check digits.

### ATA
`id UUID PK`, `numero UNIQUE`, `objeto`, `orgao`, `fornecedor_id FK`,
`data_emissao DATE`, `vigencia_inicio DATE`, `vigencia_fim DATE`,
`valor_total NUMERIC(15,2)`, `data_orcamento_planilhado DATE`,
`status ENUM(rascunho, vigente, suspensa, encerrada, cancelada)`,
`responsavel_id FK → USUARIO`.

Changes from the RFC: `fornecedor_id` added (Tela 5 shows a supplier per ATA but
the model had no link); `status` values replaced (`em_andamento/concluida/
cancelada` could not express the five badges in Tela 4); `situacao_vigencia` is
**not** a column — it is derived (SPEC-0002 §2).

***(2026-09-02)* Two state machines are conflated in the source.** The
spreadsheet's `STATUS DA ATA` holds 17 distinct values, of which only five
belong to the ATA (`VIGENTE`, `VENCIDA`, `SALDO ZERO`, `PRORROGADA`,
`CANCELADO`). The rest describe the **acquisition process** that precedes or
replaces the ATA — `SAP` (414), `FRACASSADO` (228), `CONSTRUÇÃO EDITAL` (202),
`EM LICITAÇÃO` (113), `PGM` (75), `DESERTO` (27), `TERMO DE REFERÊNCIA` (15).
`status` here stays the ATA's own lifecycle; the process axis needs its own
entity and is not modelled yet. See OQ-21.

***(2026-09-02)* `fornecedor_id` is not always singular.** 29 of 456 ATAs (6,4%)
carry more than one fornecedor, up to three. OQ-11 is resolved as "yes, it
happens"; the modelling response is deferred to SPEC-0002.

`CHECK (vigencia_fim > vigencia_inicio)`, `CHECK (valor_total > 0)`.

### ATA_ADITIVO *(new)*
`id UUID PK`, `ata_id FK`, `tipo ENUM(quantidade, valor, prazo)`,
`percentual NUMERIC(5,2)`, `valor_acrescimo NUMERIC(15,2)`,
`nova_vigencia_fim DATE NULL`, `justificativa TEXT`, `criado_por FK`, `criado_em`.

Required by RF15/RN15 and by the alternative flow "solicitar aditivo à ATA".
`valor_contratado` is `ATA.valor_total + Σ aditivos`.

### INSUMO
`id UUID PK`, `codigo UNIQUE`, `descricao`, `unidade`,
`grupo_id FK → GRUPO_MATERIAL NULL`, `sku VARCHAR NULL`,
`codigo_externo VARCHAR NULL`, `quantidade_referencia NUMERIC NULL`,
`ativo BOOL`, `substituido_por_id FK → INSUMO NULL`,
`descontinuado_em DATE NULL`.

**No `ata_id`.** RF03's "ATA vinculada" is realised through `ITEM_ATA` (SPEC-0003 §2).

***(2026-09-02)* Identity is plural.** The data carries four identifiers:
`SKU` (CAME mnemonic, e.g. `CLORDEG21`), the DOMS client code (`26829`), the
DOMS surrogate `mercadoriaId` (`3678`), and `Nº ITEM` (a position within a
pregão, not an identity). `codigo` holds the DOMS client code — the only one
shared across sources; `sku` and `codigo_externo` carry the other two so imports
can join. `Nº ITEM` belongs to `ITEM_ATA`, not here. See OQ-29.

***(2026-09-02)* `categoria` is replaced by `grupo_id`.** The real hierarchy has
three levels (15 groups, 44 group/subgroup pairs), which a flat string cannot
express.

***(2026-09-02)* Substitution.** `substituido_por_id` and `descontinuado_em`
record `ITEM SUBSTITUIDO POR ITEM 43204` / `ITEM DESCONTINUADO`, which the
operation performs and RN14 currently forbids. See OQ-23.

### GRUPO_MATERIAL *(new, 2026-09-02)*
`id UUID PK`, `nome`, `nivel SMALLINT`, `grupo_pai_id FK → GRUPO_MATERIAL NULL`,
`UNIQUE(nome, grupo_pai_id)`.

Self-referencing, three levels: `Grupo mercadoria` → `SubGrupo Mercadoria` →
`Classificao SubGrupo Mercadoria`. Sourced from
`TRANFERENCIA DE MERCADORIA (CSV)`.

### ITEM_ATA
`id UUID PK`, `ata_id FK`, `insumo_id FK`, `quantidade NUMERIC`,
`valor_unitario NUMERIC(15,4)`, `UNIQUE(ata_id, insumo_id)`.

Unit price uses four decimals: unit prices for consumables are frequently
sub-centavo, and rounding at storage time compounds across thousands of units.

### NOTA_EMPENHO
`id UUID PK`, `numero UNIQUE`, `processo_sei VARCHAR`, `data_emissao DATE`,
`status ENUM(demanda, validacao_saldo, pre_empenho, envio_fornecedor,
ne_emitida, cancelada)`, `ata_id FK`, `responsavel_id FK`, `criado_em`,
`atualizado_em`, `versao INT`.

`cancelada` is added (SPEC-0004 §4.1). `versao` supports optimistic locking for
`CONFLITO_DE_VERSAO`.

***(2026-09-02)* The NE is a header, not a line.** `quantidade`, `valor`,
`item_ata_id` and `insumo_id` are removed and live in `ITEM_NOTA_EMPENHO`.
Measured on real data: 27,8% of empenhos cover more than one insumo, the largest
covering 37. ADR-0007.

`ata_id` is retained deliberately: every item of an NE belongs to one ATA, so
the FK carries that invariant rather than leaving it to convention. This narrows
OQ-06 — the `insumo_id`/`item_ata_id` redundancy it warned about no longer
exists on this table.

`valor` is **derived**: `Σ ITEM_NOTA_EMPENHO.valor`. Same reasoning as ADR-0003,
one level down.

### ITEM_NOTA_EMPENHO *(new, 2026-09-02)*
`id UUID PK`, `nota_empenho_id FK`, `item_ata_id FK`, `quantidade NUMERIC`,
`valor_unitario NUMERIC(15,4)`, `valor NUMERIC(15,2)`,
`UNIQUE(nota_empenho_id, item_ata_id)`.

One row per insumo committed by the NE. **No status column** — the five-stage
flow describes the administrative document, so there is no partially advanced
NE (ADR-0005 unaffected). `valor_unitario` is copied from `ITEM_ATA` at opening
time, because a later reajuste must not retroactively change an issued empenho.

An NE with zero items cannot leave `demanda` (RN09).

### NOTA_FISCAL
`id UUID PK`, `numero`, `data_emissao DATE`, `valor NUMERIC(15,2)`,
`nota_empenho_id FK`, `fornecedor_id FK`, `servidor_id FK`,
`status ENUM(aguardando, em_conferencia, aprovada, devolvida)`,
`justificativa_devolucao TEXT NULL`,
`UNIQUE(numero, fornecedor_id)`.

`status` and `justificativa_devolucao` added (Tela 7 has statuses the RFC model
lacks — OQ-12). No `ata_id`: the ATA is reached through the NE (RN02).

### HISTORICO_MOVIMENTACAO

*(Corrected 2026-09-10. As previously written, **this table could not be
created**: PostgreSQL refuses a unique constraint on a partitioned table that
does not include every partitioning column, so `id UUID PK` with `PARTITION BY
RANGE` fails at `CREATE TABLE`. The project's first migration would not have
run.)*

```sql
CREATE TABLE historico_movimentacao (
  id               UUID        NOT NULL DEFAULT gen_random_uuid(),
  ocorrido_em      TIMESTAMPTZ NOT NULL,
  entidade_tipo    VARCHAR(40) NOT NULL,
  entidade_id      UUID        NOT NULL,
  acao             VARCHAR(60) NOT NULL,
  usuario_id       UUID        NULL REFERENCES usuario (id),
  dados_anteriores JSONB       NULL,
  justificativa    TEXT        NULL,
  correlation_id   UUID        NOT NULL,
  PRIMARY KEY (id, ocorrido_em),
  CHECK (acao ~ '^[a-z_]+\.[a-z_]+$'),
  CHECK (entidade_tipo ~ '^[a-z_]+$')
) PARTITION BY RANGE (ocorrido_em);
```

Four changes from the previous description, each with a reason:

- **`PRIMARY KEY (id, ocorrido_em)`.** Forced by partitioning. The cost is that
  `id` alone is no longer uniqueness-enforced; with UUIDv4 the collision risk is
  negligible, but the guarantee is gone and that should be a stated trade, not a
  surprise.
- **`timestamp` renamed to `ocorrido_em`.** `TIMESTAMP` is a type name; as a
  column it needs quoting in hand-written DDL, and `PARTITION BY RANGE
  (timestamp)` is exactly where the parser expects a type. The rename costs
  nothing and removes a whole class of bug from a table full of hand-written SQL.
- **`usuario_id` is nullable.** AC-0001-20 and AC-0001-21 both audit callers who
  have no account at all. `ON DELETE` stays at `NO ACTION`, which is what makes
  invariant I4 a database fact rather than a promise; `DELETE ON usuario` is
  also revoked from the application role, since AC-0001-14 replaces deletion
  with anonymisation and the privilege has no legitimate use.
- **`entidade_tipo` and `acao` gained format checks.** In a table that can never
  be corrected, a typo (`Usuario` for `usuario`) is permanent and silently
  breaks every later filter. An enum would be wrong — each new spec adds
  values — so the constraint is on shape, not on the value set.

**Indexes**, on the parent so they propagate to future partitions:

```sql
(entidade_tipo, entidade_id, ocorrido_em DESC)
(usuario_id, ocorrido_em DESC)
(correlation_id)                 -- "everything that happened in one request"
```

`CREATE INDEX CONCURRENTLY` is not supported on a partitioned table. Irrelevant
while the table is empty; painful later.

#### Append-only, and where the previous description was half-true

`REVOKE UPDATE, DELETE` **plus** a `BEFORE UPDATE OR DELETE FOR EACH ROW`
trigger (ADR-0004, RN06, RNF08, AC-0001-27). The details that decide whether
this actually holds:

- **Row triggers on the parent do propagate.** PostgreSQL 13+ clones a
  `BEFORE ... FOR EACH ROW` trigger to existing partitions and to any partition
  created or attached later. So new years are covered without action.
- **Statement-level triggers are not cloned.** A `TRUNCATE` guard on the parent
  never fires for `TRUNCATE historico_movimentacao_2027`. Defence against
  TRUNCATE is privilege-only.
- **Dropping a partition fires no trigger at all.** That is the real delete
  path, and only ownership stops it.
- **`ENABLE ALWAYS`** is required, or `session_replication_role = 'replica'`
  disables the trigger. Whether a clone on a later partition inherits it is
  asserted by a test, not assumed — the partition-creation routine re-applies it.
- **Privileges are per-partition, not inherited**, but permission is checked
  against the table *named in the query*. So `UPDATE historico_movimentacao` is
  checked against the parent and the `REVOKE` works, while
  `UPDATE historico_movimentacao_2026` is checked against that partition's own
  ACL — which grants the app role nothing, unless someone runs
  `GRANT ... ON ALL TABLES IN SCHEMA public`, the line every convenience script
  contains. Each partition therefore gets `GRANT SELECT, INSERT` explicitly and
  nothing else, and a test asserts the ACL.
- The trigger raises a **custom SQLSTATE** (`SI001`) so tests assert on a code
  rather than on a Portuguese message.

**Two database roles are a precondition, and today there is one.**
`docker-compose.yml` provisions only `sigi`, which is both owner and application
role — and an owner can `ALTER TABLE ... DISABLE TRIGGER`, `TRUNCATE`, and
re-`GRANT` itself `UPDATE`. ADR-0004 already says migrations run under a
separate role; until that exists, **the append-only guarantee is enforced by
nothing**. The migration guards its `GRANT`/`REVOKE` on a `pg_roles` lookup so
it fails loudly instead of half-applying.

#### Partitions

Created for **2026 through 2032** in the first migration, plus an idempotent
`SECURITY DEFINER` function `criar_particao_historico(ano int)` that creates a
partition, applies the narrow grant and re-applies `ENABLE ALWAYS`.

**Why seven at once:** nothing creates next year's partition automatically, and
an insert with no matching partition fails with SQLSTATE `23514`. Because every
write in SIGI must record its history row *in the same transaction*, that failure
is not localised — **every write endpoint starts returning 500 at midnight on
1 January.** A total, self-inflicted write outage, on a public holiday. Seven
empty partitions cost nothing and buy six years of not depending on a cron job
nobody is watching.

**A `DEFAULT` partition is a trap here** and is deliberately absent. It prevents
the outage, but rows landing in it cannot be moved out: attaching the real 2033
partition later requires the default to hold no overlapping rows, and the table
cannot be deleted from without breaking ADR-0004 at owner level.

**Bounds are written in explicit UTC** — `FROM ('2026-01-01 00:00:00+00')` — not
as bare dates. A bare date literal against a `TIMESTAMPTZ` column resolves in
the creating session's `TimeZone`, and this project sets `TZ=America/Sao_Paulo`
everywhere, so bounds would silently land at 03:00 UTC.

#### Downgrade

`alembic downgrade` **refuses** if the table holds any row, raising `SI002` with
the count. A downgrade that silently destroys the audit trail is not a
downgrade, and the definition-of-done's "reversible" cannot mean "reversible by
deleting the evidence". It drops the parent, not the partitions it happens to
know about, so cron-created ones do not become orphans.

`env.py` also needs an `include_object` filter excluding
`historico_movimentacao_%`, or the next `--autogenerate` will propose dropping
every partition as an unknown table.

## Relationships

```
USUARIO 1─────* ATA                (responsável)
USUARIO 1─────? HISTORICO_MOVIMENTACAO  (usuario_id é nullable: há linha sem ator)
USUARIO 1─────* CONVITE            (convidado; e outro FK para quem convidou)
USUARIO 1─────* SESSAO_FAMILIA
SESSAO_FAMILIA 1* SESSAO           (FK composta (familia, usuario_id))
FORNECEDOR 1──* ATA
FORNECEDOR 1──* NOTA_FISCAL
ATA 1─────────* ITEM_ATA *─────────1 INSUMO
ATA 1─────────* ATA_ADITIVO
ATA 1─────────* NOTA_EMPENHO       (all items of an NE share one ATA)
NOTA_EMPENHO 1* ITEM_NOTA_EMPENHO *1 ITEM_ATA
NOTA_EMPENHO 1* NOTA_FISCAL
GRUPO_MATERIAL 1* INSUMO
GRUPO_MATERIAL 1* GRUPO_MATERIAL     (3 levels)
```

## Invariants enforced in the database

| # | Invariant | Mechanism |
| --- | --- | --- |
| DB1 | An NF's NE must be `ne_emitida` | Trigger on insert/update |
| DB2 | Every `ITEM_NOTA_EMPENHO.item_ata_id` resolves to the parent `NOTA_EMPENHO.ata_id` | Trigger *(2026-09-02, replaces the old NE-level check)* |
| DB3 | Audit rows are immutable | Privileges + trigger |
| DB4 | An ATA cannot be `encerrada` with non-terminal NEs | Trigger |
| DB5 | Monetary columns are `NUMERIC`, never `FLOAT` | Column types |
| DB6 | `Σ NF.valor` per NE ≤ `Σ ITEM_NOTA_EMPENHO.valor` | Trigger (RN12) *(2026-09-02)* |
| DB7 | An NE may not leave `demanda` with zero items | Trigger (RN09) *(2026-09-02)* |
| DB8 | A usuario has at most one outstanding `CONVITE` | `UNIQUE INDEX ... WHERE utilizado_em IS NULL AND cancelado_em IS NULL` *(2026-09-10)* |
| DB9 | A `pendente` usuario never carries a credential | `CHECK (status <> 'pendente' OR senha_hash IS NULL)` *(2026-09-10)* |
| DB10 | A `SESSAO` is immutable except for its revocation | Trigger rejecting any update that changes a column other than `revogado_em`/`revogado_motivo` *(2026-09-10, widened: "never un-revoked" left `familia`, `usuario_id`, `refresh_token_hash` and `emitido_em` mutable)* |
| DB11 | A session family belongs to exactly one usuario | Composite FK `SESSAO (familia, usuario_id) → SESSAO_FAMILIA` *(2026-09-10)* |
| DB12 | Anonymisation is complete or refused | `CHECK` on `USUARIO` requiring `nome`, `email`, `senha_hash` and `oidc_subject` all null once `anonimizado_em` is set *(2026-09-10)* |
| DB13 | At least one `ativo` gestor always exists | Trigger on `USUARIO` update, counting with `ORDER BY id FOR UPDATE` so concurrent transactions take locks in a deterministic order; the service also takes `pg_advisory_xact_lock` so the API returns 409 `ULTIMO_GESTOR` instead of a deadlock *(2026-09-10)* |

**On DB13.** It is a cross-row aggregate, so a `CHECK` cannot express it, and a
trigger alone is not enough: two transactions each blocking a different one of
two gestores both see a count of two and both commit. That is write skew, which
snapshot isolation does not prevent. The trigger is the backstop — it stops a
`psql` session too — and the advisory lock in the service is what serialises the
API path so the specified 409 is what the caller sees. Neither alone suffices.

Application-level enforcement is the first line, not the only one. Every rule an
auditor may one day rely on is also expressed where a buggy migration script or
a well-meaning `psql` session cannot bypass it.

## What is deliberately absent

- **No `saldo` column anywhere.** ADR-0003.
- **No `estoque` computed or mutated by SIGI.** SIGI is not the system of record
  for physical stock. *(2026-09-02)* It does hold an **imported, dated**
  snapshot — `POSICAO_ESTOQUE_SNAPSHOT` — written only by the importer, with no
  endpoint, service or UI that mutates it, and no `entrada de estoque`
  operation. ADR-0008, accepted by ADR-0009.
- **No `area`/`setor` on USUARIO or INSUMO** — those field names never existed in
  the operation. *(2026-09-02)* RN07's "área de competência" turns out to be two
  axes the data does carry: **unidade** and **grupo de materiais**, both now
  entities. RN07 becomes implementable as a scope on `USUARIO` referencing
  `UNIDADE` and `GRUPO_MATERIAL`. *(2026-09-10)* Those columns land with
  **SPEC-0003**, not SPEC-0001: RN07 restricts which *insumos* a servidor may
  see, and neither reference table exists yet, so a criterion in SPEC-0001 would
  assert nothing observable. OQ-04 resolved, OQ-26.

## Entities required by the operation

*(2026-09-02, ADR-0009)* These were recorded as gaps when the RFC governed
scope. Under ADR-0009 the operational data governs, so they are requirements.
Every field below exists in an export the entity supplies today — see
`data-sources.md`. Attribute lists are the modelling intent; the migrations land
with the specs that adopt them.

### UNIDADE
`id UUID PK`, `codigo_externo VARCHAR UNIQUE` (`unidadeId`, e.g. `289`), `nome`,
`tipo ENUM(ubsf, upa, hospital, ambulatorio, caf, central)`,
`regiao VARCHAR NULL`, `populacao INT NULL`, `equipes JSONB NULL`, `ativo BOOL`.

Every stock and fulfilment row in every export is keyed by `unidadeId`. `regiao`
(`Centro`, `Norte`) comes from `REQUISIÇÃO ENTRE UNIDADES`; `populacao` and the
team composition (ESF, ESB, EMULT, EMAP, EAPP, EMAD) from the CAME dashboard.

### CENTRO_CUSTO
`id UUID PK`, `codigo_externo VARCHAR UNIQUE` (`centroCustoId`), `nome`,
`unidade_id FK → UNIDADE`.

A unidade requests through a centro de custo (`PEDIDO QUINZENAL`,
`CIAD CAME`). Stock and fulfilment are keyed by the pair, not by unidade alone.

### SOLICITACAO
`id UUID PK`, `codigo_externo VARCHAR` (`id` in the source),
`unidade_solicitante_id FK`, `centro_custo_solicitante_id FK`,
`unidade_atendente_id FK`, `cronograma_id FK NULL`,
`tipo ENUM(manual, administrativa)`, `urgente BOOL`,
`status VARCHAR`, `data_cadastro TIMESTAMPTZ`,
`data_autorizacao TIMESTAMPTZ NULL`, `autorizador_id FK NULL`,
`data_aprovacao TIMESTAMPTZ NULL`, `aprovador_id FK NULL`,
`data_finalizado TIMESTAMPTZ NULL`, `finalizador_id FK NULL`,
`valor_solicitado NUMERIC(15,2)`.

**`tipo` inverts the intuitive reading:** `manual` means the request *follows*
the cronograma; `administrativa` means it falls outside it. Source: the entity's
own `HUB` annotation.

Three approval stages, each with its own actor, timestamp and scheduling window.
This is a second state machine, independent of the NE flow.

### ITEM_SOLICITACAO
`id UUID PK`, `solicitacao_id FK`, `insumo_id FK`,
`quantidade_solicitada NUMERIC`, `quantidade_autorizada NUMERIC`,
`quantidade_atendida NUMERIC`, `quantidade_pendente NUMERIC`,
`quantidade_pendente_sem_estoque NUMERIC`,
`valor_unitario NUMERIC(15,4)`, `lote VARCHAR NULL`, `validade DATE NULL`.

**Five quantities, not two.** *Authorised* is a distinct administrative decision
from *fulfilled*, and `quantidade_pendente_sem_estoque` is the one that
separates a supply failure from an administrative refusal — the rupture metric.
A fulfilment rate computed as `atendida ÷ solicitada` would conflate them.

### CRONOGRAMA
`id UUID PK`, `nome VARCHAR` (`CAME 6 2026`), `periodicidade VARCHAR`
(`PEDIDO QUINZENAL`), `unidade_id FK NULL`,
`janela_pedido_inicio DATE`, `janela_pedido_fim DATE`,
`janela_entrega_inicio DATE`, `janela_entrega_fim DATE`.

The delivery calendar described in the 17/08 meeting — first request by day 24 to
receive on the 2nd, second by day 8 to receive on the 16th — and carried in the
export as four scheduling windows per request.

### POSICAO_ESTOQUE_SNAPSHOT
`id UUID PK`, `insumo_id FK`, `unidade_id FK`, `centro_custo_id FK NULL`,
`data_referencia DATE`, `estoque_atual NUMERIC`, `demanda_diaria NUMERIC`,
`demanda_mensal NUMERIC`, `dias_estoque INT`, `curva_abc CHAR(1) NULL`,
`curva_xyz CHAR(1) NULL`, `estoque_minimo NUMERIC NULL`,
`ponto_pedido NUMERIC NULL`, `estoque_maximo NUMERIC NULL`,
`valor_unitario NUMERIC(15,5)`, `importado_em TIMESTAMPTZ`,
`UNIQUE(insumo_id, unidade_id, centro_custo_id, data_referencia)`.

Written **only by the importer** (ADR-0008). No endpoint, service or UI mutates
a row. Values are copied verbatim from DOMS, which computes them; SIGI does not
recalculate. Every surface displaying one shows its `data_referencia`.
Refresh cadence is monthly (OQ-25).

`valor_unitario` carries five decimals because the source does
(`0,00599`); rounding to two would be a 67% error on the smallest items.

### PROCESSO_LICITATORIO
`id UUID PK`, `numero_processo VARCHAR UNIQUE`, `numero_pregao VARCHAR NULL`,
`ano INT`, `objeto TEXT`, `modalidade VARCHAR NULL`,
`canal ENUM(proprio, cincatarina)`, `data_abertura DATE NULL`,
`previsao_homologacao DATE NULL`,
`status ENUM(termo_referencia, construcao_edital, etp_revisado, pgm, sap,
compras, em_licitacao, analise_itens, aguardando_abertura, selecao_fornecedor,
revisando_processo, homologado, finalizado, encerrado, fracassado, deserto,
cancelado)`.

The third status axis. Twelve of the seventeen values in the source's
`STATUS DA ATA` belong here, not on the ATA: a `VENCIDA` ATA whose replacement
pregão is `DESERTO` is operationally different from one `EM LICITAÇÃO`, and the
ATA's own lifecycle cannot express that. `canal` records Cincatarina, through
which some ATAs arrive without the entity running the pregão itself.

### ETAPA_PROCESSO
`id UUID PK`, `processo_id FK`, `etapa ENUM(comunicado, acp, sap, pgm, lct,
publicacao_edital, pregao, propostas, homologacao)`, `ordem SMALLINT`,
`dias_planejado INT NULL`, `dias_real INT NULL`, `concluida_em DATE NULL`.

Nine stages with planned-versus-actual in days, as tracked on page 3 of the CAME
dashboard.

### ITEM_PROCESSO
`id UUID PK`, `processo_id FK`, `insumo_id FK`, `quantidade_estimada NUMERIC`,
`UNIQUE(processo_id, insumo_id)`.

Links an insumo to the process that will replenish it — the basis for "how long
until this item has an ATA again".

### ACAO_ITEM
`id UUID PK`, `insumo_id FK`, `tipo ENUM(fazer_compra, sem_ata, sem_saldo_ata,
ata_vencida, com_estoque, solicitacao_pre_empenho, aguardando_entrega,
aguardando_retorno_sap, aguardando_assinaturas, aguardando_dotacao_aco,
item_do_estado, emprestimo, permuta)`, `descricao TEXT NULL`,
`responsavel_id FK NULL`, `criada_em TIMESTAMPTZ`,
`encerrada_em TIMESTAMPTZ NULL`.

What is being done about a critical item — the difference between a shortage
list and an actionable one. The first eleven values are observed in
`ESTOQUE <3 › STATUS`; `emprestimo` and `permuta` come from the 17/08 meeting,
where borrowing from and swapping with other entities were described as routine
responses. `solicitacao_pre_empenho` shows the NE state machine surfacing here,
so the two are coupled: an open action may reference an NE.

## Relationships added 2026-09-02

```
UNIDADE 1─────* CENTRO_CUSTO
UNIDADE 1─────* SOLICITACAO          (solicitante)
UNIDADE 1─────* POSICAO_ESTOQUE_SNAPSHOT
CRONOGRAMA 1──* SOLICITACAO
SOLICITACAO 1─* ITEM_SOLICITACAO *──1 INSUMO
INSUMO 1──────* POSICAO_ESTOQUE_SNAPSHOT
INSUMO 1──────* ACAO_ITEM
PROCESSO_LICITATORIO 1* ETAPA_PROCESSO
PROCESSO_LICITATORIO 1* ITEM_PROCESSO *1 INSUMO
PROCESSO_LICITATORIO 1* ATA           (a homologated process produces an ATA)
```

## Sequencing

These entities are not one migration. Suggested order, cheapest dependency
first: `GRUPO_MATERIAL` → `UNIDADE`/`CENTRO_CUSTO` →
`POSICAO_ESTOQUE_SNAPSHOT` (unlocks the coverage view, the highest-value
addition) → `SOLICITACAO`/`ITEM_SOLICITACAO` → `PROCESSO_LICITATORIO` and its
children → `ACAO_ITEM`. Each lands with the spec that adopts it; see
`roadmap.md` for the milestone impact, which is not small.
