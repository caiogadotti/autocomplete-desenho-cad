"""Compara as heurísticas de corte de forma medida, não por opinião.

Cada heurística roda sobre os mesmos pedidos, e o resultado só é
reportado depois de passar na validação do layout (`Layout.validar`).
Isso não é formalidade: em nesting, um bug de sobreposição **melhora** o
aproveitamento aparente, porque a mesma área de rolo passa a contar duas
peças. Número bonito de heurística que não valida é número errado.

Mede três coisas, porque as três importam e podem discordar entre si:
- **aproveitamento**: fração do rolo consumido que virou peça
- **comprimento usado**: quanto de rolo foi desenrolado (o custo real)
- **tempo**: se a heurística mais esperta compensa o que cobra

Uso:
    python scripts/comparar_heuristicas.py
"""

import os
import statistics
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from src.heuristicas.faixas import melhor_faixa, primeira_faixa_que_serve
from src.heuristicas.skyline import skyline
from src.modelo.catalogo import LARGURA_ROLO_PADRAO_MM, gerar_pedido
from src.modelo.peca import Rolo

HEURISTICAS = [
    ("Faixa, primeira que serve", primeira_faixa_que_serve),
    ("Faixa, melhor encaixe", melhor_faixa),
    ("Skyline", skyline),
    ("Skyline, penaliza enterrado", lambda p, r: skyline(p, r, penalizar_enterrado=True)),
]

TAMANHOS_PEDIDO = [50, 200, 500]
SEMENTES = [1, 2, 3, 4, 5]


def main() -> None:
    # Comprimento máximo alto de propósito: o limite existe para o caso real
    # (rolo acaba), mas no benchmark ele truncaria o pedido grande e faria
    # todas as heurísticas empatarem no mesmo teto artificial, escondendo a
    # diferença entre elas. A primeira versão deste script usava o padrão de
    # 100m e 795 peças de um pedido de 500 nao cabiam.
    rolo = Rolo(largura_mm=LARGURA_ROLO_PADRAO_MM, comprimento_max_mm=1_000_000)

    print(f"Rolo de {rolo.largura_mm}mm de largura")
    print(f"{len(SEMENTES)} pedidos por tamanho, sementes {SEMENTES}\n")

    for quantidade in TAMANHOS_PEDIDO:
        print(f"--- pedido de {quantidade} peças ---")
        print(f"{'heuristica':<28} {'aproveit.':>10} {'compr. rolo':>13} {'tempo':>9}  validacao")

        for nome, funcao in HEURISTICAS:
            aproveitamentos, comprimentos, tempos = [], [], []
            problemas_totais = 0
            nao_couberam_total = 0

            for seed in SEMENTES:
                pedido = gerar_pedido(quantidade, seed=seed)

                inicio = time.perf_counter()
                layout = funcao(pedido, rolo)
                tempos.append(time.perf_counter() - inicio)

                problemas = layout.validar()
                problemas_totais += len(problemas)
                nao_couberam_total += len(layout.nao_couberam)

                aproveitamentos.append(layout.aproveitamento)
                comprimentos.append(layout.comprimento_usado_mm)

            marca = "ok" if problemas_totais == 0 else f"{problemas_totais} PROBLEMAS"
            if nao_couberam_total:
                marca += f", {nao_couberam_total} nao couberam"

            print(
                f"{nome:<28} {statistics.mean(aproveitamentos):>9.1%} "
                f"{statistics.mean(comprimentos)/1000:>11.2f}m "
                f"{statistics.mean(tempos)*1000:>8.1f}ms  {marca}"
            )
        print()

    print("aproveitamento = area das pecas / area de rolo consumida (largura cheia x comprimento)")
    print("comprimento = quanto de rolo foi desenrolado, o custo real em materia-prima")


if __name__ == "__main__":
    main()
