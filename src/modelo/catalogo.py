"""Peças reais de descartáveis hospitalares, e geração de pedidos de teste.

As medidas abaixo são de ordem de grandeza plausível para avental
cirúrgico, campo e touca, não medidas exatas de um produto específico da
Descartee (não são dado da empresa, são referência genérica de produto do
setor). Servem para o benchmark ter peças com proporções realistas em vez
de retângulos aleatórios: o que separa uma heurística boa de uma ruim é
justamente como ela lida com a mistura de peça grande e peça pequena, e
essa mistura precisa parecer com a real para a medição valer.

Largura de rolo de TNT: 1600mm é um valor comum de fabricação.
"""

from __future__ import annotations

import random

from src.modelo.peca import Peca

LARGURA_ROLO_PADRAO_MM = 1600

# (nome, largura, altura, pode_girar)
# pode_girar=False onde o sentido de fabricação do TNT importa: peça que
# precisa esticar no sentido do corpo não pode ser rotacionada.
CATALOGO = [
    ("frente-avental", 700, 1200, False),
    ("costas-avental", 700, 1150, False),
    ("manga-avental", 320, 620, False),
    ("campo-cirurgico-g", 1400, 900, True),
    ("campo-cirurgico-m", 900, 750, True),
    ("campo-cirurgico-p", 500, 450, True),
    ("touca", 480, 480, True),
    ("propé", 380, 260, True),
    ("reforco-punho", 120, 300, True),
]


def gerar_pedido(quantidade: int, seed: int) -> list[Peca]:
    """Monta um pedido com mistura realista de peças do catálogo.

    A distribuição não é uniforme de propósito: peça pequena aparece muito
    mais que peça grande num pedido real (um kit cirúrgico leva vários
    propés e uma touca para cada avental), e é essa assimetria que estressa
    as heurísticas.
    """
    rng = random.Random(seed)
    pesos = [3, 3, 6, 1, 2, 4, 5, 6, 4]

    pedido: list[Peca] = []
    for i in range(quantidade):
        nome, largura, altura, pode_girar = rng.choices(CATALOGO, weights=pesos, k=1)[0]
        pedido.append(
            Peca(id=f"{nome}-{i:04d}", largura_mm=largura, altura_mm=altura, pode_girar=pode_girar)
        )
    return pedido
