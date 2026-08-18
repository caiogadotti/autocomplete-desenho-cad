"""Peças a cortar e o rolo de matéria-prima de onde elas saem.

Modela o problema real de uma fábrica de descartáveis hospitalares: o TNT
chega em rolo de largura fixa e comprimento praticamente contínuo, e as
peças (frente de avental, manga, campo cirúrgico) são retângulos que
precisam ser posicionados nesse rolo com o mínimo de sobra.

Todas as medidas em milímetros, inteiras. Ponto flutuante em geometria de
corte causa erro de arredondamento que se acumula peça a peça e produz
sobreposição de 0.0001mm que o algoritmo não detecta.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Peca:
    """Um retângulo a ser cortado.

    `pode_girar` existe porque tecido não é isotrópico: TNT tem sentido de
    fabricação, e girar uma peça 90 graus muda como ela estica e resiste.
    Peça de avental que precisa esticar no sentido do corpo não pode ser
    girada; peça de embalagem interna pode.
    """

    id: str
    largura_mm: int
    altura_mm: int
    pode_girar: bool = True

    @property
    def area_mm2(self) -> int:
        return self.largura_mm * self.altura_mm

    def girada(self) -> "Peca":
        return Peca(
            id=self.id,
            largura_mm=self.altura_mm,
            altura_mm=self.largura_mm,
            pode_girar=self.pode_girar,
        )


@dataclass(frozen=True)
class Rolo:
    """A matéria-prima: largura fixa, comprimento a minimizar.

    Diferente de "chapa" (que tem os dois lados fixos e o objetivo é usar
    menos chapas), num rolo o objetivo é usar o menor **comprimento**
    possível, porque o rolo é contínuo e o desperdício é o quanto de rolo
    foi consumido além do necessário.
    """

    largura_mm: int
    comprimento_max_mm: int = 100_000


@dataclass(frozen=True)
class PecaPosicionada:
    """Uma peça já com posição definida no rolo.

    `x` corre na largura do rolo, `y` no comprimento. Origem no canto
    inferior esquerdo.
    """

    peca: Peca
    x_mm: int
    y_mm: int
    girada: bool

    @property
    def largura_mm(self) -> int:
        return self.peca.altura_mm if self.girada else self.peca.largura_mm

    @property
    def altura_mm(self) -> int:
        return self.peca.largura_mm if self.girada else self.peca.altura_mm

    @property
    def x_fim_mm(self) -> int:
        return self.x_mm + self.largura_mm

    @property
    def y_fim_mm(self) -> int:
        return self.y_mm + self.altura_mm

    def sobrepoe(self, outra: "PecaPosicionada") -> bool:
        """Duas peças se sobrepõem se as projeções em x E em y se cruzam.

        Usado só na validação (`src/modelo/layout.py`), não no caminho
        quente das heurísticas: verificar par a par é O(n²) e as
        heurísticas têm estruturas próprias mais rápidas para evitar
        colisão. Aqui a lentidão não importa, a correção sim.
        """
        return (
            self.x_mm < outra.x_fim_mm
            and outra.x_mm < self.x_fim_mm
            and self.y_mm < outra.y_fim_mm
            and outra.y_mm < self.y_fim_mm
        )
