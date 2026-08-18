"""Heurísticas por faixa (shelf): a família mais simples, e a linha de base.

A ideia: empilhar as peças em faixas horizontais de altura fixa, como
prateleiras. Cada faixa tem a altura da peça mais alta que entrou nela, e
peças novas vão sendo encostadas à direita até não caber mais na largura
do rolo, quando uma faixa nova começa acima.

É a família mais fácil de implementar e a mais fácil de entender olhando o
desenho, mas desperdiça o vão vertical: uma faixa criada por uma peça de
400mm de altura fica com 400mm de altura mesmo que todas as outras peças
dela tenham 150mm. Esse desperdício é justamente o que as heurísticas mais
espertas (`skyline.py`) atacam, e é por isso que faixa serve de linha de
base honesta para medir se o resto vale a complexidade.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.modelo.layout import Layout
from src.modelo.peca import Peca, PecaPosicionada, Rolo


@dataclass
class _Faixa:
    y_base_mm: int
    altura_mm: int
    x_livre_mm: int


def _orientacao_para_faixa(peca: Peca, largura_livre: int, altura_faixa: int) -> tuple[int, int, bool] | None:
    """Escolhe orientação que cabe na faixa, preferindo a que gasta menos altura.

    Devolve (largura, altura, girada) ou None se nenhuma orientação couber.
    """
    opcoes = [(peca.largura_mm, peca.altura_mm, False)]
    if peca.pode_girar and peca.largura_mm != peca.altura_mm:
        opcoes.append((peca.altura_mm, peca.largura_mm, True))

    cabem = [
        (larg, alt, girou)
        for larg, alt, girou in opcoes
        if larg <= largura_livre and alt <= altura_faixa
    ]
    return min(cabem, key=lambda o: o[1]) if cabem else None


def _orientacao_para_faixa_nova(peca: Peca, largura_rolo: int) -> tuple[int, int, bool] | None:
    """Numa faixa nova a altura é livre, então prefere a orientação mais baixa.

    Peça deitada gasta menos comprimento de rolo, que é exatamente o que
    se quer minimizar.
    """
    opcoes = [(peca.largura_mm, peca.altura_mm, False)]
    if peca.pode_girar and peca.largura_mm != peca.altura_mm:
        opcoes.append((peca.altura_mm, peca.largura_mm, True))

    cabem = [(larg, alt, girou) for larg, alt, girou in opcoes if larg <= largura_rolo]
    return min(cabem, key=lambda o: o[1]) if cabem else None


def primeira_faixa_que_serve(pecas: list[Peca], rolo: Rolo) -> Layout:
    """First Fit Decreasing por faixa: a peça entra na primeira faixa onde couber.

    Ordena por altura decrescente antes de posicionar. Essa ordenação é o
    que transforma uma heurística ruim numa razoável: colocar as peças
    altas primeiro define faixas altas cedo, e as baixas depois preenchem
    os vãos que sobraram, em vez de criar faixa alta nova no fim.
    """
    layout = Layout(rolo=rolo)
    faixas: list[_Faixa] = []
    topo_mm = 0

    for peca in sorted(pecas, key=lambda p: max(p.largura_mm, p.altura_mm), reverse=True):
        posicionou = False

        for faixa in faixas:
            escolha = _orientacao_para_faixa(
                peca, rolo.largura_mm - faixa.x_livre_mm, faixa.altura_mm
            )
            if escolha is None:
                continue
            largura, _altura, girou = escolha
            layout.posicionadas.append(
                PecaPosicionada(peca=peca, x_mm=faixa.x_livre_mm, y_mm=faixa.y_base_mm, girada=girou)
            )
            faixa.x_livre_mm += largura
            posicionou = True
            break

        if posicionou:
            continue

        escolha = _orientacao_para_faixa_nova(peca, rolo.largura_mm)
        if escolha is None:
            layout.nao_couberam.append(peca)
            continue

        largura, altura, girou = escolha
        if topo_mm + altura > rolo.comprimento_max_mm:
            layout.nao_couberam.append(peca)
            continue

        layout.posicionadas.append(PecaPosicionada(peca=peca, x_mm=0, y_mm=topo_mm, girada=girou))
        faixas.append(_Faixa(y_base_mm=topo_mm, altura_mm=altura, x_livre_mm=largura))
        topo_mm += altura

    return layout


def melhor_faixa(pecas: list[Peca], rolo: Rolo) -> Layout:
    """Best Fit Decreasing: entre as faixas que servem, escolhe a de menor sobra.

    Diferença para a anterior: em vez de parar na primeira faixa que
    couber, olha todas e escolhe a que fica com menos espaço livre depois
    de encaixar. Custa mais tempo (percorre todas as faixas sempre) e a
    pergunta que o benchmark responde é se esse custo compra
    aproveitamento de verdade.
    """
    layout = Layout(rolo=rolo)
    faixas: list[_Faixa] = []
    topo_mm = 0

    for peca in sorted(pecas, key=lambda p: max(p.largura_mm, p.altura_mm), reverse=True):
        melhor: tuple[int, _Faixa, tuple[int, int, bool]] | None = None

        for faixa in faixas:
            escolha = _orientacao_para_faixa(
                peca, rolo.largura_mm - faixa.x_livre_mm, faixa.altura_mm
            )
            if escolha is None:
                continue
            sobra = rolo.largura_mm - faixa.x_livre_mm - escolha[0]
            if melhor is None or sobra < melhor[0]:
                melhor = (sobra, faixa, escolha)

        if melhor is not None:
            _sobra, faixa, (largura, _altura, girou) = melhor
            layout.posicionadas.append(
                PecaPosicionada(peca=peca, x_mm=faixa.x_livre_mm, y_mm=faixa.y_base_mm, girada=girou)
            )
            faixa.x_livre_mm += largura
            continue

        escolha = _orientacao_para_faixa_nova(peca, rolo.largura_mm)
        if escolha is None:
            layout.nao_couberam.append(peca)
            continue

        largura, altura, girou = escolha
        if topo_mm + altura > rolo.comprimento_max_mm:
            layout.nao_couberam.append(peca)
            continue

        layout.posicionadas.append(PecaPosicionada(peca=peca, x_mm=0, y_mm=topo_mm, girada=girou))
        faixas.append(_Faixa(y_base_mm=topo_mm, altura_mm=altura, x_livre_mm=largura))
        topo_mm += altura

    return layout
