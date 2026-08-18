"""Skyline: acompanha o contorno superior real do que já foi cortado.

A limitação das faixas (`faixas.py`) é tratar cada prateleira como um
retângulo de altura única: uma peça de 400mm cria uma faixa de 400mm, e o
vão acima das peças baixas dessa faixa é perdido. Skyline resolve isso
guardando o **perfil real** do topo, segmento a segmento, como o horizonte
de uma cidade. Uma peça nova pode assentar em cima de duas peças baixas
vizinhas, coisa que a heurística de faixa nunca enxerga.

Custo: manter o perfil exige fundir e dividir segmentos a cada inserção, e
verificar assentamento é mais caro que consultar uma altura de faixa. O
benchmark (`scripts/comparar_heuristicas.py`) mede se isso compensa.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.modelo.layout import Layout
from src.modelo.peca import Peca, PecaPosicionada, Rolo


@dataclass
class _Segmento:
    """Um trecho do horizonte: de x até x+largura, o topo está em `altura`."""

    x_mm: int
    largura_mm: int
    altura_mm: int


def _assentamento(perfil: list[_Segmento], indice: int, largura: int, largura_rolo: int) -> tuple[int, int] | None:
    """Onde e como uma peça de `largura` assenta começando no segmento `indice`.

    Devolve `(altura_da_base, area_enterrada)`, ou None se não couber na
    largura do rolo.

    A peça é rígida: pousa sobre o ponto mais alto de todo o trecho que
    cobre, não afunda no vão do vizinho mais baixo. O espaço que sobra
    embaixo dela, sobre os segmentos mais baixos, fica **enterrado**: o
    perfil passa a registrar o topo da peça, e nada mais consegue ocupar
    aquele vão depois. É esse desperdício que a segunda versão desta
    heurística passou a considerar na escolha, ver `skyline()`.
    """
    x_inicio = perfil[indice].x_mm
    if x_inicio + largura > largura_rolo:
        return None

    cobertos: list[_Segmento] = []
    largura_restante = largura
    i = indice

    while largura_restante > 0 and i < len(perfil):
        cobertos.append(perfil[i])
        largura_restante -= perfil[i].largura_mm
        i += 1

    if largura_restante > 0:
        return None

    base = max(seg.altura_mm for seg in cobertos)

    # O último segmento pode ser coberto só parcialmente pela peça.
    area_enterrada = 0
    restante = largura
    for seg in cobertos:
        largura_usada = min(seg.largura_mm, restante)
        area_enterrada += (base - seg.altura_mm) * largura_usada
        restante -= largura_usada

    return base, area_enterrada


def _inserir_no_perfil(perfil: list[_Segmento], x: int, largura: int, novo_topo: int) -> None:
    """Atualiza o horizonte depois de assentar uma peça, e funde vizinhos iguais.

    A fusão não é cosmética: sem ela o perfil cresce um segmento por peça
    inserida, e a busca de assentamento (que percorre segmentos) degrada
    de forma perceptível em lote grande.
    """
    x_fim = x + largura
    novo: list[_Segmento] = []

    for seg in perfil:
        seg_fim = seg.x_mm + seg.largura_mm

        if seg_fim <= x or seg.x_mm >= x_fim:
            novo.append(seg)
            continue

        if seg.x_mm < x:
            novo.append(_Segmento(seg.x_mm, x - seg.x_mm, seg.altura_mm))
        if seg_fim > x_fim:
            novo.append(_Segmento(x_fim, seg_fim - x_fim, seg.altura_mm))

    novo.append(_Segmento(x, largura, novo_topo))
    novo.sort(key=lambda s: s.x_mm)

    fundido: list[_Segmento] = []
    for seg in novo:
        if fundido and fundido[-1].altura_mm == seg.altura_mm:
            fundido[-1] = _Segmento(
                fundido[-1].x_mm, fundido[-1].largura_mm + seg.largura_mm, seg.altura_mm
            )
        else:
            fundido.append(seg)

    perfil[:] = fundido


def skyline(pecas: list[Peca], rolo: Rolo, penalizar_enterrado: bool = False) -> Layout:
    """Posiciona cada peça no melhor ponto do horizonte.

    Critério padrão: **menor topo resultante, empate resolvido pelo x mais
    à esquerda**. O parâmetro existe para o benchmark medir a alternativa,
    não porque a escolha esteja em aberto: ela foi decidida por medição.

    **Por que a "melhoria óbvia" ficou de fora.** A literatura de bin
    packing costuma desempatar pela menor área desperdiçada, e aqui isso
    seria a área que fica *enterrada* embaixo da peça (o vão sobre os
    segmentos mais baixos, que o perfil sela e ninguém mais ocupa).
    Implementei e medi em 20 pedidos: piorou o aproveitamento de 89.6%
    para 86.7%, e priorizar a área enterrada acima do topo derrubou para
    68.3%.

    A causa, também medida: compactar à esquerda mantém o horizonte como
    poucas paredes largas (3.9 segmentos em média), enquanto perseguir a
    menor área enterrada espalha peça pelo rolo e serrilha o perfil (5.6
    segmentos, 9.4 ao final). Perfil fragmentado tem mais degraus estreitos
    onde nada mais cabe. Economizar o vão de agora custa a superfície boa
    de depois.
    """
    layout = Layout(rolo=rolo)
    perfil: list[_Segmento] = [_Segmento(0, rolo.largura_mm, 0)]

    for peca in sorted(pecas, key=lambda p: max(p.largura_mm, p.altura_mm), reverse=True):
        orientacoes = [(peca.largura_mm, peca.altura_mm, False)]
        if peca.pode_girar and peca.largura_mm != peca.altura_mm:
            orientacoes.append((peca.altura_mm, peca.largura_mm, True))

        melhor_chave: tuple | None = None
        melhor_pos: tuple[int, int, int, bool] | None = None  # (topo, x, largura, girou)

        for largura, altura, girou in orientacoes:
            for i in range(len(perfil)):
                assentamento = _assentamento(perfil, i, largura, rolo.largura_mm)
                if assentamento is None:
                    continue
                base, enterrada = assentamento
                topo = base + altura
                if topo > rolo.comprimento_max_mm:
                    continue

                x = perfil[i].x_mm
                chave = (topo, enterrada, x) if penalizar_enterrado else (topo, x)

                if melhor_chave is None or chave < melhor_chave:
                    melhor_chave = chave
                    melhor_pos = (topo, x, largura, girou)

        if melhor_pos is None:
            layout.nao_couberam.append(peca)
            continue

        topo, x, largura, girou = melhor_pos
        altura = peca.largura_mm if girou else peca.altura_mm
        layout.posicionadas.append(
            PecaPosicionada(peca=peca, x_mm=x, y_mm=topo - altura, girada=girou)
        )
        _inserir_no_perfil(perfil, x, largura, topo)

    return layout
