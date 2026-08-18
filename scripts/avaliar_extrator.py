"""Mede o extrator de peças contra a verdade que o gerador de prancha conhece.

Métricas, no vocabulário de detecção:
- **recall**: das peças que estavam no desenho, quantas foram achadas
- **precisão**: das que o extrator devolveu, quantas eram peça de verdade
- **erro de medida**: quantos mm de diferença entre a peça achada e a real

As três importam e não são intercambiáveis. Um extrator que devolve todo
retângulo da folha tem recall perfeito e precisão péssima (traz carimbo e
cota junto). Um que só devolve o retângulo mais óbvio tem precisão perfeita
e recall péssimo. E os dois podem estar certos na contagem e errados na
medida, que é o que de fato alimenta o otimizador de corte.

Uso:
    python scripts/avaliar_extrator.py
"""

import os
import statistics
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from src.visao.extrator import PecaExtraida, extrair_pecas
from src.visao.prancha import PecaDesenhada, gerar_prancha

SEMENTES = list(range(1, 16))
QUANTIDADES = [3, 6, 10]
TOLERANCIA_PX = 6


def _casam(real: PecaDesenhada, achada: PecaExtraida) -> bool:
    """Mesma peça se os cantos batem dentro da tolerância.

    A tolerância existe porque o contorno é desenhado com linha de 3px: o
    retângulo detectado fica alguns pixels maior ou menor que o nominal
    dependendo de qual borda da linha o contorno pegou.
    """
    return (
        abs(real.x_px - achada.x_px) <= TOLERANCIA_PX
        and abs(real.y_px - achada.y_px) <= TOLERANCIA_PX
        and abs(real.largura_px - achada.largura_px) <= TOLERANCIA_PX
        and abs(real.altura_px - achada.altura_px) <= TOLERANCIA_PX
    )


def avaliar(quantidade: int, com_ruido: bool, descartar_carimbo: bool) -> dict:
    achadas_certas = total_reais = total_achadas = 0
    erros_mm: list[float] = []

    for seed in SEMENTES:
        prancha = gerar_prancha(quantidade, seed=seed, com_ruido=com_ruido)
        extraidas = extrair_pecas(prancha.imagem, descartar_carimbo=descartar_carimbo)

        total_reais += len(prancha.pecas)
        total_achadas += len(extraidas)

        disponiveis = list(extraidas)
        for real in prancha.pecas:
            casada = next((e for e in disponiveis if _casam(real, e)), None)
            if casada is None:
                continue
            disponiveis.remove(casada)
            achadas_certas += 1

            largura_mm, altura_mm = casada.medidas_mm(prancha.escala_px_por_mm)
            erros_mm.append(abs(largura_mm - real.largura_mm))
            erros_mm.append(abs(altura_mm - real.altura_mm))

    return {
        "recall": achadas_certas / total_reais if total_reais else 0.0,
        "precisao": achadas_certas / total_achadas if total_achadas else 0.0,
        "erro_medio_mm": statistics.mean(erros_mm) if erros_mm else float("nan"),
        "erro_max_mm": max(erros_mm) if erros_mm else float("nan"),
        "reais": total_reais,
        "achadas": total_achadas,
    }


def main() -> None:
    print(f"{len(SEMENTES)} pranchas por tamanho, tolerancia de casamento {TOLERANCIA_PX}px\n")

    cenarios = [
        ("desenho limpo (so contornos)", True, dict(com_ruido=False, descartar_carimbo=True)),
        ("com cota, centro e carimbo", True, dict(com_ruido=True, descartar_carimbo=True)),
        ("com ruido, sem filtrar carimbo", True, dict(com_ruido=True, descartar_carimbo=False)),
    ]

    for titulo, _, kwargs in cenarios:
        print(f"--- {titulo} ---")
        print(f"{'pecas':>6} {'recall':>9} {'precisao':>10} {'erro medio':>12} {'erro max':>10}")
        for quantidade in QUANTIDADES:
            r = avaliar(quantidade, **kwargs)
            print(
                f"{quantidade:>6} {r['recall']:>8.1%} {r['precisao']:>9.1%} "
                f"{r['erro_medio_mm']:>10.1f}mm {r['erro_max_mm']:>8.1f}mm"
            )
        print()

    print("recall   = das pecas do desenho, quantas foram achadas")
    print("precisao = das devolvidas pelo extrator, quantas eram peca de verdade")
    print("erro     = diferenca em mm entre a medida extraida e a real")


if __name__ == "__main__":
    main()
