"""Fixed values of the reports and their exports (SPEC-0009)."""

from __future__ import annotations

from types import MappingProxyType
from typing import Final

# The four reports of RF12, by the name the route takes (§2.1).
EXECUCAO_ORCAMENTARIA: Final = "execucao-orcamentaria"
POSICAO_SALDO: Final = "posicao-saldo"
NFS_EM_CONFERENCIA: Final = "notas-fiscais-em-conferencia"
INDICADORES_FORNECEDORES: Final = "indicadores-fornecedores"

# Titles and columns, pt-BR, because the auditor reads them in the file.
TITLES: Final = MappingProxyType(
    {
        EXECUCAO_ORCAMENTARIA: "Execução orçamentária por ATA",
        POSICAO_SALDO: "Posição de saldo consolidada",
        NFS_EM_CONFERENCIA: "Notas fiscais em conferência",
        INDICADORES_FORNECEDORES: "Indicadores de fornecedores",
    }
)
# Each column by the key `colunas` names it with and the title the file prints (§2.1).
COLUMNS: Final = MappingProxyType(
    {
        EXECUCAO_ORCAMENTARIA: (
            ("ata", "ATA"),
            ("fornecedor", "Fornecedor"),
            ("processo_sei", "Processo SEI"),
            ("numero_pre_empenho", "Pré-empenho"),
            ("ne", "NE"),
            ("stage", "Etapa"),
            ("value", "Valor"),
            ("issued_on", "Data de emissão"),
        ),
        POSICAO_SALDO: (
            ("ata", "ATA"),
            ("fornecedor", "Fornecedor"),
            ("status", "Situação"),
            ("vigencia_fim", "Fim da vigência"),
            ("valor_contratado", "Valor contratado"),
            ("valor_reservado", "Valor reservado"),
            ("valor_empenhado", "Valor empenhado"),
            ("saldo_disponivel", "Saldo disponível"),
            ("comprometimento_percentual", "Comprometimento (%)"),
            ("alto_consumo", "Alto consumo"),
        ),
        NFS_EM_CONFERENCIA: (
            ("nf", "NF"),
            ("fornecedor", "Fornecedor"),
            ("ne", "NE"),
            ("ata", "ATA"),
            ("issued_on", "Data de emissão"),
            ("value", "Valor"),
        ),
        INDICADORES_FORNECEDORES: (
            ("fornecedor", "Fornecedor"),
            ("cnpj", "CNPJ"),
            ("atas", "ATAs"),
            ("valor_contratado", "Valor contratado"),
            ("valor_empenhado", "Valor empenhado"),
            ("nfs_lancadas", "NFs lançadas"),
            ("nfs_aprovadas", "NFs aprovadas"),
            ("nfs_devolvidas", "NFs devolvidas"),
            ("valor_aprovado", "Valor aprovado"),
        ),
    }
)

FORMAT_CSV: Final = "csv"
FORMAT_PDF: Final = "pdf"
MEDIA_TYPES: Final = MappingProxyType(
    {FORMAT_CSV: "text/csv; charset=utf-8", FORMAT_PDF: "application/pdf"}
)

# Excel in pt-BR opens this without an import wizard (AC-0009-06).
CSV_BOM: Final = "﻿"
CSV_SEPARATOR: Final = ";"
CSV_LINE_END: Final = "\r\n"
# A text cell starting with one of these is run as a formula by a spreadsheet.
CSV_FORMULA_PREFIXES: Final = ("=", "+", "-", "@", "\t", "\r")
CSV_FORMULA_GUARD: Final = "'"

# The provenance every export opens with (AC-0009-02).
HEADER_REPORT: Final = "Relatório"
HEADER_ID: Final = "Identificador"
HEADER_GENERATED: Final = "Gerado em"
HEADER_USER: Final = "Gerado por"
HEADER_REFERENCE: Final = "Data de referência"
HEADER_PERIOD: Final = "Período"
HEADER_FILTERS: Final = "Filtros"
PERIOD_UNTIL: Final = "Até a data de referência"
PERIOD_BETWEEN: Final = "De {start} até {end}"
NO_FILTER: Final = "Nenhum"
FILTER_ATA: Final = "ATA"
UNNAMED_USER: Final = "Usuário sem nome"
INSTANT_FORMAT: Final = "%d/%m/%Y %H:%M:%S"
DATE_FORMAT: Final = "%d/%m/%Y"
FILE_STAMP_FORMAT: Final = "%Y%m%d-%H%M%S"
FILE_PREFIX: Final = "sigi"

YES: Final = "Sim"
NO: Final = "Não"
ATA_STATUS_LABEL: Final = MappingProxyType(
    {
        "vigente": "Vigente",
        "suspensa": "Suspensa",
        "encerrada": "Encerrada",
        "cancelada": "Cancelada",
    }
)

# The audit row of an export (AC-0009-04).
ACAO_EXPORTADO: Final = "relatorio.exportado"
ENTIDADE: Final = "relatorio"

# The `dados_anteriores` keys a state at the reference is read from (§2.2).
KEY_STATUS: Final = "status"
KEY_VALOR_TOTAL: Final = "valor_total"
KEY_VIGENCIA_FIM: Final = "vigencia_fim"
KEY_ITENS: Final = "itens"
KEY_NUMERO_PRE_EMPENHO: Final = "numero_pre_empenho"
KEY_NUMERO: Final = "numero"
KEY_VALOR: Final = "valor"
KEY_DATA_EMISSAO: Final = "data_emissao"
REWOUND_ENTIDADES: Final = ("ata", "nota_empenho", "nota_fiscal")

# The PDF page: A4 on its side, so ten columns fit.
PDF_ORIENTATION: Final = "L"
PDF_FONT: Final = "Helvetica"
PDF_TITLE_SIZE: Final = 14
PDF_TEXT_SIZE: Final = 8
PDF_LINE_HEIGHT: Final = 5
# The core PDF fonts cover this charset only; pt-BR fits in it.
PDF_ENCODING: Final = "latin-1"

# Messages, pt-BR, because the auditor reads them.
FORMAT_UNKNOWN: Final = "Informe csv ou pdf."
REFERENCE_IN_FUTURE: Final = "A data de referência não pode estar no futuro."
COLUMNS_UNKNOWN: Final = "Informe colunas deste relatório: {columns}."
START_AFTER_REFERENCE: Final = "O início não pode ser posterior à data de referência."
START_NOT_APPLICABLE: Final = "A posição de saldo não tem período: é lida na data de referência."
