#!/usr/bin/env python3
"""
Reproduz as contagens citadas em docs/architecture/data-sources.md e nas
resoluções de docs/open-questions.md.

As planilhas NÃO estão no repositório: contêm CNPJ, e-mail e nome de paciente.
Rode apontando para os arquivos recebidos dos stakeholders.

    python3 scripts/analise-planilhas.py <dir-com-os-xlsx>

Saída: apenas agregados e nomes de coluna. Nunca valores de campos pessoais.
"""
import sys, os, glob
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _xlsx_reader import WB


def find(d, needle):
    hits = [p for p in glob.glob(os.path.join(d, "*.xlsx")) if needle in p]
    if not hits:
        sys.exit(f"não encontrei arquivo contendo {needle!r} em {d}")
    return hits[0]


def sheets(w):
    return {n: t for n, t, _ in w.sheets}


def col_index(c):
    n = 0
    for ch in c:
        n = n * 26 + (ord(ch) - 64)
    return n


def header(w, target):
    row = next(w.rows(target, limit=1), {})
    return [v for _, v in sorted(row.items(), key=lambda kv: col_index(kv[0]))]


def tally(w, target, col, skip_header=True):
    out = defaultdict(int)
    for i, c in enumerate(w.rows(target)):
        if skip_header and i == 0:
            continue
        v = c.get(col)
        if v:
            out[str(v).strip()] += 1
    return out


def main(d):
    came = WB(find(d, "Controle_CAME__2026__1007"))
    csvs = WB(find(d, "CSVs_disponeis_para_SIGI"))
    bkp = WB(find(d, "Backup_20260401"))
    S, C, B = sheets(came), sheets(csvs), sheets(bkp)

    print("=" * 72)
    print("1. INVENTÁRIO")
    print("=" * 72)
    for label, w in (("Controle CAME 2026", came), ("CSVs disponíveis", csvs), ("Backup 01/04", bkp)):
        vis = sum(1 for _, _, st in w.sheets if st == "visible")
        print(f"  {label:22} {len(w.sheets):3} abas ({vis} visíveis)")

    print()
    print("=" * 72)
    print("2. OQ-05 — uma NE cobre vários insumos?")
    print("=" * 72)
    emp = defaultdict(set)
    for i, c in enumerate(came.rows(S["EMPENHOS"])):
        if i == 0:
            continue
        sku, ne = c.get("A"), c.get("D")          # SKU, EMP/SEI
        if sku and ne:
            emp[str(ne).strip()].add(str(sku).strip())
    multi = {k: v for k, v in emp.items() if len(v) > 1}
    pct = 100 * len(multi) / len(emp) if emp else 0
    print(f"  empenhos distintos ........ {len(emp)}")
    print(f"  com mais de um SKU ........ {len(multi)}  ({pct:.1f}%)")
    print(f"  maior nº de SKUs numa NE .. {max((len(v) for v in emp.values()), default=0)}")
    print("  RESPOSTA: multi-item é a regra, não a exceção.")

    print()
    print("=" * 72)
    print("3. OQ-11 — uma ATA tem mais de um fornecedor?")
    print("=" * 72)
    forn = defaultdict(set)
    for i, c in enumerate(came.rows(S["Controle de ITENS"])):
        if i == 0:
            continue
        sei, f = c.get("C"), c.get("T")           # SEI DA ATA, FORNECEDOR
        if sei and f:
            forn[str(sei).strip()].add(str(f).strip())
    multi_f = {k: v for k, v in forn.items() if len(v) > 1}
    pct = 100 * len(multi_f) / len(forn) if forn else 0
    print(f"  ATAs com fornecedor identificado .. {len(forn)}")
    print(f"  com mais de um fornecedor ......... {len(multi_f)}  ({pct:.1f}%)")
    print(f"  maior nº de fornecedores numa ATA . {max((len(v) for v in forn.values()), default=0)}")

    print()
    print("=" * 72)
    print("4. ENUMS REAIS vs. MODELO")
    print("=" * 72)
    for label, sheet, col, modelo in (
        ("STATUS DA ATA", "Controle de ITENS", "M", "5 (rascunho/vigente/suspensa/encerrada/cancelada)"),
        ("STATUS PREGÃO", "Controle de ITENS", "L", "não existe no modelo"),
        ("AÇÃO sobre item crítico", "ESTOQUE <3", "D", "não existe no modelo"),
    ):
        t = tally(came, S[sheet], col)
        print(f"\n  {label} — {len(t)} valores distintos · modelo: {modelo}")
        for k, n in sorted(t.items(), key=lambda x: -x[1]):
            print(f"      {n:6}  {k}")

    print()
    print("=" * 72)
    print("5. HIERARQUIA DE MATERIAIS (3 níveis)")
    print("=" * 72)
    tgt = C["TRANFERENCIA DE MERCADORIA (CSV"]
    tri = defaultdict(set)
    grupos = set()
    for i, c in enumerate(csvs.rows(tgt)):
        if i == 0:
            continue
        g, sg, cl = c.get("P"), c.get("O"), c.get("N")   # Grupo, SubGrupo, Classificação
        if g:
            grupos.add(str(g).strip())
            if sg:
                tri[str(g).strip()].add(str(sg).strip())
    print(f"  grupos distintos ..... {len(grupos)}")
    print(f"  pares grupo/subgrupo . {sum(len(v) for v in tri.values())}")
    for g in sorted(tri)[:6]:
        print(f"      {g} → {len(tri[g])} subgrupos")

    print()
    print("=" * 72)
    print("6. FAIXAS DE COBERTURA (abas do CAME)")
    print("=" * 72)
    for sheet in ("ESTOQUE <3", "ESTOQUE >3<6", "ESTOQUE >6<9", "ESTOQUE >9<12",
                  "ESTOQUE >12", "SEM GIRO", "POR DEMANDA", "ESTOQUE ZERADO"):
        if sheet not in S:
            continue
        n = sum(1 for i, c in enumerate(came.rows(S[sheet])) if i > 0 and c.get("A"))
        print(f"  {sheet:16} {n:6} itens")

    print()
    print("=" * 72)
    print("7. VOLUMES DAS FONTES CSV")
    print("=" * 72)
    for name in ("COBERTURA DE ESTOQUE (CSV)", "ESTOQUE CONSOLIDADO (CSV)",
                 "TRANSFERENCIA CONSOLIDADO (CSV)", "REQUISIÇÃO ENTRE UNIDADES (CSV)",
                 "ENTRADAS NFS (CSV)", "PRODUTOS INDISPONIVEIS (CSV)",
                 "TRANFERENCIA DE MERCADORIA (CSV"):
        if name not in C:
            continue
        n = sum(1 for _ in csvs.rows(C[name])) - 1
        print(f"  {name:36} {n:7} linhas · {len(header(csvs, C[name])):2} colunas")

    print()
    print("=" * 72)
    print("8. CINCATARINA como canal de compra")
    print("=" * 72)
    for sheet, col, label in (("Controle de ITENS", "M", "STATUS DA ATA"),
                              ("Controle de ITENS", "L", "STATUS PREGÃO")):
        t = tally(came, S[sheet], col)
        for k, n in t.items():
            if "CINCATARINA" in k.upper():
                print(f"  {label:16} {k:28} {n:5} itens")

    print()
    print("=" * 72)
    print("9. SALDO: armazenado vs. calculado (evidência para ADR-0003)")
    print("=" * 72)
    div = same = 0
    for i, c in enumerate(came.rows(S["Controle de ITENS"])):
        if i == 0:
            continue
        s, sc = c.get("I"), c.get("J")            # SALDO, SALDO CALCULADO
        if s is None or sc is None:
            continue
        try:
            a, b = float(str(s).replace(",", ".")), float(str(sc).replace(",", "."))
        except ValueError:
            continue
        if abs(a - b) > 0.001:
            div += 1
        else:
            same += 1
    tot = div + same
    pct = 100 * div / tot if tot else 0
    print(f"  linhas com ambos os saldos .. {tot}")
    print(f"  divergentes ................. {div}  ({pct:.1f}%)")
    print("  Duas colunas para a mesma verdade: o cenário que ADR-0003 evita.")

    print()
    print("=" * 72)
    print("10. LGPD — colunas com dado pessoal nas fontes")
    print("=" * 72)
    for name in C:
        if "(CSV" not in name and "FORNECED" not in name:
            continue
        cols = header(csvs, C[name])
        flags = [c for c in cols if any(k in c.lower() for k in
                 ("paciente", "cnpj", "e-mail", "email", "telefone", "responsavel",
                  "requerente", "autorizador", "aprovador", "usuario", "finalizador"))]
        if flags:
            print(f"  {name}")
            print(f"      {' · '.join(flags)}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
