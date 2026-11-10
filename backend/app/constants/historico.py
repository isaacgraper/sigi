"""Fixed values of the history reads (SPEC-0007)."""

from __future__ import annotations

from types import MappingProxyType
from typing import Final

# Every `entidade_tipo` a row is written with, so a filter on any other is a typo.
ENTIDADE_TIPOS: Final = frozenset(
    {
        "usuario",
        "rota",
        "ata",
        "fornecedor",
        "insumo",
        "grupo_material",
        "nota_empenho",
        "nota_fiscal",
    }
)

# ATA rows carry the item they touch under this key (SPEC-0003 §8).
ATA_ENTIDADE: Final = "ata"
NOTA_EMPENHO_ENTIDADE: Final = "nota_empenho"
NOTA_FISCAL_ENTIDADE: Final = "nota_fiscal"
ITEM_ATA_KEY: Final = "item_ata_id"

# The stage of the cycle a row belongs to (AC-0007-07).
ETAPA_ATA: Final = "ata"
ETAPA_ITEM_ATA: Final = "item_ata"
ETAPA_NOTA_EMPENHO: Final = "nota_empenho"
ETAPA_NOTA_FISCAL: Final = "nota_fiscal"

# Two rows written in the same instant read in the order of the cycle.
ETAPA_RANK: Final = MappingProxyType(
    {ETAPA_ATA: 0, ETAPA_ITEM_ATA: 1, ETAPA_NOTA_EMPENHO: 2, ETAPA_NOTA_FISCAL: 3}
)

# Filter messages, pt-BR, because the auditor reads them under the input.
PERIODO_INVERTIDO: Final = "A data inicial deve ser anterior ou igual à final."
ENTIDADE_SEM_TIPO: Final = "Informe o tipo da entidade."
TIPO_DESCONHECIDO: Final = "Tipo de entidade desconhecido."
