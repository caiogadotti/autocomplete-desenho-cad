"""CLI do otimizador: DXF entra, plano de corte em DXF sai.

É a forma de usar o projeto sem escrever código Python, e a que se encaixa
em fluxo de trabalho de quem já desenha em CAD: exporta o DXF com as peças,
roda este comando, abre o resultado de volta no CAD.

Uso:
    python scripts/otimizar.py pecas.dxf --largura-rolo 1600 --saida plano.dxf
    python scripts/otimizar.py pecas.dxf --heuristica faixa
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from src.cad.dxf import escrever_plano, ler_pecas
from src.heuristicas.faixas import melhor_faixa, primeira_faixa_que_serve
from src.heuristicas.skyline import skyline
from src.modelo.peca import Rolo

HEURISTICAS = {
    "skyline": skyline,
    "faixa": primeira_faixa_que_serve,
    "faixa-melhor": melhor_faixa,
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Otimiza o corte de peças retangulares num rolo, a partir de um DXF."
    )
    parser.add_argument("entrada", help="arquivo DXF com as peças a cortar")
    parser.add_argument("--saida", default=None, help="DXF do plano de corte (padrão: <entrada>_plano.dxf)")
    parser.add_argument("--largura-rolo", type=int, default=1600, help="largura do rolo em mm (padrão: 1600)")
    parser.add_argument(
        "--heuristica", choices=sorted(HEURISTICAS), default="skyline",
        help="qual heurística usar (padrão: skyline, a mais rápida)",
    )
    args = parser.parse_args()

    try:
        pecas = ler_pecas(args.entrada)
    except FileNotFoundError:
        print(f"arquivo não encontrado: {args.entrada}", file=sys.stderr)
        raise SystemExit(1)
    except ValueError as erro:
        print(erro, file=sys.stderr)
        raise SystemExit(1)

    rolo = Rolo(largura_mm=args.largura_rolo, comprimento_max_mm=10_000_000)
    layout = HEURISTICAS[args.heuristica](pecas, rolo)

    problemas = layout.validar()
    if problemas:
        print(f"ERRO: o plano gerado é inválido ({len(problemas)} problemas):", file=sys.stderr)
        for problema in problemas[:5]:
            print(f"  - {problema}", file=sys.stderr)
        raise SystemExit(2)

    saida = args.saida or f"{os.path.splitext(args.entrada)[0]}_plano.dxf"
    escrever_plano(layout, saida)

    print(f"{len(pecas)} peças lidas de {args.entrada}")
    if layout.nao_couberam:
        print(f"ATENÇÃO: {len(layout.nao_couberam)} peça(s) não couberam na largura do rolo")
    print(f"heurística: {args.heuristica}")
    print(f"comprimento de rolo: {layout.comprimento_usado_mm/1000:.2f}m")
    print(f"aproveitamento: {layout.aproveitamento:.1%}")
    print(f"sobra: {layout.sobra_mm2/1_000_000:.2f}m²")
    print(f"\nplano salvo em {saida}")


if __name__ == "__main__":
    main()
