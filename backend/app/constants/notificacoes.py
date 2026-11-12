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
ACAO_ENVIADA: Final = "notificacao.enviada"
ACAO_ENVIO_FALHOU: Final = "notificacao.envio_falhou"

# Mirrors api-conventions.md.
PAGE_SIZE_MAX: Final = 100

# The digest (AC-0008-06). pt-BR, because the member reads it.
DIGEST_SUBJECT: Final = "SIGI: {count} aviso(s) de ATAs"
DIGEST_GREETING: Final = "Olá, {name}."
DIGEST_GREETING_UNNAMED: Final = "Olá."
DIGEST_INTRO: Final = "Estas ATAs pedem atenção desde o último resumo:"
DIGEST_LINE: Final = "- ATA {numero}: {detalhe} {link}"
DIGEST_FOOTER: Final = "Os avisos também estão no sino do SIGI."
DIGEST_DETAIL: Final = MappingProxyType(
    {
        VAI_VENCER: "vence em {fim}",
        VENCEU: "venceu em {fim}",
        SALDO_80: "{percentual}% do saldo comprometido",
        SALDO_ESGOTADO: "saldo esgotado",
        REAJUSTE: "reajuste a pedir desde {data}",
    }
)
DATE_FORMAT: Final = "%d/%m/%Y"
MAIL_FILE_STAMP: Final = "%Y%m%d-%H%M%S"
PRODUCTION: Final = "production"
