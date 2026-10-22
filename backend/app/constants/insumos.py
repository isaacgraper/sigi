"""Fixed values of the insumo catalogue, its grupos and the items of an ATA (SPEC-0003)."""

from __future__ import annotations

import decimal
import re
from types import MappingProxyType
from typing import Final

# ── Codes ───────────────────────────────────────────────────────────────────

# The DOMS client code is digits only (AC-0003-02). `2888.0` is how some source
# files spell it, and it is refused rather than trimmed.
DOMS_CODE_PATTERN: Final = re.compile(r"^[0-9]+$")

# Shown in the refusal of a malformed SKU, beside the pattern (RF07).
SKU_EXAMPLE: Final = "CLORDEG21"

# ── Grupos de materiais ─────────────────────────────────────────────────────

# Grupo → subgrupo → classificação, the three levels of the DOMS hierarchy
# (data-sources.md §5). Mirrors `ck_grupo_material_nivel`.
GRUPO_MAX_LEVEL: Final = 3

# ── The insumo ──────────────────────────────────────────────────────────────

# Derived, never stored (AC-0003-12): from `substituido_por_id` and `descontinuado_em`.
INSUMO_STATUS: Final = ("ativo", "descontinuado", "substituido")

# The column behind each attribute an edit can change, for `dados_anteriores`,
# whose keys are Portuguese (ADR-0013).
INSUMO_EDITABLE_COLUMN: Final = MappingProxyType(
    {
        "description": "descricao",
        "unit": "unidade",
        "grupo_id": "grupo_id",
        "codigo_doms": "codigo_doms",
        "external_code": "codigo_externo",
        "reference_quantity": "quantidade_referencia",
    }
)

# ── The items of an ATA ─────────────────────────────────────────────────────

# ADR-0016: an item's value is rounded once, half up, to this.
CENTAVO: Final = decimal.Decimal("0.01")

# ADR-0016: only the unit price keeps five places; a quantity keeps three.
UNIT_PRICE_PLACES: Final = 5
QUANTITY_PLACES: Final = 3

ITEM_EDITABLE_COLUMN: Final = MappingProxyType(
    {
        "insumo_id": "insumo_id",
        "quantity": "quantidade",
        "unit_price": "valor_unitario",
        "item_number": "numero_item",
        "fornecedor_id": "fornecedor_id",
    }
)

# ── Imports ─────────────────────────────────────────────────────────────────

CATALOGUE_REQUIRED: Final = ("sku", "descricao", "unidade", "grupo")
CATALOGUE_OPTIONAL: Final = (
    "subgrupo",
    "classificacao",
    "codigo_doms",
    "codigo_externo",
    "quantidade_referencia",
)

ITEMS_REQUIRED: Final = ("sku", "quantidade", "valor_unitario")
ITEMS_OPTIONAL: Final = ("numero_item", "cnpj_fornecedor", "razao_social_fornecedor")

# A column the catalogue ignores, with the note the report gives for it, so an
# operator does not conclude the data was lost (AC-0003-06, §4).
IGNORED_COLUMN_NOTES: Final = MappingProxyType(
    {
        "estoque": "A coluna estoque não entra no catálogo: o estoque é lido pela importação"
        " de cobertura, com a data de referência.",
    }
)

# `26829 - CLOREXIDINA 2% - 1 L`: the DOMS code typed into the descrição
# (data-sources.md §12).
EMBEDDED_CODE: Final = re.compile(r"^(\d+)\s*-\s*(\S.*)$")

# `2888.0`: a code exported as a float (data-sources.md §12).
FLOAT_CODE: Final = re.compile(r"^\d+[.,]\d+$")

# A control character, a tab or a line break inside a cell: none belongs in a
# code or a descrição, and each breaks an export (AC-0003-34).
CONTROL_CHARACTER: Final = re.compile(r"[\x00-\x1f\x7f]")

# A cell that starts like a formula runs as one when the data is opened again in
# a spreadsheet (CSV injection, OWASP). "-" stays allowed: descrições start with it.
FORMULA_PREFIXES: Final = ("=", "+", "@")

# Excel's two encodings for a Brazilian workstation, tried in this order.
IMPORT_ENCODINGS: Final = ("utf-8-sig", "cp1252")

# Written into the audit row of each insumo or item an import creates or changes.
IMPORT_JUSTIFICATION: Final = "Importado de arquivo CSV."

# The two routes allowed past the 64 KiB body ceiling (SPEC-0001 AC-0001-42 v1.10).
IMPORT_PATHS: Final = re.compile(r"^/api/v1/(insumos|atas/[0-9a-fA-F-]{36}/itens)/importacao$")

# The messages of the import report, one per kind of invalid cell (pt-BR).
IMPORT_MESSAGES: Final = MappingProxyType(
    {
        "required": "Campo obrigatório.",
        "sku": f"SKU inválido. Use só letras e números, como {SKU_EXAMPLE}.",
        "doms": "Código DOMS inválido. Use só números, como 26829.",
        "float_code": "Código escrito como número decimal. Formate a coluna como texto.",
        "embedded_mismatch": "A descrição começa com um código DOMS diferente do informado.",
        "classificacao_without_subgrupo": "Informe o subgrupo antes da classificação.",
        "number": "Número inválido.",
        "positive": "Informe um valor maior que zero.",
        "not_negative": "Informe um valor maior ou igual a zero.",
        "places": "Use no máximo {places} casas decimais.",
        "duplicate_sku": "SKU repetido no arquivo, também na linha {other}.",
        "duplicate_doms": "Código DOMS repetido no arquivo, também na linha {other}.",
        "doms_in_use": "Código DOMS já usado pelo insumo {sku}.",
        "sku_unknown": "SKU não cadastrado no catálogo.",
        "descontinuado": "Insumo descontinuado: não entra em itens novos.",
        "cnpj": "CNPJ inválido.",
        "razao_social": "Informe a razão social para um fornecedor novo.",
        "aditivo": "A quantidade deixa os aditivos acima de 25% do item.",
        "control": "Caractere de controle não permitido.",
        "formula": "O texto não pode começar com =, + ou @.",
    }
)
