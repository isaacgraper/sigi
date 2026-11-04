"""Fixed values of the NE flow (SPEC-0004) and of saldo (SPEC-0006)."""

from __future__ import annotations

import decimal
import re
from types import MappingProxyType
from typing import Final

# The five stages in their order (RN08), then the one exit. Mirrors `ck_nota_empenho_status`.
STAGES: Final = ("demanda", "validacao_saldo", "pre_empenho", "envio_fornecedor", "ne_emitida")
CANCELADA: Final = "cancelada"
NE_STATUS: Final = (*STAGES, CANCELADA)
TERMINAL: Final = frozenset({"ne_emitida", CANCELADA})
NE_IN_PROGRESS: Final = frozenset(set(STAGES) - TERMINAL)

# Saldo counts an NE from the first stage past the guard (ADR-0015, RN17).
RESERVING: Final = frozenset({"pre_empenho", "envio_fornecedor"})
COMMITTED: Final = frozenset({"ne_emitida"})

# The itens may be replaced only before saldo is reserved (AC-0004-22).
ITEMS_EDITABLE: Final = frozenset({"demanda", "validacao_saldo"})

# An item referenced by an NE in these is locked (AC-0004-27). A cancelled NE
# releases it.
LOCKS_ITEM: Final = frozenset({"validacao_saldo", "pre_empenho", "envio_fornecedor", "ne_emitida"})

# The item fields an NE locks (AC-0004-27).
LOCKED_ITEM_FIELDS: Final = frozenset({"insumo_id", "quantity", "unit_price"})

# The ATA figures an NE emitida locks (AC-0004-26).
LOCKED_ATA_FIELDS: Final = frozenset(
    {"number", "fornecedor", "vigencia_inicio", "vigencia_fim", "total_value", "budget_date"}
)

# Both números are typed in as the financial system issues them (§9).
NUMERO_PATTERN: Final = re.compile(r"^[A-Za-z0-9]{1,20}$")

# RF14: the commitment that flags an ATA.
ALTO_CONSUMO: Final = decimal.Decimal("80")

# The empty sum, so a saldo with no NE adds Decimals, never ints.
ZERO: Final = decimal.Decimal("0")

# Labels for messages, pt-BR, because the servidor reads them.
STAGE_LABEL: Final = MappingProxyType(
    {
        "demanda": "Demanda",
        "validacao_saldo": "Validação de saldo",
        "pre_empenho": "Pré-empenho",
        "envio_fornecedor": "Envio ao fornecedor",
        "ne_emitida": "NE emitida",
        "cancelada": "Cancelada",
    }
)

# The `acao` of each audit row (SPEC-0004 §8).
ACAO_CRIADA: Final = "ne.criada"
ACAO_ITENS: Final = "ne.itens_alterados"
ACAO_AVANCADA: Final = "ne.avancada"
ACAO_REVERTIDA: Final = "ne.revertida"
ACAO_CANCELADA: Final = "ne.cancelada"
ACAO_BLOQUEADA: Final = "ne.bloqueada"
ENTIDADE: Final = "nota_empenho"
