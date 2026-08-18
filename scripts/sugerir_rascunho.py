"""CLI: lê uma imagem (rascunho/foto de desenho parcial) e sugere as peças.

Fecha o fluxo do módulo `src/ia/sugestor.py` num comando de terminal: em vez
de desenhar cada peça com precisão, o usuário desenha aproximado, tira uma
foto ou exporta a imagem, e este comando devolve a medida de catálogo mais
provável para cada retângulo encontrado, junto com a confiança do casamento
e a peça que ficou de fora do catálogo (medida nova ou orientação inválida).

Uso:
    python scripts/sugerir_rascunho.py rascunho.png --escala 0.12
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import cv2

from src.ia.sugestor import sugerir_pecas_de_rascunho


def main() -> None:
    parser = argparse.ArgumentParser(description="Sugere peças de catálogo a partir de um rascunho/foto.")
    parser.add_argument("imagem", help="arquivo de imagem (png/jpg) com o rascunho")
    parser.add_argument(
        "--escala", type=float, default=0.12,
        help="pixels por mm da imagem (padrão: 0.12, escala usada nas pranchas sintéticas)",
    )
    parser.add_argument(
        "--tolerancia", type=float, default=15.0,
        help="tolerância em mm para casar com o catálogo (padrão: 15.0)",
    )
    args = parser.parse_args()

    imagem = cv2.imread(args.imagem, cv2.IMREAD_GRAYSCALE)
    if imagem is None:
        print(f"não consegui ler a imagem: {args.imagem}", file=sys.stderr)
        raise SystemExit(1)

    sugestoes = sugerir_pecas_de_rascunho(imagem, args.escala, args.tolerancia)

    if not sugestoes:
        print("nenhum retângulo encontrado no rascunho")
        return

    print(f"{len(sugestoes)} peça(s) encontrada(s):\n")
    for i, s in enumerate(sugestoes, start=1):
        if s.origem == "catalogo":
            girada = " (girada)" if s.girada else ""
            print(
                f"  {i}. {s.largura_mm}x{s.altura_mm}mm -> '{s.nome_catalogo}'{girada}, "
                f"confiança {s.confianca:.0%}"
            )
        else:
            print(f"  {i}. {s.largura_mm}x{s.altura_mm}mm -> peça nova, sem casamento no catálogo")


if __name__ == "__main__":
    main()
