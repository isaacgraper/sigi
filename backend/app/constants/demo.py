"""The fictitious sample `seed-demo` loads on a development install.

Every name, code and CNPJ here is invented; the CNPJs carry valid check digits so
the services accept them, and belong to no company. Dates are offsets from the
day the seed runs, so the alerts and the vigência words always have something to
show.
"""

from __future__ import annotations

from typing import Final

# The ATA whose presence means the sample is already loaded.
DEMO_MARKER_ATA: Final = "DEMO-001/2026"

# Development credentials, refused outside development like the admin's.
DEMO_MEMBERS: Final[tuple[dict[str, str], ...]] = (
    {
        "email": "servidor@sc.gov.br",
        "password": "servidor",  # noqa: S105 - a development credential
        "perfil": "servidor",
        "nome": "Servidora de Demonstração",
        "registro": "DEMO-0001",
    },
    {
        "email": "auditor@sc.gov.br",
        "password": "auditor",  # noqa: S105 - a development credential
        "perfil": "auditor",
        "nome": "Auditor de Demonstração",
        "registro": "DEMO-0002",
    },
)

# The DOMS hierarchy, three levels deep: grupo, subgrupo, classificação.
DEMO_GRUPOS: Final[dict[str, dict[str, tuple[str, ...]]]] = {
    "MATERIAL ODONTOLÓGICO": {
        "RESTAURADORES": ("RESINAS", "IONÔMEROS"),
        "DESCARTÁVEIS ODONTOLÓGICOS": (),
    },
    "MATERIAL MÉDICO HOSPITALAR": {
        "ANTISSÉPTICOS": (),
        "LUVAS": (),
        "SERINGAS E AGULHAS": (),
    },
    "MATERIAL DE EXPEDIENTE": {
        "PAPELARIA": (),
    },
}

# The servidor sees these grupos and those below them (RN07).
DEMO_SERVIDOR_GRUPOS: Final = ("MATERIAL ODONTOLÓGICO",)

# sku, descrição, unidade, grupo path, código DOMS.
DEMO_INSUMOS: Final[tuple[tuple[str, str, str, tuple[str, ...], str], ...]] = (
    (
        "RESA2",
        "RESINA COMPOSTA FOTOPOLIMERIZÁVEL A2 4 G",
        "UN",
        ("MATERIAL ODONTOLÓGICO", "RESTAURADORES", "RESINAS"),
        "90101",
    ),
    (
        "RESA3",
        "RESINA COMPOSTA FOTOPOLIMERIZÁVEL A3 4 G",
        "UN",
        ("MATERIAL ODONTOLÓGICO", "RESTAURADORES", "RESINAS"),
        "90102",
    ),
    (
        "IONVID",
        "CIMENTO DE IONÔMERO DE VIDRO RESTAURADOR KIT",
        "KIT",
        ("MATERIAL ODONTOLÓGICO", "RESTAURADORES", "IONÔMEROS"),
        "90110",
    ),
    (
        "SUGSAL",
        "SUGADOR DE SALIVA DESCARTÁVEL PACOTE 40",
        "PCT",
        ("MATERIAL ODONTOLÓGICO", "DESCARTÁVEIS ODONTOLÓGICOS"),
        "90120",
    ),
    (
        "CLORDEG21",
        "CLOREXIDINA DEGERMANTE 2% 1 L",
        "UN",
        ("MATERIAL MÉDICO HOSPITALAR", "ANTISSÉPTICOS"),
        "26829",
    ),
    (
        "ALC70",
        "ÁLCOOL ETÍLICO 70% 1 L",
        "UN",
        ("MATERIAL MÉDICO HOSPITALAR", "ANTISSÉPTICOS"),
        "26830",
    ),
    (
        "LUVPROCM",
        "LUVA DE PROCEDIMENTO LÁTEX M CAIXA 100",
        "CX",
        ("MATERIAL MÉDICO HOSPITALAR", "LUVAS"),
        "31001",
    ),
    (
        "LUVPROCG",
        "LUVA DE PROCEDIMENTO LÁTEX G CAIXA 100",
        "CX",
        ("MATERIAL MÉDICO HOSPITALAR", "LUVAS"),
        "31002",
    ),
    (
        "SER5D",
        "SERINGA DESCARTÁVEL 5 ML SEM AGULHA",
        "UN",
        ("MATERIAL MÉDICO HOSPITALAR", "SERINGAS E AGULHAS"),
        "32005",
    ),
    (
        "AGU2513",
        "AGULHA HIPODÉRMICA 25 X 0,7 MM",
        "UN",
        ("MATERIAL MÉDICO HOSPITALAR", "SERINGAS E AGULHAS"),
        "32013",
    ),
    (
        "PAPA4",
        "PAPEL SULFITE A4 75 G RESMA 500",
        "RESMA",
        ("MATERIAL DE EXPEDIENTE", "PAPELARIA"),
        "40001",
    ),
    (
        "CANAZ",
        "CANETA ESFEROGRÁFICA AZUL CAIXA 50",
        "CX",
        ("MATERIAL DE EXPEDIENTE", "PAPELARIA"),
        "40010",
    ),
)

# CANAZ leaves the catalogue, and RESA3 is replaced by RESA2 (AC-0003-14, -15).
DEMO_DISCONTINUED: Final = ("CANAZ",)
DEMO_SUBSTITUTIONS: Final = (("RESA3", "RESA2"),)

# Fictitious fornecedores with valid check digits.
DEMO_FORNECEDORES: Final[dict[str, tuple[str, str]]] = {
    "odonto": ("90.456.123/0001-24", "Odonto Sul Distribuidora Ltda"),
    "hospitalar": ("87.123.456/0001-27", "MedSul Produtos Hospitalares Ltda"),
    "papelaria": ("76.543.210/0001-98", "Papelaria Catarinense Ltda"),
    "luvas": ("65.498.732/0001-07", "Proteção Luvas S.A."),
}

# number, objeto, fornecedor, start and end of vigência in days from today,
# valor total, orçamento in days from today, then the lifecycle move, if any.
DEMO_ATAS: Final[tuple[tuple[str, str, str, int, int, str, int, str | None], ...]] = (
    (
        DEMO_MARKER_ATA,
        "Material odontológico restaurador",
        "odonto",
        -200,
        165,
        "48500.00",
        -210,
        None,
    ),
    (
        "DEMO-002/2026",
        "Antissépticos e material hospitalar",
        "hospitalar",
        -330,
        20,
        "126000.00",
        -350,
        None,
    ),
    ("DEMO-003/2025", "Luvas de procedimento", "luvas", -400, -5, "58000.00", -420, None),
    ("DEMO-004/2026", "Material de expediente", "papelaria", -60, 300, "9800.00", -70, None),
    ("DEMO-005/2025", "Seringas e agulhas", "hospitalar", -500, -130, "34000.00", -520, "encerrar"),
    (
        "DEMO-006/2026",
        "Material odontológico descartável",
        "odonto",
        -30,
        330,
        "12000.00",
        -40,
        "suspender",
    ),
)

# ATA number, sku, item number, quantidade, valor unitário, own fornecedor key.
DEMO_ITEMS: Final[tuple[tuple[str, str, str, str, str, str | None], ...]] = (
    (DEMO_MARKER_ATA, "RESA2", "1", "1200", "18.90000", None),
    (DEMO_MARKER_ATA, "IONVID", "2", "300", "74.35000", None),
    (DEMO_MARKER_ATA, "SUGSAL", "3", "800", "6.12500", None),
    ("DEMO-002/2026", "CLORDEG21", "1", "4000", "12.45000", None),
    ("DEMO-002/2026", "ALC70", "2", "6000", "7.98000", None),
    ("DEMO-002/2026", "SER5D", "3", "250000", "0.00599", None),
    ("DEMO-002/2026", "AGU2513", "4", "120000", "0.08750", None),
    ("DEMO-002/2026", "LUVPROCM", "5", "900", "29.90000", "luvas"),
    ("DEMO-003/2025", "LUVPROCM", "1", "1200", "28.50000", None),
    ("DEMO-003/2025", "LUVPROCG", "2", "800", "28.50000", None),
    ("DEMO-004/2026", "PAPA4", "1", "300", "26.90000", None),
    ("DEMO-006/2026", "SUGSAL", "1", "1500", "6.05000", None),
)

# ATA number, sku of the item, quantidade acrescida.
DEMO_QUANTITY_ADITIVOS: Final = ((DEMO_MARKER_ATA, "RESA2", "200"),)
# ATA number, valor acrescido.
DEMO_VALUE_ADITIVOS: Final = (("DEMO-002/2026", "15000.00"),)
# ATA number, processo SEI, requested days from today.
DEMO_REAJUSTES: Final = (("DEMO-002/2026", "00412.005120/2026-07", -15),)

# ATA number, processo SEI, the stage it is walked to, and (sku, quantidade) of each line.
DEMO_NES: Final[tuple[tuple[str, str, str, tuple[tuple[str, str], ...]], ...]] = (
    (DEMO_MARKER_ATA, "00301.000451/2026-12", "pre_empenho", (("RESA2", "300"),)),
    (
        "DEMO-002/2026",
        "00301.000502/2026-31",
        "ne_emitida",
        (("CLORDEG21", "1000"), ("ALC70", "500")),
    ),
    ("DEMO-002/2026", "00301.000517/2026-08", "validacao_saldo", (("SER5D", "50000"),)),
    ("DEMO-004/2026", "00301.000533/2026-44", "demanda", (("PAPA4", "50"),)),
)
# The números the financial system would have issued, typed in at their stage.
DEMO_NUMERO_PRE_EMPENHO: Final = "2026PE{:06d}"
DEMO_NUMERO_NE: Final = "2026NE{:06d}"

DEMO_JUSTIFICATION: Final = "Dado fictício de demonstração."
