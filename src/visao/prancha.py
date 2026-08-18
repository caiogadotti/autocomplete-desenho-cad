"""Gera pranchas de desenho técnico sintéticas, com a verdade conhecida junto.

Por que sintético: extrair peça de desenho técnico é problema de visão
computacional, e visão precisa de dado rotulado para ser medida. Desenho
técnico real de fábrica é propriedade do cliente e não pode virar dataset
público, e anotar centenas à mão levaria semanas antes da primeira linha de
algoritmo.

A saída de gerar sintético não é só a imagem: é a imagem **mais a lista
exata de peças que estão nela**. Isso permite medir o extrator contra a
verdade, do mesmo jeito que o simulador de sensores do projeto de catenária
conhecia o dano real que o motor de análise tinha que descobrir sozinho.

Essa estratégia não é atalho, é o que a literatura da área usa quando não
há dataset: ver "Symbol Detection in Mechanical Engineering Sketches:
Experimental Study on Principle Sketches with Synthetic Data Generation and
Deep Learning" (Applied Sciences, MDPI, 2024).

O desenho imita as convenções que um desenho de corte real tem, porque são
elas que o extrator vai ter que aprender a separar:

- **contorno da peça**: linha grossa e contínua, é o que interessa
- **linha de cota**: fina, com setas nas pontas e o número da medida
- **linha de centro**: fina e tracejada, não é corte e não pode virar peça
- **carimbo**: retângulo no canto com texto, é o maior retângulo da folha
  e justamente o que não é peça
"""

from __future__ import annotations

import random
from dataclasses import dataclass

import cv2
import numpy as np

ESCALA_PADRAO = 0.12  # pixels por mm: um rolo de 1600mm cabe em ~192px

PRETO = 0
BRANCO = 255

ESPESSURA_CONTORNO = 3
ESPESSURA_FINA = 1


@dataclass(frozen=True)
class PecaDesenhada:
    """A verdade: uma peça que está na prancha, e onde ela está.

    Coordenadas em pixel na imagem, medidas em mm no mundo real. O extrator
    vai devolver pixels, e a comparação com `largura_mm`/`altura_mm` só é
    possível porque o gerador sabe a escala.
    """

    id: str
    x_px: int
    y_px: int
    largura_px: int
    altura_px: int
    largura_mm: int
    altura_mm: int


@dataclass
class Prancha:
    imagem: np.ndarray
    pecas: list[PecaDesenhada]
    escala_px_por_mm: float


def _desenhar_cota(img: np.ndarray, x1: int, y1: int, x2: int, y2: int, texto: str) -> None:
    """Linha de cota fina com setas e o número da medida, como num desenho real."""
    cv2.arrowedLine(img, (x1, y1), (x2, y2), PRETO, ESPESSURA_FINA, tipLength=0.06)
    cv2.arrowedLine(img, (x2, y2), (x1, y1), PRETO, ESPESSURA_FINA, tipLength=0.06)

    meio_x, meio_y = (x1 + x2) // 2, (y1 + y2) // 2
    cv2.putText(img, texto, (meio_x - 14, meio_y - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.32, PRETO, 1)


def _desenhar_linha_de_centro(img: np.ndarray, x: int, y: int, largura: int, altura: int) -> None:
    """Linha tracejada no meio da peça. Ruído proposital: não é contorno de corte."""
    meio_y = y + altura // 2
    passo = 12
    for inicio in range(x + 4, x + largura - 4, passo):
        cv2.line(img, (inicio, meio_y), (min(inicio + 6, x + largura - 4), meio_y), PRETO, ESPESSURA_FINA)


def _desenhar_carimbo(img: np.ndarray, largura_img: int, altura_img: int) -> None:
    """Carimbo no canto inferior direito, com texto dentro.

    É o retângulo mais óbvio da folha depois das peças, e não é peça. Está
    aqui de propósito: um extrator ingênuo que só procura retângulo vai
    devolver o carimbo como se fosse uma peça a cortar.
    """
    larg, alt = 190, 60
    x, y = largura_img - larg - 12, altura_img - alt - 12
    cv2.rectangle(img, (x, y), (x + larg, y + alt), PRETO, ESPESSURA_FINA)
    cv2.line(img, (x, y + 22), (x + larg, y + 22), PRETO, ESPESSURA_FINA)
    cv2.putText(img, "PLANO DE CORTE", (x + 6, y + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.34, PRETO, 1)
    cv2.putText(img, "TNT 40g  ESC 1:10", (x + 6, y + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.3, PRETO, 1)


def gerar_prancha(
    quantidade_pecas: int,
    seed: int,
    escala_px_por_mm: float = ESCALA_PADRAO,
    com_ruido: bool = True,
) -> Prancha:
    """Monta uma prancha com peças retangulares dispostas em grade irregular.

    `com_ruido` liga os elementos que não são peça (cotas, linha de centro,
    carimbo). Desligar serve para isolar, no diagnóstico, se um erro do
    extrator vem da geometria ou da poluição do desenho.
    """
    rng = random.Random(seed)
    largura_img, altura_img = 1000, 700
    img = np.full((altura_img, largura_img), BRANCO, dtype=np.uint8)

    medidas_mm = [
        (700, 1200), (700, 1150), (320, 620), (900, 750),
        (500, 450), (480, 480), (380, 260),
    ]

    pecas: list[PecaDesenhada] = []
    ocupadas: list[tuple[int, int, int, int]] = []

    tentativas = 0
    while len(pecas) < quantidade_pecas and tentativas < quantidade_pecas * 60:
        tentativas += 1
        largura_mm, altura_mm = rng.choice(medidas_mm)
        if rng.random() < 0.5:
            largura_mm, altura_mm = altura_mm, largura_mm

        largura_px = int(largura_mm * escala_px_por_mm)
        altura_px = int(altura_mm * escala_px_por_mm)

        # margem generosa: cota precisa de espaço fora da peça pra não colar
        x = rng.randint(60, max(61, largura_img - largura_px - 220))
        y = rng.randint(40, max(41, altura_img - altura_px - 110))

        folga = 34
        colide = any(
            x < ox + ol + folga and ox < x + largura_px + folga
            and y < oy + oa + folga and oy < y + altura_px + folga
            for ox, oy, ol, oa in ocupadas
        )
        if colide:
            continue

        cv2.rectangle(img, (x, y), (x + largura_px, y + altura_px), PRETO, ESPESSURA_CONTORNO)

        if com_ruido:
            _desenhar_cota(img, x, y - 14, x + largura_px, y - 14, str(largura_mm))
            _desenhar_cota(img, x - 16, y, x - 16, y + altura_px, str(altura_mm))
            if altura_px > 40:
                _desenhar_linha_de_centro(img, x, y, largura_px, altura_px)

        ocupadas.append((x, y, largura_px, altura_px))
        pecas.append(
            PecaDesenhada(
                id=f"peca-{len(pecas):02d}",
                x_px=x, y_px=y,
                largura_px=largura_px, altura_px=altura_px,
                largura_mm=largura_mm, altura_mm=altura_mm,
            )
        )

    if com_ruido:
        _desenhar_carimbo(img, largura_img, altura_img)

    return Prancha(imagem=img, pecas=pecas, escala_px_por_mm=escala_px_por_mm)
