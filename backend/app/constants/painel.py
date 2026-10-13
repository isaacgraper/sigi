"""Fixed values of the dashboard, the stakeholders' CAME report (SPEC-0012)."""

from __future__ import annotations

from types import MappingProxyType
from typing import Final

# Each section's block ids, in the report's order (§7). They are the keys of
# `blocks` in `frontend/lib/dashboard/constants.ts`.
SECTIONS: Final = MappingProxyType(
    {
        "atendimento": ("mercadorias", "unidades", "grafico"),
        "consumo": ("estoque", "grafico"),
        "processos": (
            "abertura",
            "novo_processo",
            "previsao",
            "status",
            "nova_data",
            "progresso",
            "vigente",
            "vencimento",
            "sem_processo",
            "etapas",
            "itens",
        ),
        "itens-em-falta": (
            "sku",
            "estoque",
            "consumo_mes",
            "informacoes",
            "sugestoes",
            "grupos",
            "curva_abc",
            "disponibilidade",
            "materiais",
        ),
    }
)
