"""Fixed values of ATAs, aditivos and reajustes (SPEC-0002)."""

from __future__ import annotations

import decimal
from types import MappingProxyType
from typing import Final

# Mirrors `ck_ata_status` as migration 0004 leaves it: no `rascunho` (SPEC-0002 v1.2).
ATA_STATUS: Final = ("vigente", "suspensa", "encerrada", "cancelada")

# History, not corrected: an ATA in these is not edited (AC-0002-24).
NOT_EDITABLE_STATUS: Final = frozenset({"encerrada", "cancelada"})

# Mirrors `ck_ata_aditivo_tipo`.
ADITIVO_KINDS: Final = ("valor", "prazo")

# RN15 and RF15: the aditivos of value may not together pass a quarter of what
# was contracted.
ADITIVO_CEILING: Final = decimal.Decimal("0.25")

# Each move: the statuses it leaves from, the status it reaches, and the `acao`
# it records (SPEC-0002 §3.7, AC-0002-22).
MOVES: Final = MappingProxyType(
    {
        "suspender": (frozenset({"vigente"}), "suspensa", "ata.suspensa"),
        "retomar": (frozenset({"suspensa"}), "vigente", "ata.retomada"),
        "encerrar": (frozenset({"vigente", "suspensa"}), "encerrada", "ata.encerrada"),
        "cancelar": (frozenset({"vigente", "suspensa"}), "cancelada", "ata.cancelada"),
    }
)

# The column behind each attribute that an edit can change, for the audit row's
# `dados_anteriores`, whose keys are Portuguese (ADR-0013).
EDITABLE_COLUMN: Final = MappingProxyType(
    {
        "number": "numero",
        "subject": "objeto",
        "organ": "orgao",
        "fornecedor_id": "fornecedor_id",
        "issued_on": "data_emissao",
        "vigencia_inicio": "vigencia_inicio",
        "vigencia_fim": "vigencia_fim",
        "total_value": "valor_total",
        "budget_date": "data_orcamento_planilhado",
        "owner_id": "responsavel_id",
    }
)

# Shown in the refusal of a malformed number (AC-0002-08).
PROCESSO_SEI_FORMAT: Final = "NNNNN.NNNNNN/AAAA-DD"
