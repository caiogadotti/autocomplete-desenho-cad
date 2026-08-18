"""Renderiza um DXF de plano de corte em imagem, para conferir sem abrir CAD.

Serve para dois momentos: olhar rápido durante o desenvolvimento, e gerar a
figura que vai no README. Não substitui abrir no CAD, mas evita depender
dele para saber se o plano saiu certo.

As camadas escritas por `src/cad/dxf.py` ganham cor distinta aqui, para o
que é corte, identificação e contorno do rolo ficar separado na imagem do
mesmo jeito que fica no CAD.

Uso:
    python scripts/ver_plano.py plano.dxf
    python scripts/ver_plano.py plano.dxf --saida docs/plano.png
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import ezdxf
import matplotlib
matplotlib.use("Agg")  # sem janela: só grava arquivo, funciona em terminal puro
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

CORES_CAMADA = {
    "CORTE": "#f5a524",
    "SOBRA": "#5a5a66",
    "IDENT": "#7dd3a8",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Renderiza um DXF de plano de corte em PNG.")
    parser.add_argument("entrada", help="arquivo DXF a renderizar")
    parser.add_argument("--saida", default=None, help="PNG de saída (padrão: <entrada>.png)")
    parser.add_argument("--sem-rotulo", action="store_true", help="não desenha o id das peças")
    args = parser.parse_args()

    documento = ezdxf.readfile(args.entrada)
    espaco = documento.modelspace()

    figura, eixo = plt.subplots(figsize=(7, 11))
    figura.patch.set_facecolor("#0a0a0b")
    eixo.set_facecolor("#0a0a0b")

    pecas = 0
    for entidade in espaco.query("LWPOLYLINE"):
        pontos = [(p[0], p[1]) for p in entidade.get_points()]
        xs = [x for x, _ in pontos]
        ys = [y for _, y in pontos]
        camada = entidade.dxf.layer
        cor = CORES_CAMADA.get(camada, "#8b8b96")

        eixo.add_patch(
            Rectangle(
                (min(xs), min(ys)),
                max(xs) - min(xs),
                max(ys) - min(ys),
                fill=camada == "CORTE",
                facecolor="#f5a524" if camada == "CORTE" else "none",
                alpha=0.20 if camada == "CORTE" else 1.0,
                edgecolor=cor,
                linewidth=1.6 if camada == "CORTE" else 1.0,
                linestyle="-" if camada != "SOBRA" else "--",
            )
        )
        if camada == "CORTE":
            pecas += 1

    if not args.sem_rotulo:
        for texto in espaco.query("TEXT"):
            ponto = texto.dxf.insert
            eixo.text(
                ponto[0], ponto[1], texto.dxf.text,
                ha="center", va="center", fontsize=5, color=CORES_CAMADA["IDENT"],
            )

    eixo.autoscale_view()
    eixo.set_aspect("equal")
    eixo.set_xlabel("largura do rolo (mm)", color="#8b8b96", fontsize=9)
    eixo.set_ylabel("comprimento desenrolado (mm)", color="#8b8b96", fontsize=9)
    eixo.tick_params(colors="#5a5a66", labelsize=8)
    for borda in eixo.spines.values():
        borda.set_color("#292930")
    eixo.set_title(f"Plano de corte, {pecas} peças", color="#f4f4f5", fontsize=11, pad=12)
    eixo.grid(True, color="#1b1b20", linewidth=0.5)

    saida = args.saida or f"{os.path.splitext(args.entrada)[0]}.png"
    figura.tight_layout()
    figura.savefig(saida, dpi=160, facecolor=figura.get_facecolor())
    print(f"{pecas} peças renderizadas em {saida}")


if __name__ == "__main__":
    main()
