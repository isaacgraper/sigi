"""Fixed values of the ATA notices (SPEC-0008)."""

from __future__ import annotations

from types import MappingProxyType
from typing import Final

# The reasons a notice is raised for an ATA (AC-0008-01), as stored in `motivo`.
VAI_VENCER: Final = "vai_vencer"
VENCEU: Final = "venceu"
SALDO_80: Final = "saldo_80"
SALDO_ESGOTADO: Final = "saldo_esgotado"
REAJUSTE: Final = "reajuste"
MOTIVOS: Final = (VAI_VENCER, VENCEU, SALDO_80, SALDO_ESGOTADO, REAJUSTE)

# pt-BR, because the member reads it under the bell and in the e-mail.
MOTIVO_ROTULO: Final = MappingProxyType(
    {
        VAI_VENCER: "Vai vencer",
        VENCEU: "Venceu",
        SALDO_80: "Saldo em 80%",
        SALDO_ESGOTADO: "Saldo esgotado",
        REAJUSTE: "Reajuste a pedir",
    }
)

ATA_VIGENTE: Final = "vigente"
ENTIDADE: Final = "notificacao"
ACAO_CRIADA: Final = "notificacao.criada"
ACAO_LIDA: Final = "notificacao.lida"
ACAO_TODAS_LIDAS: Final = "notificacao.todas_lidas"

# Mirrors api-conventions.md.
PAGE_SIZE_MAX: Final = 100

# ── The e-mail summary (AC-0008-06 to -11) ──────────────────────────────────

DIARIO: Final = "diario"
SEMANAL: Final = "semanal"
NENHUM: Final = "nenhum"
FREQUENCIAS: Final = (DIARIO, SEMANAL, NENHUM)
# A member who never chose receives it weekly, on Mondays (AC-0008-07).
DEFAULT_FREQUENCIA: Final = SEMANAL
DEFAULT_DIA_SEMANA: Final = 1
WEEK_DAYS: Final = 7

PREFERENCIA_ENTIDADE: Final = "usuario"
ACAO_PREFERENCIA: Final = "preferencia_email.alterada"
RESUMO_ENTIDADE: Final = "resumo"
ACAO_RESUMO_ENVIADO: Final = "resumo.enviado"
ACAO_RESUMO_FALHOU: Final = "resumo.envio_falhou"

FREQUENCIA_INVALIDA: Final = "Escolha diário, semanal ou nenhum."
DIA_INVALIDO: Final = "Escolha um dia da semana."

# The fixed template (AC-0008-06), pt-BR, because the member reads it.
SUBJECT: Final = "SIGI: resumo de {dia}"
GREETING: Final = "Olá, {name}."
GREETING_UNNAMED: Final = "Olá."
INTRO: Final = "Este é o resumo do SIGI de {dia}."
SECTION_ATAS: Final = "ATAs"
SECTION_NES: Final = "Notas de empenho"
SECTION_NFS: Final = "Notas fiscais"
NONE_LINE: Final = "- Nenhuma."
ATA_LINE: Final = "- ATA {numero}: {detalhe} {link}"
ATA_DETAIL: Final = MappingProxyType(
    {
        VAI_VENCER: "vence em {fim}",
        VENCEU: "venceu em {fim}",
        SALDO_80: "{percentual}% do saldo comprometido",
        SALDO_ESGOTADO: "saldo esgotado",
        REAJUSTE: "reajuste a pedir desde {data}",
    }
)
NE_STAGE_LINE: Final = "- {etapa}: {count}"
NE_ADVANCED_LINE: Final = "- Avançaram de etapa desde o último resumo: {count}"
NF_LINE: Final = "- {rotulo}: {count}"
NF_COUNTS: Final = (
    ("em_conferencia", "Em conferência"),
    ("devolvida", "Devolvidas"),
    ("quarentena", "Em quarentena"),
)
NE_ADVANCE_ACAO: Final = "ne.avancada"
FOOTER: Final = "Para mudar a frequência deste e-mail, abra Configurações no SIGI: {link}"
DATE_FORMAT: Final = "%d/%m/%Y"
MAIL_FILE_STAMP: Final = "%Y%m%d-%H%M%S"
PRODUCTION: Final = "production"
