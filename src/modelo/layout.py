"""O resultado de um plano de corte, e como medir se ele é bom.

O `Layout` carrega as peças posicionadas e sabe validar a si mesmo. A
validação existe porque heurística de nesting é o tipo de código onde um
bug produz resultado *melhor* que o correto: se duas peças se sobrepõem,
o aproveitamento calculado sobe, e o número fica bonito justamente porque
está errado. Toda heurística deste projeto é validada antes de ter a
métrica reportada.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.modelo.peca import Peca, PecaPosicionada, Rolo


@dataclass
class Layout:
    rolo: Rolo
    posicionadas: list[PecaPosicionada] = field(default_factory=list)
    nao_couberam: list[Peca] = field(default_factory=list)

    @property
    def comprimento_usado_mm(self) -> int:
        """Até onde o rolo precisou ser desenrolado."""
        if not self.posicionadas:
            return 0
        return max(p.y_fim_mm for p in self.posicionadas)

    @property
    def area_util_mm2(self) -> int:
        """Soma da área das peças, o que de fato virou produto."""
        return sum(p.largura_mm * p.altura_mm for p in self.posicionadas)

    @property
    def area_consumida_mm2(self) -> int:
        """Área de rolo gasta: largura cheia x comprimento desenrolado.

        Conta a largura inteira do rolo mesmo onde não há peça, porque é
        assim que o custo funciona: o rolo é consumido por comprimento, a
        faixa vazia na lateral foi paga do mesmo jeito.
        """
        return self.rolo.largura_mm * self.comprimento_usado_mm

    @property
    def aproveitamento(self) -> float:
        """Fração da área consumida que virou peça. 1.0 seria desperdício zero."""
        consumida = self.area_consumida_mm2
        return self.area_util_mm2 / consumida if consumida else 0.0

    @property
    def sobra_mm2(self) -> int:
        return self.area_consumida_mm2 - self.area_util_mm2

    def validar(self) -> list[str]:
        """Devolve a lista de problemas encontrados. Lista vazia = layout válido.

        Retorna os problemas em vez de levantar exceção porque quem chama
        (o benchmark) quer reportar todas as heurísticas, inclusive as
        que falharam, em vez de abortar na primeira.
        """
        problemas: list[str] = []

        for p in self.posicionadas:
            if p.x_mm < 0 or p.y_mm < 0:
                problemas.append(f"{p.peca.id}: posição negativa ({p.x_mm}, {p.y_mm})")
            if p.x_fim_mm > self.rolo.largura_mm:
                problemas.append(
                    f"{p.peca.id}: passa da largura do rolo "
                    f"({p.x_fim_mm}mm > {self.rolo.largura_mm}mm)"
                )
            if not p.peca.pode_girar and p.girada:
                problemas.append(f"{p.peca.id}: foi girada mas o sentido do tecido não permite")

        for i, a in enumerate(self.posicionadas):
            for b in self.posicionadas[i + 1:]:
                if a.sobrepoe(b):
                    problemas.append(f"sobreposição entre {a.peca.id} e {b.peca.id}")

        return problemas
