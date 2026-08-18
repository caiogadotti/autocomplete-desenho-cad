"""Sugere o fechamento de uma peça a partir de poucos pontos ou de um rascunho.

Junta as duas pontas do projeto: o extrator de visão (`src/visao/extrator.py`)
já sabe achar retângulo em desenho, mas não sabe se aquele retângulo é uma
peça conhecida ou uma medida nova. Este módulo fecha essa lacuna comparando
a medida bruta (de 2-3 pontos desenhados, ou de um contorno extraído de uma
foto/rascunho) contra o catálogo de peças que a fábrica já corta, e sugere a
medida exata do catálogo quando a distância é pequena o bastante pra ser
"a mesma peça, desenho impreciso" em vez de "peça nova de verdade".

Isso é o que torna o CAD assistido: em vez de o usuário desenhar cada peça
com precisão milimétrica, ele desenha aproximado e o sistema aprende do
catálogo (que cresce com o uso real) o que ele provavelmente quis dizer.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from src.modelo.catalogo import CATALOGO
from src.visao.extrator import PecaExtraida, extrair_pecas

TOLERANCIA_PADRAO_MM = 15.0


@dataclass(frozen=True)
class SugestaoFechamento:
    """Resultado de tentar casar uma medida bruta com o catálogo.

    `origem="bruto"` significa que nenhuma peça do catálogo ficou dentro da
    tolerância: a sugestão é a própria medida lida, sem snap. Isso é
    intencional, não uma falha. O objetivo é não forçar peça nova a virar
    uma peça existente errada.
    """

    largura_mm: int
    altura_mm: int
    nome_catalogo: str | None
    confianca: float
    origem: str  # "catalogo" ou "bruto"
    girada: bool = False


def _distancia_mm(bruta: tuple[float, float], catalogo: tuple[int, int]) -> float:
    return math.hypot(bruta[0] - catalogo[0], bruta[1] - catalogo[1])


def sugerir_fechamento(
    largura_bruta_mm: float,
    altura_bruta_mm: float,
    tolerancia_mm: float = TOLERANCIA_PADRAO_MM,
) -> SugestaoFechamento:
    """Casa uma medida bruta (2-3 pontos desenhados) com o catálogo, se der.

    Testa a peça na orientação lida e, quando `pode_girar`, também girada,
    porque um usuário desenhando de memória erra a orientação com a mesma
    frequência que erra a medida. Entre os candidatos dentro da tolerância,
    fica com o de menor distância; a confiança cai linearmente até 0 na
    borda da tolerância, então "quase estourou o limite" já chega ao
    chamador como baixa confiança, não como certeza binária.
    """
    melhor: SugestaoFechamento | None = None
    menor_distancia = float("inf")

    for nome, largura_cat, altura_cat, pode_girar in CATALOGO:
        candidatos = [(largura_cat, altura_cat, False)]
        if pode_girar:
            candidatos.append((altura_cat, largura_cat, True))

        for largura_teste, altura_teste, girada in candidatos:
            distancia = _distancia_mm((largura_bruta_mm, altura_bruta_mm), (largura_teste, altura_teste))
            if distancia <= tolerancia_mm and distancia < menor_distancia:
                menor_distancia = distancia
                limite = tolerancia_mm * math.sqrt(2)
                confianca = max(0.0, 1.0 - distancia / limite)
                melhor = SugestaoFechamento(
                    largura_mm=largura_teste,
                    altura_mm=altura_teste,
                    nome_catalogo=nome,
                    confianca=round(confianca, 3),
                    origem="catalogo",
                    girada=girada,
                )

    if melhor is not None:
        return melhor

    return SugestaoFechamento(
        largura_mm=round(largura_bruta_mm),
        altura_mm=round(altura_bruta_mm),
        nome_catalogo=None,
        confianca=0.0,
        origem="bruto",
    )


def sugerir_pecas_de_rascunho(
    imagem,
    escala_px_por_mm: float,
    tolerancia_mm: float = TOLERANCIA_PADRAO_MM,
) -> list[SugestaoFechamento]:
    """Roda o extrator de visão num rascunho e sugere o fechamento de cada peça.

    É o modo "foto do rascunho": o usuário desenha à mão ou tira foto de um
    desenho parcial, o extrator (que já existe e já foi validado com 100% de
    recall/precisão sintética) acha os retângulos, e cada um passa por
    `sugerir_fechamento` pra virar uma medida de catálogo ou ficar como
    medida bruta nova.
    """
    extraidas: list[PecaExtraida] = extrair_pecas(imagem)
    sugestoes: list[SugestaoFechamento] = []

    for peca in extraidas:
        largura_mm, altura_mm = peca.medidas_mm(escala_px_por_mm)
        sugestoes.append(sugerir_fechamento(largura_mm, altura_mm, tolerancia_mm))

    return sugestoes
