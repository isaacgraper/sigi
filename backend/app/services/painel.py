"""The dashboard's read model: the stakeholders' CAME report (SPEC-0012).

Every block answers with no rows today, because none of its sources exists yet
(SPEC-0012 §3): no DOMS import, no insumo, no NE, NF or processo licitatório.
The spec that brings a source fills its blocks here, and the contract in §7
does not change. The block ids are the keys of `frontend/lib/dashboard.ts`.
"""

from __future__ import annotations

from app.services.errors import SectionNotFound

SECTIONS: dict[str, tuple[str, ...]] = {
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


def read(section: str) -> dict[str, list[list[str]]]:
    """Return every block of `section` with its rows (AC-0012-12).

    Raises:
        SectionNotFound: when the dashboard has no such section.
    """
    blocks = SECTIONS.get(section)
    if blocks is None:
        raise SectionNotFound()
    return {block: [] for block in blocks}
