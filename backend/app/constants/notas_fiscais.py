"""Fixed values of the NF conference (SPEC-0005)."""

from __future__ import annotations

from types import MappingProxyType
from typing import Final

# The four statuses (OQ-12). Mirrors `ck_nota_fiscal_status`.
AGUARDANDO: Final = "aguardando"
EM_CONFERENCIA: Final = "em_conferencia"
APROVADA: Final = "aprovada"
DEVOLVIDA: Final = "devolvida"
NF_STATUS: Final = (AGUARDANDO, EM_CONFERENCIA, APROVADA, DEVOLVIDA)

# A devolvida NF bills nothing, so neither cap counts it (RN12, OQ-46).
COUNTED: Final = frozenset({AGUARDANDO, EM_CONFERENCIA, APROVADA})

# Sent to conference from here; coming back from devolvida re-runs the caps (AC-0005-08).
SENDABLE: Final = frozenset({AGUARDANDO, DEVOLVIDA})

# Corrected only before conference (AC-0005-14).
EDITABLE: Final = frozenset({AGUARDANDO, DEVOLVIDA})

# Quarantine holds an NF still in the conference (AC-0005-13).
QUARANTINABLE: Final = frozenset({AGUARDANDO, EM_CONFERENCIA})

# The NE an NF binds to (DB1, AC-0005-03).
NE_EMITIDA: Final = "ne_emitida"

# Labels for messages, pt-BR, because the servidor reads them.
STATUS_LABEL: Final = MappingProxyType(
    {
        AGUARDANDO: "Aguardando",
        EM_CONFERENCIA: "Em conferência",
        APROVADA: "Aprovada",
        DEVOLVIDA: "Devolvida",
    }
)
QUARENTENA_LABEL: Final = "Quarentena"
LIBERADA_LABEL: Final = "Liberada"

# The `acao` of each audit row (SPEC-0005 §8).
ACAO_REGISTRADA: Final = "nf.registrada"
ACAO_CORRIGIDA: Final = "nf.corrigida"
ACAO_ENVIADA: Final = "nf.enviada"
ACAO_APROVADA: Final = "nf.aprovada"
ACAO_DEVOLVIDA: Final = "nf.devolvida"
ACAO_QUARENTENA: Final = "nf.quarentena_iniciada"
ACAO_LIBERADA: Final = "nf.quarentena_liberada"
ENTIDADE: Final = "nota_fiscal"
