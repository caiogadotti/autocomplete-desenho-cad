"""Extrai as peças a cortar de uma prancha de desenho técnico.

Linha de base em OpenCV clássico, sem aprendizado: binariza, acha contornos,
filtra o que não é peça e devolve os retângulos. Existe antes de qualquer
rede neural pelo mesmo motivo que o estimador espectral veio antes do MLP no
projeto de catenária: só faz sentido pagar por um modelo aprendido depois de
medir quanto o método direto já resolve. Se a linha de base acerta quase
tudo, a rede não tem espaço pra provar valor.

O trabalho de verdade aqui não é achar retângulo, é **descartar o que é
retângulo mas não é peça**: o carimbo, o contorno externo da folha, e os
retângulos falsos que as linhas de cota formam ao se cruzarem.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

# Um contorno de peça é desenhado com linha grossa; cota e linha de centro
# são finas. Erodir a imagem binarizada apaga o fino e preserva o grosso,
# que é o filtro mais barato que separa os dois mundos.
ESPESSURA_MINIMA_PX = 2

AREA_MINIMA_PX2 = 900
TOLERANCIA_RETANGULO = 0.80


@dataclass(frozen=True)
class PecaExtraida:
    x_px: int
    y_px: int
    largura_px: int
    altura_px: int

    @property
    def area_px2(self) -> int:
        return self.largura_px * self.altura_px

    def medidas_mm(self, escala_px_por_mm: float) -> tuple[int, int]:
        return (
            round(self.largura_px / escala_px_por_mm),
            round(self.altura_px / escala_px_por_mm),
        )


def _e_retangulo_cheio(contorno: np.ndarray, largura: int, altura: int) -> bool:
    """Descarta contorno cuja área não preenche o próprio retângulo delimitador.

    Um retângulo de verdade ocupa quase todo o seu bounding box. Um "L" de
    duas cotas que se cruzam, ou um contorno aberto, tem bounding box grande
    e área pequena. Esse teste sozinho mata a maior parte dos falsos.
    """
    area_bbox = largura * altura
    if area_bbox == 0:
        return False
    return cv2.contourArea(contorno) / area_bbox >= TOLERANCIA_RETANGULO


def extrair_pecas(imagem: np.ndarray, descartar_carimbo: bool = True) -> list[PecaExtraida]:
    """Devolve os retângulos que parecem peça a cortar, do maior para o menor.

    `descartar_carimbo` remove o retângulo do canto inferior direito que
    carrega o texto do desenho. É parametrizável para o benchmark medir
    quanto esse descarte específico vale.
    """
    _, binaria = cv2.threshold(imagem, 200, 255, cv2.THRESH_BINARY_INV)

    # Apaga traço fino (cota, linha de centro), mantém contorno grosso.
    nucleo = np.ones((ESPESSURA_MINIMA_PX, ESPESSURA_MINIMA_PX), np.uint8)
    so_grosso = cv2.erode(binaria, nucleo, iterations=1)
    so_grosso = cv2.dilate(so_grosso, nucleo, iterations=1)

    contornos, _ = cv2.findContours(so_grosso, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    altura_img, largura_img = imagem.shape[:2]
    encontradas: list[PecaExtraida] = []

    for contorno in contornos:
        x, y, largura, altura = cv2.boundingRect(contorno)

        if largura * altura < AREA_MINIMA_PX2:
            continue
        if largura >= largura_img - 4 and altura >= altura_img - 4:
            continue  # moldura da folha inteira
        if not _e_retangulo_cheio(contorno, largura, altura):
            continue
        if descartar_carimbo and x > largura_img * 0.72 and y > altura_img * 0.80:
            continue

        encontradas.append(PecaExtraida(x_px=x, y_px=y, largura_px=largura, altura_px=altura))

    return _fundir_contornos_da_mesma_linha(encontradas)


def _fundir_contornos_da_mesma_linha(encontradas: list[PecaExtraida]) -> list[PecaExtraida]:
    """Funde o par de contornos de cada linha grossa, ficando com o eixo dela.

    `findContours` enxerga uma linha de contorno grossa como duas fronteiras:
    a de fora e a de dentro. A primeira versão deste extrator ficava com a de
    fora e descartava a de dentro como duplicata, e isso produzia um viés
    **sistemático de +5px** em toda medida: a espessura do traço (3px) mais a
    dilatação da limpeza (2px) entravam na conta como se fossem peça.

    Com escala de 0.12px/mm isso era 40mm de erro em toda peça, sempre para
    mais. Erro constante assim seria fácil de esconder subtraindo 5, mas a
    constante depende da espessura do traço, que num desenho real varia de
    prancha para prancha e de quem desenhou.

    A média entre a fronteira externa e a interna é o eixo da linha, que é a
    medida nominal da peça, e ela não precisa saber a espessura: qualquer que
    seja, o eixo continua no meio.
    """
    encontradas.sort(key=lambda p: p.area_px2, reverse=True)

    fundidas: list[PecaExtraida] = []
    usadas: set[int] = set()

    for i, externa in enumerate(encontradas):
        if i in usadas:
            continue

        interna = None
        for j, candidata in enumerate(encontradas[i + 1:], start=i + 1):
            if j in usadas:
                continue
            dentro = (
                candidata.x_px >= externa.x_px
                and candidata.y_px >= externa.y_px
                and candidata.x_px + candidata.largura_px <= externa.x_px + externa.largura_px
                and candidata.y_px + candidata.altura_px <= externa.y_px + externa.altura_px
            )
            # o par de uma mesma linha tem tamanho parecido; retângulo bem
            # menor lá dentro é outra peça desenhada dentro desta, não a
            # fronteira interna do mesmo traço
            if dentro and candidata.area_px2 >= externa.area_px2 * 0.5:
                interna = candidata
                usadas.add(j)
                break

        if interna is None:
            fundidas.append(externa)
            continue

        fundidas.append(
            PecaExtraida(
                x_px=round((externa.x_px + interna.x_px) / 2),
                y_px=round((externa.y_px + interna.y_px) / 2),
                largura_px=round((externa.largura_px + interna.largura_px) / 2),
                altura_px=round((externa.altura_px + interna.altura_px) / 2),
            )
        )

    return fundidas
