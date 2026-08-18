"""Autocomplete de desenho: sugere o resto de uma peça a partir de pouco traço.

É a parte de IA do projeto, e o que ela faz é mais próximo de autocomplete de
CAD do que de "reconhecer produto": conforme o usuário desenha (ou fotografa
um rascunho), o sistema tenta prever o resto do retângulo antes dele estar
completo, e aprende a fazer isso melhor com o próprio uso.

Duas fontes de conhecimento, priorizadas nessa ordem:

1. **Histórico do usuário** (`src/ia/historico.py`): cresce sozinho, peça a
   peça, cada vez que uma sugestão é aceita. É o que faz o sistema aprender
   com quem está desenhando, não só reconhecer produto de catálogo.
2. **Catálogo da fábrica** (`src/modelo/catalogo.py`): lista fixa de
   produtos que já se sabe que existem, serve de base antes do histórico
   ter dado alguma peça.

Duas formas de acionar o autocomplete:

- **Fechamento**: o usuário já desenhou as duas dimensões (2-3 pontos, ou um
  retângulo inteiro extraído de foto), e o sistema sugere ajustar a medida
  bruta para a peça conhecida mais próxima.
- **Só uma aresta**: o usuário desenhou só o primeiro traço (uma medida),
  ainda não fechou a peça, e o sistema já sugere candidatos de como ela
  provavelmente vai terminar. Isso é autocomplete de verdade: a sugestão
  aparece antes do desenho estar pronto, não depois.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from src.ia.historico import PecaHistorico, carregar_historico
from src.modelo.catalogo import CATALOGO

TOLERANCIA_PADRAO_MM = 15.0


@dataclass(frozen=True)
class SugestaoFechamento:
    """Resultado de tentar completar uma peça a partir de medida parcial.

    `origem="bruto"` significa que nada no histórico nem no catálogo ficou
    dentro da tolerância: a sugestão é a própria medida lida, sem snap.
    Isso é intencional, não uma falha. O objetivo é não forçar peça nova a
    virar uma peça existente errada.
    """

    largura_mm: int
    altura_mm: int
    nome: str | None
    confianca: float
    origem: str  # "historico", "catalogo" ou "bruto"
    girada: bool = False


def _candidatos(historico: list[PecaHistorico] | None) -> list[tuple[str, int, int, bool, str]]:
    """Junta histórico e catálogo numa lista só, histórico primeiro.

    Vir primeiro importa: quando uma peça do histórico e uma do catálogo
    empatam em distância da medida lida, a busca abaixo usa `<` estrito e
    fica com o primeiro candidato encontrado, então o histórico (o que o
    próprio usuário desenhou) vence o catálogo genérico no empate.
    """
    candidatos: list[tuple[str, int, int, bool, str]] = []
    for peca in historico or []:
        candidatos.append((peca.nome, peca.largura_mm, peca.altura_mm, peca.pode_girar, "historico"))
    for nome, largura, altura, pode_girar in CATALOGO:
        candidatos.append((nome, largura, altura, pode_girar, "catalogo"))
    return candidatos


def _distancia_mm(bruta: tuple[float, float], alvo: tuple[int, int]) -> float:
    return math.hypot(bruta[0] - alvo[0], bruta[1] - alvo[1])


def sugerir_fechamento(
    largura_bruta_mm: float,
    altura_bruta_mm: float,
    historico: list[PecaHistorico] | None = None,
    tolerancia_mm: float = TOLERANCIA_PADRAO_MM,
) -> SugestaoFechamento:
    """Casa uma medida já com as duas dimensões desenhadas com o que se conhece.

    Testa cada candidato (histórico + catálogo) na orientação lida e,
    quando `pode_girar`, também girado, porque um usuário desenhando de
    memória erra a orientação com a mesma frequência que erra a medida.
    Confiança cai linearmente até 0 na borda da tolerância.
    """
    melhor: SugestaoFechamento | None = None
    menor_distancia = float("inf")

    for nome, largura_ref, altura_ref, pode_girar, origem in _candidatos(historico):
        testes = [(largura_ref, altura_ref, False)]
        if pode_girar:
            testes.append((altura_ref, largura_ref, True))

        for largura_teste, altura_teste, girada in testes:
            distancia = _distancia_mm((largura_bruta_mm, altura_bruta_mm), (largura_teste, altura_teste))
            if distancia <= tolerancia_mm and distancia < menor_distancia:
                menor_distancia = distancia
                limite = tolerancia_mm * math.sqrt(2)
                confianca = max(0.0, 1.0 - distancia / limite)
                melhor = SugestaoFechamento(
                    largura_mm=largura_teste,
                    altura_mm=altura_teste,
                    nome=nome,
                    confianca=round(confianca, 3),
                    origem=origem,
                    girada=girada,
                )

    if melhor is not None:
        return melhor

    return SugestaoFechamento(
        largura_mm=round(largura_bruta_mm),
        altura_mm=round(altura_bruta_mm),
        nome=None,
        confianca=0.0,
        origem="bruto",
    )


def sugerir_por_uma_aresta(
    comprimento_aresta_mm: float,
    historico: list[PecaHistorico] | None = None,
    tolerancia_mm: float = TOLERANCIA_PADRAO_MM,
    maximo: int = 3,
) -> list[SugestaoFechamento]:
    """Autocomplete real: sugere como a peça termina a partir de só um traço.

    Diferente de `sugerir_fechamento`, aqui o retângulo ainda não existe:
    só uma medida foi desenhada (um lado), e a peça pode virar qualquer
    coisa que tenha esse lado como largura ou altura. Por isso devolve uma
    lista ranqueada por confiança em vez de uma única resposta: com um
    traço só, mais de uma peça conhecida pode bater, e quem está desenhando
    decide entre as opções em vez do sistema escolher por ele.

    É essa função que faz o autocomplete acontecer *durante* o desenho, não
    só depois que a peça já está pronta.
    """
    candidatos_ranqueados: list[SugestaoFechamento] = []

    for nome, largura_ref, altura_ref, pode_girar, origem in _candidatos(historico):
        pares = [(largura_ref, altura_ref)]
        if pode_girar:
            pares.append((altura_ref, largura_ref))

        for lado_a, lado_b in pares:
            for lado_conhecido, lado_a_completar in ((lado_a, lado_b), (lado_b, lado_a)):
                distancia = abs(comprimento_aresta_mm - lado_conhecido)
                if distancia > tolerancia_mm:
                    continue
                confianca = round(max(0.0, 1.0 - distancia / tolerancia_mm), 3)
                candidatos_ranqueados.append(
                    SugestaoFechamento(
                        largura_mm=round(lado_conhecido),
                        altura_mm=round(lado_a_completar),
                        nome=nome,
                        confianca=confianca,
                        origem=origem,
                        girada=False,
                    )
                )

    candidatos_ranqueados.sort(key=lambda s: s.confianca, reverse=True)

    # remove duplicata de medida (mesma peça aparece 2x quando pode_girar
    # produz o mesmo par lado_conhecido/lado_a_completar nas duas voltas)
    vistos: set[tuple[int, int, str | None]] = set()
    unicos: list[SugestaoFechamento] = []
    for s in candidatos_ranqueados:
        chave = (s.largura_mm, s.altura_mm, s.nome)
        if chave not in vistos:
            vistos.add(chave)
            unicos.append(s)

    return unicos[:maximo]


def sugerir_pecas_de_rascunho(
    imagem,
    escala_px_por_mm: float,
    historico: list[PecaHistorico] | None = None,
    tolerancia_mm: float = TOLERANCIA_PADRAO_MM,
) -> list[SugestaoFechamento]:
    """Roda o extrator de visão num rascunho e sugere o fechamento de cada peça.

    É o modo "foto do rascunho": o usuário desenha à mão ou tira foto de um
    desenho parcial, o extrator (já validado com 100% de recall/precisão
    sintética) acha os retângulos, e cada um passa por `sugerir_fechamento`.
    Se `historico=None`, carrega o histórico persistido em disco.

    Import de `src.visao.extrator` fica aqui dentro, não no topo do módulo,
    porque esse é o único caminho do autocomplete que depende de OpenCV. O
    addon de FreeCAD usa `sugerir_por_uma_aresta`/`sugerir_fechamento`
    direto, sem imagem, e o Python embutido do FreeCAD não tem `cv2`
    instalado por padrão.
    """
    from src.visao.extrator import PecaExtraida, extrair_pecas

    if historico is None:
        historico = carregar_historico()

    extraidas: list[PecaExtraida] = extrair_pecas(imagem)
    sugestoes: list[SugestaoFechamento] = []

    for peca in extraidas:
        largura_mm, altura_mm = peca.medidas_mm(escala_px_por_mm)
        sugestoes.append(sugerir_fechamento(largura_mm, altura_mm, historico, tolerancia_mm))

    return sugestoes
