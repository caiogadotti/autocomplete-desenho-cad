"""CLI: digita a medida que quer, o sistema gera o desenho e salva no banco.

É o caminho inverso do autocomplete por aresta: em vez de o sistema
adivinhar a medida a partir de um traço parcial, aqui a medida já é
conhecida (o usuário digitou) e o sistema só desenha e lembra. Toda peça
gerada aqui entra no histórico (`src/ia/historico.py`, banco SQLite), então
da segunda vez que essa mesma peça for citada por nome, ela já pesa mais
que o catálogo genérico nas sugestões futuras.

Uso:
    python scripts/gerar_peca.py 480 480 --nome touca --saida touca.dxf
    python scripts/gerar_peca.py 700 1200 --nome frente-avental --nao-pode-girar
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from src.cad.dxf import escrever_peca_avulsa
from src.ia.historico import registrar_peca


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera o DXF de uma peça a partir da medida digitada, e salva no histórico.")
    parser.add_argument("largura_mm", type=int, help="largura da peça em mm")
    parser.add_argument("altura_mm", type=int, help="altura da peça em mm")
    parser.add_argument("--nome", default=None, help="nome da peça (padrão: largura x altura)")
    parser.add_argument("--saida", default=None, help="arquivo DXF de saída (padrão: <nome>.dxf)")
    parser.add_argument(
        "--nao-pode-girar", action="store_true",
        help="marca que essa peça não pode ser rotacionada (sentido de fabricação importa)",
    )
    args = parser.parse_args()

    nome = args.nome or f"{args.largura_mm}x{args.altura_mm}"
    saida = args.saida or f"{nome}.dxf"

    escrever_peca_avulsa(args.largura_mm, args.altura_mm, saida, nome=nome)
    registrar_peca(nome, args.largura_mm, args.altura_mm, pode_girar=not args.nao_pode_girar)

    print(f"peça '{nome}' ({args.largura_mm}x{args.altura_mm}mm) gerada em {saida}")
    print("salva no histórico: vai pesar nas próximas sugestões do autocomplete.")


if __name__ == "__main__":
    main()
