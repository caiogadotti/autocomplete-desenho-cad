"""Histórico de peças que o usuário já desenhou, para o sugestor aprender com uso real.

O catálogo em `src/modelo/catalogo.py` é a lista de produtos que a fábrica
já corta, fixa e definida por quem opera a produção. Esse histórico é outra
coisa: cresce sozinho conforme o usuário desenha, então uma peça que ele
usa toda semana mas que não é produto de catálogo (uma medida auxiliar, um
recorte específico de um pedido) também passa a ser reconhecida da segunda
vez em diante. É o que torna o autocomplete pessoal, não só "sabe os
produtos da fábrica".

Persistido em JSON simples de propósito: é um arquivo por usuário/máquina,
sem concorrência de escrita a resolver, e dá para inspecionar ou editar à
mão sem ferramenta nenhuma.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass

CAMINHO_PADRAO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "dados", "historico_pecas.json")


@dataclass(frozen=True)
class PecaHistorico:
    nome: str
    largura_mm: int
    altura_mm: int
    pode_girar: bool
    vezes_usada: int


def carregar_historico(caminho: str = CAMINHO_PADRAO) -> list[PecaHistorico]:
    if not os.path.exists(caminho):
        return []
    with open(caminho, "r", encoding="utf-8") as arquivo:
        bruto = json.load(arquivo)
    return [PecaHistorico(**item) for item in bruto]


def registrar_peca(
    nome: str,
    largura_mm: int,
    altura_mm: int,
    pode_girar: bool = True,
    caminho: str = CAMINHO_PADRAO,
) -> None:
    """Registra uma peça que o usuário desenhou/confirmou, somando uso se já existir.

    "Já existir" é decidido por nome exato, não por medida próxima: duas
    peças de nome diferente que dão em medida parecida (uma variação de
    corte, por exemplo) continuam contadas separadamente, porque são
    decisões de desenho distintas mesmo se a medida final coincidir.
    """
    historico = carregar_historico(caminho)
    atualizado = False

    novo_historico = []
    for peca in historico:
        if peca.nome == nome:
            novo_historico.append(
                PecaHistorico(
                    nome=nome,
                    largura_mm=largura_mm,
                    altura_mm=altura_mm,
                    pode_girar=pode_girar,
                    vezes_usada=peca.vezes_usada + 1,
                )
            )
            atualizado = True
        else:
            novo_historico.append(peca)

    if not atualizado:
        novo_historico.append(
            PecaHistorico(nome=nome, largura_mm=largura_mm, altura_mm=altura_mm, pode_girar=pode_girar, vezes_usada=1)
        )

    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as arquivo:
        json.dump([asdict(p) for p in novo_historico], arquivo, ensure_ascii=False, indent=2)
