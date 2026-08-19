"""Histórico de peças que o usuário já desenhou, para o sugestor aprender com uso real.

O catálogo em `src/modelo/catalogo.py` é a lista de produtos que a fábrica
já corta, fixa e definida por quem opera a produção. Esse histórico é outra
coisa: cresce sozinho conforme o usuário desenha, então uma peça que ele
usa toda semana mas que não é produto de catálogo (uma medida auxiliar, um
recorte específico de um pedido) também passa a ser reconhecida da segunda
vez em diante. É o que torna o autocomplete pessoal, não só "sabe os
produtos da fábrica".

Persistido em SQLite, não num JSON solto: banco de verdade dá `UPSERT`
atômico (duas gravações concorrentes não corrompem o arquivo, o que um
`json.dump` reescrevendo o arquivo inteiro não garante), e o mesmo arquivo
`.db` pode ser aberto por qualquer ferramenta de SQL pra inspecionar,
sem precisar de servidor nem credencial. Continua sendo "banco local",
não um serviço remoto: não faz sentido esse projeto exigir Supabase ou
Postgres só pra rodar o autocomplete.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone

CAMINHO_PADRAO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "dados", "historico_pecas.db")

_SQL_CRIAR_TABELA = """
CREATE TABLE IF NOT EXISTS pecas (
    nome TEXT PRIMARY KEY,
    largura_mm INTEGER NOT NULL,
    altura_mm INTEGER NOT NULL,
    pode_girar INTEGER NOT NULL,
    vezes_usada INTEGER NOT NULL DEFAULT 1,
    atualizado_em TEXT NOT NULL
)
"""


@dataclass(frozen=True)
class PecaHistorico:
    nome: str
    largura_mm: int
    altura_mm: int
    pode_girar: bool
    vezes_usada: int
    atualizado_em: str = ""


@contextmanager
def _conexao(caminho: str):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    conexao = sqlite3.connect(caminho)
    try:
        conexao.execute(_SQL_CRIAR_TABELA)
        yield conexao
        conexao.commit()
    finally:
        conexao.close()


def carregar_historico(caminho: str = CAMINHO_PADRAO) -> list[PecaHistorico]:
    """Devolve o histórico ordenado da peça mais usada pra menos usada.

    A ordem importa em `sugerir_por_uma_aresta`: quando duas peças do
    histórico empatam em distância da medida procurada, a que aparece
    primeiro na lista de candidatos vence, então listar por uso decrescente
    faz o autocomplete preferir a peça que o usuário desenha mais, não uma
    ordem arbitrária de inserção no banco.
    """
    with _conexao(caminho) as conexao:
        linhas = conexao.execute(
            "SELECT nome, largura_mm, altura_mm, pode_girar, vezes_usada, atualizado_em "
            "FROM pecas ORDER BY vezes_usada DESC"
        ).fetchall()

    return [
        PecaHistorico(
            nome=nome,
            largura_mm=largura_mm,
            altura_mm=altura_mm,
            pode_girar=bool(pode_girar),
            vezes_usada=vezes_usada,
            atualizado_em=atualizado_em,
        )
        for nome, largura_mm, altura_mm, pode_girar, vezes_usada, atualizado_em in linhas
    ]


def registrar_peca(
    nome: str,
    largura_mm: int,
    altura_mm: int,
    pode_girar: bool = True,
    caminho: str = CAMINHO_PADRAO,
) -> None:
    """Registra uma peça que o usuário desenhou/gerou/confirmou, somando uso se já existir.

    "Já existir" é decidido por nome exato, não por medida próxima: duas
    peças de nome diferente que dão em medida parecida (uma variação de
    corte, por exemplo) continuam contadas separadamente, porque são
    decisões de desenho distintas mesmo se a medida final coincidir. O
    `UPSERT` do SQLite resolve isso numa instrução só, sem o
    ler-tudo/reescrever-tudo que o JSON exigia.
    """
    agora = datetime.now(timezone.utc).isoformat()
    with _conexao(caminho) as conexao:
        conexao.execute(
            """
            INSERT INTO pecas (nome, largura_mm, altura_mm, pode_girar, vezes_usada, atualizado_em)
            VALUES (?, ?, ?, ?, 1, ?)
            ON CONFLICT(nome) DO UPDATE SET
                largura_mm = excluded.largura_mm,
                altura_mm = excluded.altura_mm,
                pode_girar = excluded.pode_girar,
                vezes_usada = vezes_usada + 1,
                atualizado_em = excluded.atualizado_em
            """,
            (nome, largura_mm, altura_mm, int(pode_girar), agora),
        )
