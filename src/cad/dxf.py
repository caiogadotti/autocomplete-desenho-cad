"""Ponte com o CAD: lê peças de um DXF e escreve o plano de corte em DXF.

DXF é o formato de troca que todo CAD lê e escreve (AutoCAD, FreeCAD,
SolidWorks, Fusion, LibreCAD, BricsCAD). Ele é a razão de este projeto poder
ser integrado ao fluxo de trabalho de quem já desenha em CAD, em vez de
obrigar a pessoa a redesenhar tudo numa interface nossa.

O contrato é deliberadamente simples, para não obrigar quem for usar a
aprender uma convenção nossa:

**Entrada** (`ler_pecas`): qualquer LWPOLYLINE fechada de 4 vértices que
forme um retângulo alinhado aos eixos vira uma peça. É o que sai de um
`RECTANG` do AutoCAD. Bloco de texto, cota e linha de centro são ignorados
porque não são polilinha fechada.

**Saída** (`escrever_plano`): cada peça posicionada vira uma polilinha
fechada, e camadas separam o que é o quê, porque camada é como o desenhista
liga e desliga informação no CAD dele:

| camada | conteúdo |
|---|---|
| `CORTE` | o contorno de corte de cada peça, o que a máquina segue |
| `IDENT` | o id da peça, para conferência |
| `SOBRA` | o retângulo do rolo, para enxergar o desperdício |

As unidades do DXF são milímetros, declaradas no cabeçalho (`$INSUNITS`),
para o CAD não abrir o arquivo assumindo polegada e escalar tudo por 25.4.
"""

from __future__ import annotations

from pathlib import Path

import ezdxf

from src.modelo.layout import Layout
from src.modelo.peca import Peca

TOLERANCIA_RETANGULO_MM = 0.5

CAMADA_CORTE = "CORTE"
CAMADA_IDENT = "IDENT"
CAMADA_SOBRA = "SOBRA"


def _e_retangulo_alinhado(pontos: list[tuple[float, float]]) -> bool:
    """Checa se 4 vértices formam um retângulo paralelo aos eixos.

    Só retângulo alinhado é aceito porque o motor de nesting deste projeto
    trabalha com peça retangular. Peça inclinada ou de contorno livre é
    recusada de forma explícita em vez de ser aproximada pelo seu
    bounding box, o que devolveria um plano de corte errado com aparência
    de certo.
    """
    if len(pontos) != 4:
        return False

    xs = sorted({round(x, 3) for x, _ in pontos})
    ys = sorted({round(y, 3) for _, y in pontos})
    if len(xs) != 2 or len(ys) != 2:
        return False

    esperados = {(xs[0], ys[0]), (xs[0], ys[1]), (xs[1], ys[0]), (xs[1], ys[1])}
    reais = {(round(x, 3), round(y, 3)) for x, y in pontos}
    return esperados == reais


def ler_pecas(caminho: str | Path, prefixo_id: str = "dxf") -> list[Peca]:
    """Extrai as peças retangulares de um arquivo DXF.

    Levanta `ValueError` com contagem se o arquivo não tiver nenhuma peça
    reconhecível, em vez de devolver lista vazia: silêncio aqui viraria um
    plano de corte vazio mais adiante, e o usuário não saberia se o desenho
    estava errado ou se o otimizador falhou.
    """
    documento = ezdxf.readfile(str(caminho))
    espaco = documento.modelspace()

    pecas: list[Peca] = []
    ignoradas = 0

    for entidade in espaco.query("LWPOLYLINE"):
        if not entidade.closed:
            ignoradas += 1
            continue

        pontos = [(p[0], p[1]) for p in entidade.get_points()]
        if not _e_retangulo_alinhado(pontos):
            ignoradas += 1
            continue

        xs = [x for x, _ in pontos]
        ys = [y for _, y in pontos]
        largura = round(max(xs) - min(xs))
        altura = round(max(ys) - min(ys))

        if largura <= 0 or altura <= 0:
            ignoradas += 1
            continue

        pecas.append(
            Peca(
                id=f"{prefixo_id}-{len(pecas):04d}",
                largura_mm=largura,
                altura_mm=altura,
            )
        )

    if not pecas:
        raise ValueError(
            f"nenhuma peça retangular encontrada em {caminho}. "
            f"{ignoradas} polilinha(s) foram ignoradas por não serem retângulo "
            "fechado alinhado aos eixos. O motor só trabalha com peça retangular."
        )

    return pecas


def escrever_plano(layout: Layout, caminho: str | Path, versao_dxf: str = "R2010") -> None:
    """Grava o plano de corte como DXF pronto para abrir no CAD.

    `versao_dxf` em R2010 por padrão: é antiga o suficiente para qualquer
    CAD em uso abrir, e nova o suficiente para suportar camada e polilinha
    leve sem gambiarra.
    """
    documento = ezdxf.new(versao_dxf, setup=True)
    documento.header["$INSUNITS"] = 4  # 4 = milímetros
    espaco = documento.modelspace()

    for nome, cor in ((CAMADA_CORTE, 1), (CAMADA_IDENT, 3), (CAMADA_SOBRA, 8)):
        if nome not in documento.layers:
            documento.layers.add(nome, color=cor)

    comprimento = layout.comprimento_usado_mm
    espaco.add_lwpolyline(
        [(0, 0), (layout.rolo.largura_mm, 0),
         (layout.rolo.largura_mm, comprimento), (0, comprimento)],
        close=True,
        dxfattribs={"layer": CAMADA_SOBRA},
    )

    for posicionada in layout.posicionadas:
        x, y = posicionada.x_mm, posicionada.y_mm
        largura, altura = posicionada.largura_mm, posicionada.altura_mm

        espaco.add_lwpolyline(
            [(x, y), (x + largura, y), (x + largura, y + altura), (x, y + altura)],
            close=True,
            dxfattribs={"layer": CAMADA_CORTE},
        )

        # altura do texto proporcional à peça, com piso: peça pequena não
        # pode ficar com rótulo maior que ela
        altura_texto = max(8.0, min(largura, altura) * 0.12)
        espaco.add_text(
            posicionada.peca.id,
            dxfattribs={"layer": CAMADA_IDENT, "height": altura_texto},
        ).set_placement((x + largura / 2, y + altura / 2), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)

    documento.saveas(str(caminho))
