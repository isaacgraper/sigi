"""Demonstration figures for the dashboard (SPEC-0012 AC-0012-13).

Invented, in the shape and the ranges of the stakeholders' CAME report, so the
screen can be shown before SIGI holds the entity's data. No name, code or CNPJ
here belongs to the entity. Served only when `DASHBOARD_DEMO` is on, which the
settings refuse outside development (AC-0012-14).

Formats follow SPEC-0012 §7: tables and tiles carry pt-BR display text, charts
carry raw numbers as text. Saldo and Estoque are separate figures (invariant 5),
and every estoque figure names the date of its position (ADR-0008).
"""

from __future__ import annotations

POSICAO = "Posição de 01/10/2026"

MONTHS = [
    ("Mai/25", 2_109_400, 2_119_281, 1_918_220),
    ("Jun/25", 2_231_870, 2_207_565, 1_851_340),
    ("Jul/25", 2_180_330, 2_095_702, 1_923_910),
    ("Ago/25", 1_877_150, 1_868_954, 1_672_480),
    ("Set/25", 2_471_220, 2_636_323, 2_389_760),
    ("Out/25", 2_265_910, 2_222_974, 2_041_330),
    ("Nov/25", 1_915_640, 1_877_365, 1_702_190),
    ("Dez/25", 1_918_870, 1_851_141, 1_678_420),
    ("Jan/26", 1_701_330, 1_637_052, 1_503_870),
    ("Fev/26", 1_852_460, 1_778_040, 1_634_210),
    ("Mar/26", 2_138_920, 2_057_324, 1_967_550),
    ("Abr/26", 2_214_770, 2_201_285, 1_942_610),
    ("Mai/26", 1_931_250, 1_885_617, 1_716_340),
    ("Jun/26", 2_141_600, 2_085_307, 1_877_920),
    ("Jul/26", 2_218_480, 2_141_442, 1_961_830),
]
MEDIA_ATUAL = 11_850

UNIDADES = [
    # unidade, ESF, ESB, EMULTI, EMAP, EAPP, EMAD, população, atendido, valor atendido
    ("UPA Sul 24 horas", "-", "-", "-", "-", "-", "-", "-", 2_399_659, "1849934.72"),
    ("UPA Leste 24 horas", "-", "-", "-", "-", "-", "-", "-", 2_078_172, "1619359.58"),
    ("Pronto Atendimento Norte", "-", "-", "-", "-", "-", "-", "-", 1_756_794, "1327123.79"),
    ("Hospital Regional", "-", "-", "-", "2", "-", "-", "-", 961_545, "711711.99"),
    ("UBS Jardim Primavera", "7", "3", "3", "-", "-", "-", "23.408", 789_174, "392620.02"),
    ("UBS Centro", "7", "4", "4", "-", "-", "-", "-", 684_605, "385533.16"),
    ("UBS Vila Nova", "6", "2", "2", "-", "-", "-", "20.471", 654_413, "371208.40"),
    ("UBS Bela Vista", "6", "4", "4", "-", "1", "-", "30.036", 602_426, "348990.11"),
]

MERCADORIAS = [
    ("Abaixador de língua, pacote com 100", "3.872", "3.824", "R$ 17.661,30"),
    ("Abridor de boca adulto", "32", "32", "R$ 116,82"),
    ("Achocolatado em pó", "250", "250", "R$ 2.975,37"),
    ("Ácido peracético 0,09% a 0,31%, galão 5 L", "134", "54", "R$ 6.902,18"),
    ("Açúcar refinado", "2.172", "2.163", "R$ 8.923,74"),
    ("Adaptador de proteção para frasco de soro", "14.355", "14.225", "R$ 8.402,14"),
    ("Adesivo esmalte e dentina", "418", "412", "R$ 33.812,84"),
    ("Água destilada para autoclave", "915", "846", "R$ 9.280,62"),
    ("Água oxigenada 100 ml", "1.177", "1.176", "R$ 2.389,34"),
    ("Agulha descartável hipodérmica 13 x 4,5 mm", "210.990", "199.200", "R$ 11.952,00"),
]

ETAPAS = [
    # etapa, dias planejados, dias reais
    ("Comunicado", 30, 51),
    ("ACP", 60, 97),
    ("SAP-ARC", 30, 20),
    ("PGM", 40, 44),
    ("LCT construção de edital", 30, 18),
    ("Publicação do edital", 30, 21),
    ("Pregão", 30, 13),
    ("Propostas / amostras", 30, 35),
    ("Homologação", 30, 9),
]

ITENS_PROCESSO = [
    (
        "2024",
        "1",
        "Fita autocolante para protocolo de Manchester, amarela",
        "Protocolo Manchester",
        "-",
    ),
    (
        "2024",
        "2",
        "Fita autocolante para protocolo de Manchester, azul",
        "Protocolo Manchester",
        "-",
    ),
    (
        "2024",
        "3",
        "Fita autocolante para protocolo de Manchester, verde",
        "Protocolo Manchester",
        "-",
    ),
    ("2024", "7", "Pulseira de identificação, risco de queda", "Protocolo Manchester", "-"),
    (
        "2025",
        "2",
        "Fecho de contato fêmea e macho, 50 mm",
        "Imobilização pré-hospitalar",
        "Em andamento",
    ),
    (
        "2025",
        "13",
        "Colete de imobilização, tamanho M",
        "Imobilização pré-hospitalar",
        "Em andamento",
    ),
    ("2025", "2", "Ácido peracético 0,09% a 0,31%, 5 L", "Químicos e saneantes", "Em andamento"),
]

GRUPOS = [
    ("Uniformes e materiais de apoio", "2025", "26.0.000744-2", "15/12/2026", "467"),
    ("Agulhas, seringas e correlatos", "2025", "26.0.000014-0", "18/11/2025", "-"),
    ("Químicos e saneantes", "2025", "25.0.000675-2", "15/06/2026", "-"),
    ("Descartáveis e dispensers", "2025", "26.0.000912-8", "26/10/2026", "122"),
    ("Curativos especiais", "2025", "26.0.000874-4", "21/08/2026", "-"),
    ("Fios cirúrgicos", "2025", "26.0.000569-5", "29/09/2026", "120"),
]

MATERIAIS = [
    # material, emp. abertos, dias estoque, status item, pregão, SEI, validade,
    # saldo, status do pregão, status da ATA, classificação, estoque ideal
    (
        "Bota de Unna 10,16 cm x 9,14 m",
        "1 empenho",
        "155",
        "Aguardando entrega",
        "456/2024",
        "25159676",
        "15/04/2026",
        "-",
        "Finalizado",
        "Vencida",
        "A",
        "892",
    ),
    (
        "Atadura de crepom 10 cm",
        "-",
        "147",
        "Com estoque",
        "071/2025",
        "26135475",
        "21/07/2027",
        "72.000",
        "Finalizado",
        "Prorrogada",
        "A",
        "83.316",
    ),
    (
        "Lençol de TNT descartável com elástico",
        "-",
        "298",
        "Aguardando dotação",
        "071/2025",
        "26798105",
        "17/09/2026",
        "75.000",
        "Finalizado",
        "Vigente",
        "A",
        "11.991",
    ),
    (
        "Seringa descartável 10 ml com dispositivo de segurança",
        "-",
        "329",
        "Com estoque",
        "389/2025",
        "27510350",
        "19/11/2026",
        "342.880",
        "Finalizado",
        "Vigente",
        "A",
        "113.125",
    ),
    (
        "Atadura de crepom 15 cm",
        "-",
        "196",
        "Sem ATA",
        "013/2025",
        "25876466",
        "02/06/2026",
        "-",
        "Finalizado",
        "Vencida",
        "A",
        "80.870",
    ),
]


DEMO: dict[str, dict[str, list[list[str]]]] = {
    "atendimento": {
        "mercadorias": [list(row) for row in MERCADORIAS],
        "unidades": [
            [nome, esf, esb, emulti, emap, eapp, emad, pop, f"{atendido:,}".replace(",", ".")]
            for nome, esf, esb, emulti, emap, eapp, emad, pop, atendido, _ in UNIDADES
        ],
        "grafico": [[row[0], str(row[8]), row[9]] for row in UNIDADES],
    },
    "consumo": {
        "estoque": [["32.693", POSICAO]],
        "grafico": [
            [mes, str(sol), str(aut), str(ate), str(MEDIA_ATUAL)] for mes, sol, aut, ate in MONTHS
        ],
    },
    "processos": {
        "abertura": [["21/05/2026"]],
        "novo_processo": [["26.0.000014-0"]],
        "previsao": [["11/04/2025"]],
        "status": [["Processo concluído em 310 dias"]],
        "nova_data": [["-"]],
        "progresso": [["25,59%"]],
        "vigente": [["24.0.000021-8"]],
        "vencimento": [["-"]],
        "sem_processo": [["-"]],
        "etapas": [[nome, str(plan), str(real)] for nome, plan, real in ETAPAS],
        "itens": [list(row) for row in ITENS_PROCESSO],
    },
    "itens-em-falta": {
        "sku": [["CALCSEG"]],
        "estoque": [["0", POSICAO]],
        "consumo_mes": [["0"]],
        "informacoes": [["Item com entrega parcial; aguardar a próxima NF."]],
        "sugestoes": [["Atadura de crepom 15 cm"]],
        "grupos": [list(row) for row in GRUPOS],
        "curva_abc": [["A", "10"], ["B", "10"], ["C", "80"]],
        "disponibilidade": [["Disponível", "63.6"], ["Em falta", "32.1"], ["Baixo estoque", "4.3"]],
        "materiais": [list(row) for row in MATERIAIS],
    },
}
